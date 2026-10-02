import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ApiService } from '../../core/api.service';
import { ClientView, LedgerService } from '../../core/ledger.service';
import { Order, OrderPayment, OrderStatus } from '../../core/models';
import { fromCents, parseAmount } from '../../core/money';
import { SyncService } from '../../core/sync.service';
import { Icon } from '../../shared/icon';

const NEXT: Partial<Record<OrderStatus, OrderStatus>> = { new: 'packed', packed: 'delivered' };

@Component({
  selector: 'app-orders-page',
  imports: [Icon],
  templateUrl: './orders-page.html',
})
export class OrdersPage implements OnInit {
  private api = inject(ApiService);
  private ledger = inject(LedgerService);
  protected readonly sync = inject(SyncService);

  protected readonly orders = signal<Order[]>([]);
  protected readonly clients = signal<ClientView[]>([]);
  protected readonly showForm = signal(false);
  protected readonly message = signal('');
  protected readonly busy = signal(false);

  protected readonly clientId = signal('');
  protected readonly items = signal('');
  protected readonly address = signal('');
  protected readonly payment = signal<OrderPayment>('tab');
  protected readonly deliveryAmount = signal<Record<string, string>>({});

  protected readonly open = computed(() =>
    this.orders().filter((o) => o.status === 'new' || o.status === 'packed'),
  );
  protected readonly done = computed(() =>
    this.orders()
      .filter((o) => o.status === 'delivered' || o.status === 'canceled')
      .slice(0, 10),
  );

  protected readonly statusLabel: Record<OrderStatus, string> = {
    new: 'Novo',
    packed: 'Separado',
    delivered: 'Entregue',
    canceled: 'Cancelado',
  };
  protected readonly actionLabel: Partial<Record<OrderStatus, string>> = {
    new: 'Marcar como separado',
    packed: 'Marcar como entregue',
  };

  async ngOnInit(): Promise<void> {
    this.clients.set(await this.ledger.clients());
    await this.reload();
  }

  async reload(): Promise<void> {
    if (!this.sync.online()) {
      return;
    }
    try {
      this.orders.set(await this.api.orders());
    } catch {
      this.message.set('Não foi possível carregar os pedidos agora.');
    }
  }

  protected pickClient(id: string): void {
    this.clientId.set(id);
    this.address.set(this.clients().find((c) => c.id === id)?.address ?? '');
  }

  async create(): Promise<void> {
    if (!this.clientId() || !this.items().trim()) {
      this.message.set('Escolha o cliente e escreva os itens do pedido.');
      return;
    }
    if (!this.address().trim()) {
      this.message.set('Informe o endereço de entrega.');
      return;
    }
    this.busy.set(true);
    try {
      await this.api.createOrder({
        id: crypto.randomUUID(),
        client_id: this.clientId(),
        items: this.items().trim(),
        address: this.address().trim(),
        payment: this.payment(),
        created_at: new Date().toISOString(),
      });
      this.items.set('');
      this.clientId.set('');
      this.address.set('');
      this.showForm.set(false);
      this.message.set('Pedido registrado.');
      await this.reload();
    } catch (err) {
      this.message.set(this.errorText(err));
    } finally {
      this.busy.set(false);
    }
  }

  async advance(order: Order): Promise<void> {
    const next = NEXT[order.status];
    if (!next) {
      return;
    }
    let amount: string | undefined;
    let purchaseId: string | undefined;
    if (next === 'delivered' && order.payment === 'tab') {
      const cents = parseAmount(this.deliveryAmount()[order.id] ?? '');
      if (cents === null) {
        this.message.set('Digite o valor do pedido para anotar no fiado.');
        return;
      }
      amount = fromCents(cents);
      purchaseId = crypto.randomUUID();
    }
    await this.change(order, next, amount, purchaseId);
  }

  async cancel(order: Order): Promise<void> {
    if (confirm(`Cancelar o pedido de ${order.client_name}?`)) {
      await this.change(order, 'canceled');
    }
  }

  protected setAmount(orderId: string, value: string): void {
    this.deliveryAmount.update((map) => ({ ...map, [orderId]: value }));
  }

  private async change(order: Order, status: OrderStatus, amount?: string, purchaseId?: string) {
    this.busy.set(true);
    try {
      await this.api.changeOrderStatus(order.id, status, amount, purchaseId);
      this.message.set(
        `Pedido de ${order.client_name}: ${this.statusLabel[status].toLowerCase()}.`,
      );
      await this.reload();
      this.sync.kick();
    } catch (err) {
      this.message.set(this.errorText(err));
    } finally {
      this.busy.set(false);
    }
  }

  private errorText(err: unknown): string {
    if (err instanceof HttpErrorResponse && err.status === 0) {
      return 'Sem internet. Tente de novo quando conectar.';
    }
    if (err instanceof HttpErrorResponse && typeof err.error?.detail === 'string') {
      return err.error.detail;
    }
    return 'Não foi possível concluir. Tente novamente.';
  }
}
