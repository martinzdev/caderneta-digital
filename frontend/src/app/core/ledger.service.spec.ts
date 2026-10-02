import 'fake-indexeddb/auto';
import { TestBed } from '@angular/core/testing';
import { ApiService } from './api.service';
import { LedgerService } from './ledger.service';
import { LOCAL_DB, LocalDb } from './local-db';
import { Client } from './models';
import { SyncService } from './sync.service';

const joao: Client = {
  id: '6f1c2b3a-0000-4000-8000-000000000001',
  name: 'João Pereira',
  phone: '69999991234',
  address: null,
  credit_limit: '100.00',
  active: true,
  balance: '87.50',
  over_limit: false,
};

describe('LedgerService', () => {
  let db: LocalDb;
  let service: LedgerService;
  const kick = vi.fn();

  beforeEach(async () => {
    db = new LocalDb(`test-${crypto.randomUUID()}`);
    await db.clients.add(joao);
    await db.clients.add({
      ...joao,
      id: '6f1c2b3a-0000-4000-8000-000000000002',
      name: 'Antônio Lima',
      balance: '0.00',
    });
    TestBed.configureTestingModule({
      providers: [
        { provide: LOCAL_DB, useValue: db },
        { provide: SyncService, useValue: { kick, run: vi.fn() } },
        { provide: ApiService, useValue: {} },
      ],
    });
    service = TestBed.inject(LedgerService);
    kick.mockClear();
  });

  afterEach(async () => {
    await db.delete();
  });

  it('finds clients ignoring accents and case', async () => {
    const result = await service.clients('ANTONIO');
    expect(result.map((c) => c.name)).toEqual(['Antônio Lima']);
  });

  it('adds a purchase offline and updates the balance right away', async () => {
    const recorded = await service.recordPurchase(joao.id, 2340, 'frutas');

    expect(recorded.client.balance).toBe('110.90');
    expect(recorded.client.over_limit).toBe(true);
    expect(recorded.client.pending).toBe(1);
    expect(await db.outbox.count()).toBe(1);
    expect(kick).toHaveBeenCalled();
  });

  it('subtracts payments from the balance', async () => {
    await service.recordPurchase(joao.id, 2340, '');
    const recorded = await service.recordPayment(joao.id, 5000, 'pix');

    expect(recorded.client.balance).toBe('60.90');
    expect(recorded.client.over_limit).toBe(false);
  });

  it('queues new clients for sync', async () => {
    const client = await service.addClient({
      name: 'Rosa Alves',
      phone: null,
      address: null,
      credit_limit: null,
    });

    const outbox = await db.outbox.get(client.id);
    expect(outbox?.kind).toBe('client');
    expect((await service.clients('rosa'))[0].balance).toBe('0.00');
  });

  it('undoes a purchase that was not sent yet without calling the api', async () => {
    const recorded = await service.recordPurchase(joao.id, 2340, '');

    const result = await service.undo('purchase', recorded.id);

    expect(result).toBe('local');
    expect(await db.outbox.count()).toBe(0);
    expect((await service.client(joao.id))?.balance).toBe('87.50');
  });
});
