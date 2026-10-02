import { Routes } from '@angular/router';
import { authGuard } from './core/auth.guard';

export const routes: Routes = [
  {
    path: 'entrar',
    title: 'Entrar · Caderneta Digital',
    loadComponent: () => import('./pages/login/login-page').then((m) => m.LoginPage),
  },
  {
    path: '',
    canActivate: [authGuard],
    children: [
      {
        path: '',
        title: 'Clientes · Caderneta Digital',
        loadComponent: () => import('./pages/clients/clients-page').then((m) => m.ClientsPage),
      },
      {
        path: 'clientes/novo',
        title: 'Novo cliente · Caderneta Digital',
        loadComponent: () =>
          import('./pages/new-client/new-client-page').then((m) => m.NewClientPage),
      },
      {
        path: 'clientes/:id',
        title: 'Anotar · Caderneta Digital',
        loadComponent: () => import('./pages/record/record-page').then((m) => m.RecordPage),
      },
      {
        path: 'clientes/:id/registro',
        title: 'Registro salvo · Caderneta Digital',
        loadComponent: () => import('./pages/result/result-page').then((m) => m.ResultPage),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
