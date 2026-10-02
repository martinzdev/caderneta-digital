import { Component, OnInit, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/api.service';
import { Summary } from '../../core/models';
import { formatBRL } from '../../core/money';
import { SyncService } from '../../core/sync.service';
import { Icon } from '../../shared/icon';

@Component({
  selector: 'app-summary-page',
  imports: [RouterLink, Icon],
  templateUrl: './summary-page.html',
})
export class SummaryPage implements OnInit {
  private api = inject(ApiService);
  protected readonly sync = inject(SyncService);

  protected readonly month = signal(this.currentMonth());
  protected readonly summary = signal<Summary | null>(null);
  protected readonly failed = signal(false);
  protected readonly formatBRL = formatBRL;

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    if (!this.sync.online()) {
      return;
    }
    try {
      this.failed.set(false);
      this.summary.set(await this.api.summary(this.month()));
    } catch {
      this.failed.set(true);
    }
  }

  async changeMonth(value: string): Promise<void> {
    if (/^\d{4}-\d{2}$/.test(value)) {
      this.month.set(value);
      await this.load();
    }
  }

  private currentMonth(): string {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
  }
}
