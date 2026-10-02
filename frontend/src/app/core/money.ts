const formatter = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

export function toCents(value: string | number | null | undefined): number {
  if (value === null || value === undefined || value === '') {
    return 0;
  }
  return Math.round(Number(value) * 100);
}

export function fromCents(cents: number): string {
  return (cents / 100).toFixed(2);
}

export function formatBRL(value: string | number | null | undefined): string {
  return formatter.format(toCents(value) / 100).replace(/ /g, ' ');
}

export function parseAmount(input: string): number | null {
  const clean = input.trim().replace(/\s/g, '').replace(/^R\$/i, '');
  if (!/^\d{1,8}([.,]\d{1,2})?$/.test(clean)) {
    return null;
  }
  const cents = Math.round(Number(clean.replace(',', '.')) * 100);
  return cents > 0 ? cents : null;
}

export function maskAmount(digits: string): string {
  const only = digits.replace(/\D/g, '').replace(/^0+/, '').slice(0, 9);
  const padded = only.padStart(3, '0');
  return `${padded.slice(0, -2)},${padded.slice(-2)}`;
}
