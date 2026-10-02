export type Role = 'owner' | 'staff';
export type PaymentMethod = 'cash' | 'pix' | 'card';
export type OrderStatus = 'new' | 'packed' | 'delivered' | 'canceled';
export type OrderPayment = 'tab' | 'on_delivery';

export interface User {
  id: string;
  name: string;
  role: Role;
}

export interface Client {
  id: string;
  name: string;
  phone: string | null;
  address: string | null;
  credit_limit: string | null;
  active: boolean;
  balance: string;
  over_limit: boolean;
}

export interface Purchase {
  id: string;
  client_id: string;
  amount: string;
  description: string | null;
  created_at: string;
}

export interface Payment {
  id: string;
  client_id: string;
  amount: string;
  method: PaymentMethod;
  created_at: string;
}

export interface RecordResult {
  id: string;
  client_id: string;
  balance: string;
  over_limit: boolean;
  duplicate: boolean;
}

export interface Entry {
  id: string;
  kind: 'purchase' | 'payment';
  amount: string;
  description: string | null;
  method: PaymentMethod | null;
  created_at: string;
  canceled: boolean;
}

export interface Statement {
  client: Client;
  month: string;
  entries: Entry[];
  balance: string;
  text: string;
}

export interface Order {
  id: string;
  client_id: string;
  client_name: string;
  items: string;
  address: string;
  status: OrderStatus;
  payment: OrderPayment;
  created_at: string;
}

export interface Summary {
  month: string;
  total_receivable: string;
  received_in_month: string;
  sold_on_tab_in_month: string;
  top_debtors: { id: string; name: string; balance: string }[];
}

export type OutboxKind = 'client' | 'purchase' | 'payment';

export interface OutboxItem {
  id: string;
  kind: OutboxKind;
  payload: Client | Purchase | Payment;
  created_at: string;
  attempts: number;
  error?: string;
}
