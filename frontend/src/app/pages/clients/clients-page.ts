import { Component, effect, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { liveQuery } from 'dexie';
import { AuthService } from '../../core/auth.service';
import { ClientView, LedgerService } from '../../core/ledger.service';
import { formatBRL, toCents } from '../../core/money';
import { Icon } from '../../shared/icon';
import { SyncBadge } from '../../shared/sync-badge';

@Component({
  selector: 'app-clients-page',
  imports: [RouterLink, Icon, SyncBadge],
  templateUrl: './clients-page.html',
})
export class ClientsPage {
  protected readonly auth = inject(AuthService);
  private ledger = inject(LedgerService);

  protected readonly term = signal('');
  protected readonly clients = signal<ClientView[]>([]);
  protected readonly loaded = signal(false);
  protected readonly formatBRL = formatBRL;

  constructor() {
    effect((onCleanup) => {
      const term = this.term();
      const sub = liveQuery(() => this.ledger.clients(term)).subscribe((list) => {
        this.clients.set(list);
        this.loaded.set(true);
      });
      onCleanup(() => sub.unsubscribe());
    });
  }

  protected owes(client: ClientView): boolean {
    return toCents(client.balance) > 0;
  }

  protected maskPhone(phone: string | null): string {
    return phone ? `(${phone.slice(0, 2)}) ••••-${phone.slice(-4)}` : 'Sem telefone';
  }
}
