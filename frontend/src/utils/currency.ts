/**
 * Currency Formatting and Normalization Utility for EvidenceBridge.
 * Enforces consistent symbols, locale formatting, and transparency across USD, INR, EUR, and GBP.
 */

export type SupportedCurrency = 'INR' | 'USD' | 'EUR' | 'GBP'

/**
 * Normalizes an arbitrary currency string to a recognized ISO currency code.
 * Defaults to 'INR' (Indian Rupees) as the application standard when unrecognized or null/undefined.
 * Preserves explicit foreign currency strings ($ / USD, € / EUR, £ / GBP).
 */
export function normalizeCurrencyCode(currency?: string | null): SupportedCurrency {
  if (!currency) return 'INR'
  const c = currency.trim().toUpperCase()
  if (c === 'USD' || c === 'DOLLAR' || c === 'DOLLARS' || c === '$') {
    return 'USD'
  }
  if (c === 'EUR' || c === 'EURO' || c === 'EUROS' || c === '€') {
    return 'EUR'
  }
  if (c === 'GBP' || c === 'POUND' || c === 'POUNDS' || c === '£') {
    return 'GBP'
  }
  if (
    c === 'INR' ||
    c === 'RS' ||
    c === 'RS.' ||
    c === 'RUPEES' ||
    c === 'RUPEE' ||
    c === '₹'
  ) {
    return 'INR'
  }
  return 'INR'
}

/**
 * Returns the recognized typographical symbol for a currency code.
 * Defaults to '₹' (Indian Rupees).
 */
export function getCurrencySymbol(currency?: string | null): string {
  const code = normalizeCurrencyCode(currency)
  switch (code) {
    case 'USD':
      return '$'
    case 'EUR':
      return '€'
    case 'GBP':
      return '£'
    case 'INR':
    default:
      return '₹'
  }
}

/**
 * Formats a numeric monetary value with the correct currency symbol and locale grouping.
 * Transparently falls back to a clean message (default: "Price data not available") when null/undefined.
 * Defaults to 'INR' with Indian number grouping (en-IN).
 */
export function formatCurrency(
  val?: number | null,
  currency: string = 'INR',
  options?: {
    showCode?: boolean
    fallback?: string
    minimumFractionDigits?: number
    maximumFractionDigits?: number
  }
): string {
  if (val === null || val === undefined || isNaN(val)) {
    return options?.fallback ?? 'Price data not available'
  }

  const code = normalizeCurrencyCode(currency)
  const symbol = getCurrencySymbol(code)

  const minDigits = options?.minimumFractionDigits ?? (code === 'INR' && val % 1 === 0 ? 0 : 2)
  const maxDigits = options?.maximumFractionDigits ?? 2

  let formattedNum = ''
  switch (code) {
    case 'INR':
      formattedNum = val.toLocaleString('en-IN', {
        minimumFractionDigits: minDigits,
        maximumFractionDigits: maxDigits,
      })
      break
    case 'EUR':
      formattedNum = val.toLocaleString('de-DE', {
        minimumFractionDigits: minDigits,
        maximumFractionDigits: maxDigits,
      })
      break
    case 'GBP':
      formattedNum = val.toLocaleString('en-GB', {
        minimumFractionDigits: minDigits,
        maximumFractionDigits: maxDigits,
      })
      break
    case 'USD':
    default:
      formattedNum = val.toLocaleString('en-US', {
        minimumFractionDigits: minDigits,
        maximumFractionDigits: maxDigits,
      })
      break
  }

  const result = `${symbol}${formattedNum}`
  return options?.showCode ? `${result} ${code}` : result
}
