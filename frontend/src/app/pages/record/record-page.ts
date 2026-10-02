import { Component, effect, inject, input, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ClientView, LedgerService } from '../../core/ledger.service';
import { PaymentMethod } from '../../core/models';
import { formatBRL, maskAmount, parseAmount, toCents } from '../../core/money';
import { BackHeader } from '../../shared/back-header';
import { Icon } from '../../shared/icon';

type Mode = 'purchase' | 'payment';

@Component({
  selector: 'app-record-page',
  imports: [BackHeader, Icon],
  templateUrl: './record-page.html',
})
export class RecordPage {
  private ledger = inject(LedgerService);
  private router = inject(Router);

  readonly id = input.required<string>();

  protected readonly client = signal<ClientView | null>(null);
  protected readonly notFound = signal(false);
  protected readonly mode = signal<Mode>('purchase');
  protected readonly amount = signal('');
  protected readonly description = signal('');
  protected readonly method = signal<PaymentMethod>('cash');
  protected readonly error = signal('');
  protected readonly saving = signal(false);
  protected readonly formatBRL = formatBRL;

  protected readonly methods: { value: PaymentMethod; label: string }[] = [
    { value: 'cash', label: 'Dinheiro' },
    { value: 'pix', label: 'Pix' },
    { value: 'card', label: 'Cartão' },
  ];

  constructor() {
    effect(() => {
      const id = this.id();
      void this.ledger.client(id).then((client) => {
        this.client.set(client ?? null);
        this.notFound.set(!client);
      });
    });
  }

  protected owes(): boolean {
    return toCents(this.client()?.balance) > 0;
  }

  protected onAmount(input: HTMLInputElement): void {
    const masked = maskAmount(input.value);
    input.value = masked;
    this.amount.set(masked);
    this.error.set('');
  }

  protected setMode(mode: Mode): void {
    this.mode.set(mode);
    this.error.set('');
  }

  async save(): Promise<void> {
    const client = this.client();
    if (!client || this.saving()) {
      return;
    }
    const cents = parseAmount(this.amount());
    if (cents === null) {
      this.error.set('Digite um valor maior que zero, por exemplo 23,40.');
      return;
    }
    if (this.description().length > 120) {
      this.error.set('A descrição pode ter no máximo 120 letras.');
      return;
    }
    if (/[<>]/.test(this.description())) {
      this.error.set('A descrição não pode ter os sinais < ou >.');
      return;
    }
    const balance = toCents(client.balance);
    if (
      this.mode() === 'payment' &&
      cents > balance &&
      !confirm(
        `O pagamento é maior que o saldo de ${formatBRL(client.balance)}. Salvar mesmo assim?`,
      )
    ) {
      return;
    }

    this.saving.set(true);
    const result =
      this.mode() === 'purchase'
        ? await this.ledger.recordPurchase(client.id, cents, this.description())
        : await this.ledger.recordPayment(client.id, cents, this.method());
    await this.router.navigate(['/clientes', client.id, 'registro'], {
      replaceUrl: true,
      state: { kind: this.mode(), cents: result.amountCents },
    });
  }
}
