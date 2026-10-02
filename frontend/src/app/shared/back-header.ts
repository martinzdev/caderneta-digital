import { Component, input } from '@angular/core';
import { RouterLink } from '@angular/router';
import { Icon } from './icon';

@Component({
  selector: 'app-back-header',
  imports: [RouterLink, Icon],
  template: `
    <header class="flex items-center gap-2 bg-brand-900 px-2 py-3 text-white">
      <a
        [routerLink]="backTo()"
        class="flex min-h-12 min-w-12 items-center gap-1 rounded-xl px-2 text-lg font-semibold"
      >
        <app-icon name="back" [size]="28" />
        Voltar
      </a>
      <h1 class="flex-1 truncate pr-4 text-center text-xl font-bold">{{ title() }}</h1>
    </header>
  `,
})
export class BackHeader {
  readonly title = input.required<string>();
  readonly backTo = input<string | unknown[]>('/');
}
