import { Component, computed, inject } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { filter, map } from 'rxjs';
import { AuthService } from './core/auth.service';
import { Icon } from './shared/icon';

@Component({
  selector: 'app-root',
  imports: [RouterOutlet, RouterLink, RouterLinkActive, Icon],
  templateUrl: './app.html',
})
export class App {
  protected readonly auth = inject(AuthService);
  private router = inject(Router);

  private url = toSignal(
    this.router.events.pipe(
      filter((e) => e instanceof NavigationEnd),
      map((e) => e.urlAfterRedirects),
    ),
    { initialValue: this.router.url },
  );

  protected readonly showNav = computed(
    () => !!this.auth.user() && !this.url().startsWith('/entrar'),
  );

  protected readonly tabs = [
    { path: '/', label: 'Clientes', icon: 'users', exact: true },
    { path: '/pedidos', label: 'Pedidos', icon: 'truck', exact: false },
    { path: '/resumo', label: 'Resumo', icon: 'chart', exact: false },
  ];
}
