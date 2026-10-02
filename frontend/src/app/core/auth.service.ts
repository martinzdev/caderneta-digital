import { Injectable, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ApiService } from './api.service';
import { User } from './models';

const USER_KEY = 'caderneta.user';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private api = inject(ApiService);
  private router = inject(Router);

  readonly token = signal<string | null>(null);
  readonly user = signal<User | null>(this.storedUser());
  readonly isOwner = computed(() => this.user()?.role === 'owner');
  private refreshing: Promise<boolean> | null = null;

  async restore(): Promise<void> {
    if (!this.user()) {
      return;
    }
    if (!navigator.onLine) {
      return;
    }
    const ok = await this.refresh();
    if (!ok) {
      this.clear();
    }
  }

  async login(login: string, password: string): Promise<void> {
    const { access_token } = await this.api.login(login.trim().toLowerCase(), password);
    this.token.set(access_token);
    const user = await this.api.me();
    this.user.set(user);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  }

  refresh(): Promise<boolean> {
    this.refreshing ??= this.api
      .refresh()
      .then(({ access_token }) => {
        this.token.set(access_token);
        return true;
      })
      .catch(() => false)
      .finally(() => (this.refreshing = null));
    return this.refreshing;
  }

  async logout(): Promise<void> {
    await this.api.logout().catch(() => undefined);
    this.clear();
    await this.router.navigateByUrl('/entrar');
  }

  private clear(): void {
    this.token.set(null);
    this.user.set(null);
    localStorage.removeItem(USER_KEY);
  }

  private storedUser(): User | null {
    try {
      const raw = localStorage.getItem(USER_KEY);
      return raw ? (JSON.parse(raw) as User) : null;
    } catch {
      return null;
    }
  }
}
