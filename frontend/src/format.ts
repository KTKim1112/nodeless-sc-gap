/**
 * Number formatting for display.
 *
 * Kept apart from the components so that "how many digits" is decided once.
 * Showing more digits than the uncertainty supports is a way of lying quietly,
 * so `withError` truncates the value to match its own error bar.
 */
import type { FittedParameter, ParameterDistribution } from './api/client'

/** A plain number, switching to exponential where a fixed form is unreadable. */
export function fmt(value: number | null | undefined, digits = 4): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  const abs = Math.abs(value)
  if (abs !== 0 && (abs < 1e-3 || abs >= 1e6)) return value.toExponential(3)
  return value.toLocaleString('ko-KR', {
    maximumFractionDigits: digits,
    minimumFractionDigits: 0,
  })
}

/**
 * Round a value to the precision its uncertainty justifies.
 *
 * The convention is two significant figures on the error and the value matched
 * to it, so that 250.0421 +/- 0.0536 shows as 250.042 +/- 0.054 rather than
 * inviting the reader to believe the last three digits.
 */
export function withError(value: number, stderr: number | null | undefined): string {
  if (stderr === null || stderr === undefined || !Number.isFinite(stderr) || stderr <= 0) {
    return fmt(value)
  }
  const exponent = Math.floor(Math.log10(Math.abs(stderr)))
  const decimals = Math.max(0, Math.min(10, -(exponent - 1)))
  if (Math.abs(value) >= 1e6 || (Math.abs(value) < 1e-3 && value !== 0)) {
    return `${value.toExponential(3)} ± ${stderr.toExponential(1)}`
  }
  return `${value.toFixed(decimals)} ± ${stderr.toFixed(decimals)}`
}

export function parameter(p: FittedParameter | undefined | null): string {
  if (!p) return '—'
  return withError(p.value, p.stderr ?? null) + (p.fixed ? ' (고정)' : '')
}

export function distribution(d: ParameterDistribution | undefined | null): string {
  if (!d) return '—'
  return withError(d.mean, d.std)
}

export function interval(d: ParameterDistribution | undefined | null): string {
  if (!d) return '—'
  return `[${fmt(d.ci_low)}, ${fmt(d.ci_high)}]`
}

/**
 * A fixed number of decimals, trailing zeros kept.
 *
 * For columns of numbers. `fmt` drops trailing zeros, which leaves 45.02, 44.99
 * and 45 in the same column with their decimal points out of line and the eye
 * unable to compare them at a glance. Tabular figures only align if every cell
 * has the same number of digits after the point.
 */
export function fixed(value: number | null | undefined, decimals: number): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return '—'
  const abs = Math.abs(value)
  if (abs !== 0 && (abs < 1e-3 || abs >= 1e7)) return value.toExponential(3)
  return value.toFixed(decimals)
}

/** Percentages for progress bars and the like. */
export function percent(fraction: number, digits = 0): string {
  return `${(fraction * 100).toFixed(digits)}%`
}
