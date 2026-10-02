import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import { environment } from '../../environments/environment';
import {
  Client,
  Order,
  OrderPayment,
  OrderStatus,
  Payment,
  Purchase,
  RecordResult,
  Statement,
  Summary,
  User,
} from './models';

@Injectable({ providedIn: 'root' })
export class ApiService {
  private http = inject(HttpClient);
  private base = environment.apiUrl;

  login(login: string, password: string) {
    return firstValueFrom(
      this.http.post<{ access_token: string }>(`${this.base}/auth/login`, { login, password }),
    );
  }

  refresh() {
    return firstValueFrom(
      this.http.post<{ access_token: string }>(`${this.base}/auth/refresh`, {}),
    );
  }

  logout() {
    return firstValueFrom(this.http.post<void>(`${this.base}/auth/logout`, {}));
  }

  me() {
    return firstValueFrom(this.http.get<User>(`${this.base}/auth/me`));
  }

  clients() {
    return firstValueFrom(this.http.get<Client[]>(`${this.base}/clients`));
  }

  createClient(client: Partial<Client>) {
    return firstValueFrom(this.http.post<Client>(`${this.base}/clients`, client));
  }

  purchase(data: Purchase) {
    return firstValueFrom(this.http.post<RecordResult>(`${this.base}/purchases`, data));
  }

  payment(data: Payment) {
    return firstValueFrom(this.http.post<RecordResult>(`${this.base}/payments`, data));
  }

  cancelPurchase(id: string) {
    return firstValueFrom(this.http.post<RecordResult>(`${this.base}/purchases/${id}/cancel`, {}));
  }

  cancelPayment(id: string) {
    return firstValueFrom(this.http.post<RecordResult>(`${this.base}/payments/${id}/cancel`, {}));
  }

  statement(clientId: string, month?: string) {
    let params = new HttpParams();
    if (month) {
      params = params.set('month', month);
    }
    return firstValueFrom(
      this.http.get<Statement>(`${this.base}/clients/${clientId}/statement`, { params }),
    );
  }

  orders(status?: OrderStatus) {
    let params = new HttpParams();
    if (status) {
      params = params.set('status_filter', status);
    }
    return firstValueFrom(this.http.get<Order[]>(`${this.base}/orders`, { params }));
  }

  createOrder(data: {
    id: string;
    client_id: string;
    items: string;
    address: string | null;
    payment: OrderPayment;
    created_at: string;
  }) {
    return firstValueFrom(this.http.post<Order>(`${this.base}/orders`, data));
  }

  changeOrderStatus(id: string, status: OrderStatus, amount?: string, purchaseId?: string) {
    return firstValueFrom(
      this.http.post<Order>(`${this.base}/orders/${id}/status`, {
        status,
        amount,
        purchase_id: purchaseId,
      }),
    );
  }

  summary(month?: string) {
    let params = new HttpParams();
    if (month) {
      params = params.set('month', month);
    }
    return firstValueFrom(this.http.get<Summary>(`${this.base}/summary`, { params }));
  }
}
