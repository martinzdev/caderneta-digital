import { Component, computed, inject } from '@angular/core';
import { SyncService } from '../core/sync.service';
import { Icon } from './icon';

@Component({
  selector: 'app-sync-badge',
  imports: [Icon],
  template: `
    <p
      role="status"
      aria-live="polite"
      class="inline-flex items-center gap-2 rounded-full border-2 px-3 py-1 text-sm font-semibold"
      [class]="tone()"
    >
      <app-icon [name]="icon()" [size]="20" />
      {{ label() }}
    </p>
  `,
})
export class SyncBadge {
  private sync = inject(SyncService);

  protected readonly label = computed(() => {
    const pending = this.sync.pending();
    const failed = this.sync.failed();
    if (failed) {
      return failed === 1 ? '1 registro recusado' : `${failed} registros recusados`;
    }
    if (!this.sync.online()) {
      return pending ? `Sem internet · ${pending} para enviar` : 'Sem internet';
    }
    if (pending) {
      return pending === 1 ? '1 pendente de envio' : `${pending} pendentes de envio`;
    }
    return 'Tudo enviado';
  });

  protected readonly icon = computed(() => {
    if (this.sync.failed()) {
      return 'alert';
    }
    return this.sync.online() ? 'cloud' : 'cloud-off';
  });

  protected readonly tone = computed(() => {
    if (this.sync.failed()) {
      return 'border-red-700 bg-red-50 text-red-800';
    }
    if (!this.sync.online() || this.sync.pending()) {
      return 'border-amber-700 bg-amber-50 text-amber-900';
    }
    return 'border-brand-700 bg-brand-50 text-brand-800';
  });
}
