import { formatBRL, fromCents, parseAmount, toCents } from './money';

describe('money', () => {
  it('parses amounts typed with comma or dot', () => {
    expect(parseAmount('23,40')).toBe(2340);
    expect(parseAmount('23.4')).toBe(2340);
    expect(parseAmount(' R$ 5 ')).toBe(500);
  });

  it('rejects zero, negatives and invalid text', () => {
    for (const value of ['', '0', '0,00', '-5', 'abc', '10,555', '1.000,00']) {
      expect(parseAmount(value)).toBeNull();
    }
  });

  it('converts between cents and API strings', () => {
    expect(toCents('110.90')).toBe(11090);
    expect(toCents(null)).toBe(0);
    expect(fromCents(2340)).toBe('23.40');
  });

  it('formats in brazilian reais', () => {
    expect(formatBRL('1234.5')).toBe('R$ 1.234,50');
    expect(formatBRL(0)).toBe('R$ 0,00');
  });
});
