import { HttpErrorResponse } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../core/auth.service';
import { SyncService } from '../../core/sync.service';

@Component({
  selector: 'app-login-page',
  imports: [ReactiveFormsModule],
  templateUrl: './login-page.html',
})
export class LoginPage {
  private auth = inject(AuthService);
  private sync = inject(SyncService);
  private router = inject(Router);

  protected readonly form = inject(FormBuilder).nonNullable.group({
    login: ['', Validators.required],
    password: ['', Validators.required],
  });
  protected readonly error = signal('');
  protected readonly loading = signal(false);

  async submit(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.error.set('Preencha o usuário e a senha.');
      return;
    }
    if (!navigator.onLine) {
      this.error.set('Para entrar pela primeira vez é preciso estar conectado à internet.');
      return;
    }
    this.loading.set(true);
    this.error.set('');
    try {
      const { login, password } = this.form.getRawValue();
      await this.auth.login(login, password);
      this.sync.kick();
      await this.router.navigateByUrl('/');
    } catch (err) {
      const status = err instanceof HttpErrorResponse ? err.status : 0;
      this.error.set(
        status === 429
          ? 'Muitas tentativas. Aguarde 15 minutos e tente de novo.'
          : status === 401
            ? 'Usuário ou senha inválidos.'
            : 'Não foi possível entrar agora. Tente novamente.',
      );
    } finally {
      this.loading.set(false);
    }
  }
}
