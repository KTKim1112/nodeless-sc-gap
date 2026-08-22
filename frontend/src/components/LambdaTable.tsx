/**
 * The per-temperature table: what equation (1) gave at each measured point.
 *
 * This is the intermediate the two-step route produces and the direct route
 * skips, and it is worth showing either way -- kappa(T) leaving the strong
 * type-II range is visible here before it shows up as a warning.
 */
import type { LambdaResponse } from '../api/client'
import { fmt } from '../format'

interface Props {
  table: LambdaResponse
  maxRows?: number
}

export function LambdaTable({ table, maxRows = 200 }: Props) {
  const n = table.temperature_K.length
  const shown = Math.min(n, maxRows)

  return (
    <section className="card">
      <h2>온도별 결과</h2>

      <div className="table-scroll tall">
        <table className="results numeric">
          <thead>
            <tr>
              <th>T [K]</th>
              <th>Jc [A/m²]</th>
              <th>ξ [nm]</th>
              <th>λ [nm]</th>
              <th>κ = λ/ξ</th>
            </tr>
          </thead>
          <tbody>
            {Array.from({ length: shown }, (_, i) => (
              <tr key={i}>
                <td>{fmt(table.temperature_K[i], 3)}</td>
                <td>{table.jc_A_per_m2[i].toExponential(3)}</td>
                <td>{fmt(table.xi_nm[i], 3)}</td>
                <td>{fmt(table.lambda_nm[i], 2)}</td>
                <td>{fmt(table.kappa[i], 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {shown < n && (
        <p className="muted small">
          {n}개 중 처음 {shown}개만 표시했습니다. 전체는 CSV로 내려받으세요.
        </p>
      )}
    </section>
  )
}
