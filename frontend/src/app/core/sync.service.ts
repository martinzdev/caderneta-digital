import { HttpErrorResponse } from '@angular/common/http';
import { DestroyRef, Injectable, inject, signal } from '@angular/core';
import { liveQuery } from 'dexie';
import { ApiService } from './api.service';
import { AuthService } from './auth.service';
import { LOCAL_DB } from './local-db';
import { Client, OutboxItem, Payment, Purchase } from './models';

const RETRYABLE = new Set([0, 408, 429, 500, 502, 503, 504]);
const BASE_DELAY = 1000;
const MAX_DELAY = 30000;

export type SyncState = 'idle' | 'syncing' | 'offline' | 'error';

@Injectable({ providedIn: 'root' })
export class SyncService {
  private api = inject(ApiService);
  private auth = inject(AuthService);
  private db = inject(LOCAL_DB);

  readonly online = signal(navigator.onLine);
  readonly pending = signal(0);
  readonly failed = signal(0);
  readonly state = signal<SyncState>('idle');
  readonly lastSync = signal<Date | null>(null);

  private running: Promise<void> | null = null;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private attempt = 0;

  constructor() {
    const onOnline = () => {
      this.online.set(true);
      this.kick();
    };
    const onOffline = () => {
      this.online.set(false);
      this.state.set('offline');
    };
    window.addEventListener('online', onOnline);
    window.addEventListener('offline', onOffline);

    const subscription = liveQuery(() => this.db.outbox.toArray()).subscribe((items) => {
      this.pending.set(items.filter((i) => !i.error).length);
      this.failed.set(items.filter((i) => i.error).length);
    });

    inject(DestroyRef).onDestroy(() => {
      window.removeEventListener('online', onOnline);
      window.removeEventListener('offline', onOffline);
      subscription.unsubscribe();
    });
  }

  kick(): void {
    if (this.retryTimer) {
      clearTimeout(this.retryTimer);
      this.retryTimer = null;
    }
    void this.run();
  }

  run(): Promise<void> {
    this.running ??= this.syncOnce().finally(() => (this.running = null));
    return this.running;
  }

  private async syncOnce(): Promise<void> {
    if (!navigator.onLine || !this.auth.user()) {
      this.state.set('offline');
      return;
    }
    if (!this.auth.token() && !(await this.auth.refresh())) {
      this.state.set('offline');
      return;
    }
    this.state.set('syncing');
    try {
      await this.push();
      await this.pull();
      this.attempt = 0;
      this.lastSync.set(new Date());
      this.state.set('idle');
    } catch (error) {
      this.state.set(
        error instanceof HttpErrorResponse && error.status === 0 ? 'offline' : 'error',
      );
      this.scheduleRetry();
    }
  }

  private async push(): Promise<void> {
    const items = await this.db.outbox.orderBy('created_at').toArray();
    for (const item of items.filter((i) => !i.error)) {
      try {
        await this.send(item);
        await this.db.outbox.delete(item.id);
        if (item.kind === 'purchase') {
          await this.db.purchases.delete(item.id);
        } else if (item.kind === 'payment') {
          await this.db.payments.delete(item.id);
        }
      } catch (error) {
        if (
          error instanceof HttpErrorResponse &&
          !RETRYABLE.has(error.status) &&
          error.status !== 401
        ) {
          await this.db.outbox.update(item.id, {
            attempts: item.attempts + 1,
            error: error.error?.detail ?? 'Registro recusado pelo servidor.',
          });
          continue;
        }
        throw error;
      }
    }
  }

  private send(item: OutboxItem) {
    switch (item.kind) {
      case 'client':
        return this.api.createClient(item.payload as Client);
      case 'purchase':
        return this.api.purchase(item.payload as Purchase);
      case 'payment':
        return this.api.payment(item.payload as Payment);
    }
  }

  private async pull(): Promise<void> {
    const clients = await this.api.clients();
    const pendingClients = new Set(
      (await this.db.outbox.where('kind').equals('client').toArray()).map((i) => i.id),
    );
    await this.db.transaction('rw', this.db.clients, async () => {
      const keep = await this.db.clients.filter((c) => pendingClients.has(c.id)).toArray();
      await this.db.clients.clear();
      await this.db.clients.bulkPut([...clients, ...keep]);
    });
  }

  private scheduleRetry(): void {
    const ceiling = Math.min(MAX_DELAY, BASE_DELAY * 2 ** this.attempt);
    const delay = Math.random() * ceiling;
    this.attempt = Math.min(this.attempt + 1, 5);
    this.retryTimer = setTimeout(() => this.kick(), delay);
  }
}
