import { Injectable, inject } from '@angular/core';
import { LOCAL_DB } from './local-db';
import { Client, Payment, PaymentMethod, Purchase } from './models';
import { fromCents, toCents } from './money';
import { SyncService } from './sync.service';

export interface ClientView extends Client {
  pending: number;
}

export interface Recorded {
  id: string;
  client: ClientView;
  amountCents: number;
}

function normalize(text: string): string {
  return text.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
}

@Injectable({ providedIn: 'root' })
export class LedgerService {
  private db = inject(LOCAL_DB);
  private sync = inject(SyncService);

  async clients(term = ''): Promise<ClientView[]> {
    const needle = normalize(term.trim());
    const all = await this.db.clients.orderBy('name').toArray();
    const filtered = all.filter((c) => c.active && (!needle || normalize(c.name).includes(needle)));
    return Promise.all(filtered.map((c) => this.withPending(c)));
  }

  async client(id: string): Promise<ClientView | undefined> {
    const client = await this.db.clients.get(id);
    return client ? this.withPending(client) : undefined;
  }

  async addClient(data: {
    name: string;
    phone: string | null;
    address: string | null;
    credit_limit: string | null;
  }): Promise<Client> {
    const client: Client = {
      id: crypto.randomUUID(),
      active: true,
      balance: '0.00',
      over_limit: false,
      ...data,
    };
    await this.db.transaction('rw', this.db.clients, this.db.outbox, async () => {
      await this.db.clients.add(client);
      await this.db.outbox.add({
        id: client.id,
        kind: 'client',
        payload: client,
        created_at: new Date().toISOString(),
        attempts: 0,
      });
    });
    this.sync.kick();
    return client;
  }

  async recordPurchase(clientId: string, cents: number, description: string): Promise<Recorded> {
    const purchase: Purchase = {
      id: crypto.randomUUID(),
      client_id: clientId,
      amount: fromCents(cents),
      description: description.trim() || null,
      created_at: new Date().toISOString(),
    };
    await this.db.transaction('rw', this.db.purchases, this.db.outbox, async () => {
      await this.db.purchases.add(purchase);
      await this.db.outbox.add({
        id: purchase.id,
        kind: 'purchase',
        payload: purchase,
        created_at: purchase.created_at,
        attempts: 0,
      });
    });
    this.sync.kick();
    return { id: purchase.id, client: (await this.client(clientId))!, amountCents: cents };
  }

  async recordPayment(clientId: string, cents: number, method: PaymentMethod): Promise<Recorded> {
    const payment: Payment = {
      id: crypto.randomUUID(),
      client_id: clientId,
      amount: fromCents(cents),
      method,
      created_at: new Date().toISOString(),
    };
    await this.db.transaction('rw', this.db.payments, this.db.outbox, async () => {
      await this.db.payments.add(payment);
      await this.db.outbox.add({
        id: payment.id,
        kind: 'payment',
        payload: payment,
        created_at: payment.created_at,
        attempts: 0,
      });
    });
    this.sync.kick();
    return { id: payment.id, client: (await this.client(clientId))!, amountCents: cents };
  }

  private async withPending(client: Client): Promise<ClientView> {
    const purchases = await this.db.purchases.where('client_id').equals(client.id).toArray();
    const payments = await this.db.payments.where('client_id').equals(client.id).toArray();
    const pendingCents =
      purchases.reduce((sum, p) => sum + toCents(p.amount), 0) -
      payments.reduce((sum, p) => sum + toCents(p.amount), 0);
    const balanceCents = toCents(client.balance) + pendingCents;
    const limit = client.credit_limit === null ? null : toCents(client.credit_limit);
    return {
      ...client,
      balance: fromCents(balanceCents),
      over_limit: limit !== null && balanceCents > limit,
      pending: purchases.length + payments.length,
    };
  }
}
