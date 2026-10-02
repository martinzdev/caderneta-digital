import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { LedgerService } from '../../core/ledger.service';
import { fromCents, parseAmount } from '../../core/money';
import { BackHeader } from '../../shared/back-header';

@Component({
  selector: 'app-new-client-page',
  imports: [ReactiveFormsModule, BackHeader],
  templateUrl: './new-client-page.html',
})
export class NewClientPage {
  private ledger = inject(LedgerService);
  private router = inject(Router);

  protected readonly form = inject(FormBuilder).nonNullable.group({
    name: ['', [Validators.required, Validators.maxLength(100)]],
    phone: [''],
    address: ['', Validators.maxLength(200)],
    limit: [''],
  });
  protected readonly errors = signal<Record<string, string>>({});
  protected readonly saving = signal(false);

  async save(): Promise<void> {
    const { name, phone, address, limit } = this.form.getRawValue();
    const digits = phone.replace(/\D/g, '');
    const limitCents = limit.trim() ? parseAmount(limit) : null;
    const errors: Record<string, string> = {};

    if (!name.trim()) {
      errors['name'] = 'Digite o nome do cliente.';
    } else if (/[<>]/.test(name)) {
      errors['name'] = 'O nome não pode ter os sinais < ou >.';
    }
    if (digits && !/^\d{10,11}$/.test(digits)) {
      errors['phone'] = 'Digite o telefone com DDD, por exemplo 69 99999-1234.';
    }
    if (limit.trim() && limitCents === null) {
      errors['limit'] = 'Digite um valor válido, por exemplo 100,00.';
    }
    this.errors.set(errors);
    if (Object.keys(errors).length) {
      return;
    }

    this.saving.set(true);
    const client = await this.ledger.addClient({
      name: name.trim(),
      phone: digits || null,
      address: address.trim() || null,
      credit_limit: limitCents === null ? null : fromCents(limitCents),
    });
    await this.router.navigate(['/clientes', client.id], { replaceUrl: true });
  }
}
