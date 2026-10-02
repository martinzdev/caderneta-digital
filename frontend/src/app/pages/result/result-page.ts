import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { ClientView, LedgerService } from '../../core/ledger.service';
import { formatBRL, toCents } from '../../core/money';
import { SyncService } from '../../core/sync.service';
import { BackHeader } from '../../shared/back-header';
import { Icon } from '../../shared/icon';

interface SavedState {
  kind?: 'purchase' | 'payment';
  cents?: number;
}

@Component({
  selector: 'app-result-page',
  imports: [RouterLink, BackHeader, Icon],
  templateUrl: './result-page.html',
})
export class ResultPage {
  private ledger = inject(LedgerService);
  private api = inject(ApiService);
  protected readonly sync = inject(SyncService);

  readonly id = input.required<string>();

  protected readonly saved: SavedState = history.state ?? {};
  protected readonly client = signal<ClientView | null>(null);
  protected readonly statement = signal<string | null>(null);
  protected readonly statementError = signal(false);
  protected readonly formatBRL = formatBRL;

  protected readonly owes = computed(() => toCents(this.client()?.balance) > 0);

  protected readonly whatsappUrl = computed(() => {
    const phone = this.client()?.phone;
    const text = this.statement();
    if (!phone || !text) {
      return null;
    }
    return `https://wa.me/55${phone}?text=${encodeURIComponent(text)}`;
  });

  constructor() {
    effect(() => {
      const id = this.id();
      void this.load(id);
    });

    effect(() => {
      if (this.sync.state() === 'idle' && this.sync.pending() === 0 && this.sync.online()) {
        void this.load(this.id());
      }
    });
  }

  private async load(id: string): Promise<void> {
    this.client.set((await this.ledger.client(id)) ?? null);
    if (!this.sync.online() || this.client()?.pending) {
      return;
    }
    try {
      const statement = await this.api.statement(id);
      this.statement.set(statement.text);
      this.statementError.set(false);
    } catch {
      this.statementError.set(true);
    }
  }
}
