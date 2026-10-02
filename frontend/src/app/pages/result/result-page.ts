import { Component, computed, effect, inject, input, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { AuthService } from '../../core/auth.service';
import { ClientView, LedgerService } from '../../core/ledger.service';
import { formatBRL, toCents } from '../../core/money';
import { SyncService } from '../../core/sync.service';
import { BackHeader } from '../../shared/back-header';
import { Icon } from '../../shared/icon';

interface SavedState {
  kind?: 'purchase' | 'payment';
  cents?: number;
  recordId?: string;
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
  private auth = inject(AuthService);

  readonly id = input.required<string>();

  protected readonly saved: SavedState = history.state ?? {};
  protected readonly client = signal<ClientView | null>(null);
  protected readonly statement = signal<string | null>(null);
  protected readonly statementError = signal(false);
  protected readonly formatBRL = formatBRL;
  protected readonly undone = signal(false);
  protected readonly undoError = signal('');
  protected readonly canUndo = signal(false);

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

  async undo(): Promise<void> {
    const { kind, cents, recordId } = this.saved;
    if (!kind || !recordId || !cents) {
      return;
    }
    const label = kind === 'purchase' ? 'a compra' : 'o pagamento';
    if (!confirm(`Desfazer ${label} de ${formatBRL(cents / 100)}?`)) {
      return;
    }
    try {
      await this.ledger.undo(kind, recordId);
      this.undone.set(true);
      this.canUndo.set(false);
      this.statement.set(null);
      await this.load(this.id());
    } catch {
      this.undoError.set('Não foi possível desfazer agora. Tente de novo com internet.');
    }
  }

  private async load(id: string): Promise<void> {
    this.client.set((await this.ledger.client(id)) ?? null);
    const recordId = this.saved.recordId;
    if (recordId && !this.undone()) {
      this.canUndo.set(this.auth.isOwner() || (await this.ledger.isPending(recordId)));
    }
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
