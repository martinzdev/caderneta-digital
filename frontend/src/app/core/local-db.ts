import { InjectionToken } from '@angular/core';
import Dexie, { Table } from 'dexie';
import { Client, OutboxItem, Payment, Purchase } from './models';

export class LocalDb extends Dexie {
  clients!: Table<Client, string>;
  purchases!: Table<Purchase, string>;
  payments!: Table<Payment, string>;
  outbox!: Table<OutboxItem, string>;

  constructor(name = 'caderneta') {
    super(name);
    this.version(1).stores({
      clients: 'id, name',
      purchases: 'id, client_id, created_at',
      payments: 'id, client_id, created_at',
      outbox: 'id, kind, created_at',
    });
  }
}

export const LOCAL_DB = new InjectionToken<LocalDb>('LOCAL_DB', {
  providedIn: 'root',
  factory: () => new LocalDb(),
});
