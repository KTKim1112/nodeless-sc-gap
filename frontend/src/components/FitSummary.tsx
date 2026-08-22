/**
 * The answer: lambda(0), Delta(0), Tc, and the coupling ratio.
 *
 * An unconverged fit is refused rather than displayed (FR-014). A number that
 * the optimiser did not stand behind looks exactly like one it did, so the only
 * safe place to stop it is here.
 */
import type { AnalyzeResponse } from '../api/client'
import { fmt, parameter } from '../format'
import { LABELS } from '../errorMessages'

interface Props {
  result: AnalyzeResponse
}

export function FitSummary({ result }: Props) {
  const { fit, diagnostics, uncertainty } = result

  if (!fit.converged) {
    return (
      <section className="card">
        <h2>피팅 결과</h2>
        <p className="message error">
          피팅이 수렴하지 않아 결과를 표시하지 않습니다. 온도 범위가 좁거나 데이터 산포가
          큰 경우입니다. 저온 데이터를 늘리거나 Tc를 고정해 보세요.
        </p>
      </section>
    )
  }

  const bcs = diagnostics.bcs_ratio_reference
  const ratio = fit.coupling_ratio.value

  const rows = [
    {
      label: 'λ(0)',
      unit: 'nm',
      note: '침투깊이. 초전도 밀도 ns/m*를 결정합니다.',
      fit: parameter(fit.lambda0_nm),
      mc: uncertainty?.lambda0_nm,
    },
    {
      label: 'Δ(0)',
      unit: 'meV',
      note: '초전도 갭.',
      fit: parameter(fit.delta0_meV),
      mc: uncertainty?.delta0_meV,
    },
    {
      label: 'Tc',
      unit: 'K',
      note: fit.tc_K.fixed ? '사용자가 고정한 값입니다.' : '피팅으로 결정된 값입니다.',
      fit: parameter(fit.tc_K),
      mc: uncertainty?.tc_K,
    },
    {
      label: '2Δ(0)/k_BTc',
      unit: '',
      note: `결합 세기. BCS 약결합 값은 ${bcs}입니다.`,
      fit: parameter(fit.coupling_ratio),
      mc: uncertainty?.coupling_ratio,
    },
  ]

  return (
    <section className="card">
      <h2>피팅 결과</h2>

      <div className="table-scroll">
        <table className="results">
          <thead>
            <tr>
              <th>물리량</th>
              <th>단위</th>
              <th>값 ± 피팅 오차</th>
              {uncertainty && <th>측정 오차 전파</th>}
              <th className="note-col">비고</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row" className="quantity">{row.label}</th>
                <td className="unit">{row.unit || '—'}</td>
                <td className="value">{row.fit}</td>
                {uncertainty && (
                  <td className="value">
                    {row.mc
                      ? `${fmt(row.mc.mean)} ± ${fmt(row.mc.std)}`
                      : '—'}
                  </td>
                )}
                <td className="note muted small">{row.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="badges">
        <span className={`badge regime-${diagnostics.coupling_regime}`}>
          {LABELS.couplingRegime[diagnostics.coupling_regime]}
        </span>
        <span className="badge subtle">
          {LABELS.gapModel[fit.gap_model]}
        </span>
        <span className="badge subtle">
          {LABELS.fitRoute[fit.fit_route]}
        </span>
        <span className="badge subtle">
          χ²_red = {fmt(fit.chi2_reduced)}
        </span>
        <span className="badge subtle">
          자유도 {fit.n_points} − {fit.n_free_parameters}
        </span>
      </div>

      <p className="muted small">
        2Δ(0)/k_BTc = {fmt(ratio)}는 BCS 약결합 값 {bcs}의{' '}
        {fmt((ratio / bcs) * 100, 1)}%입니다.
        {uncertainty && (
          <>
            {' '}측정 오차 전파는 {uncertainty.n_valid}/{uncertainty.n_requested} 표본,
            seed {uncertainty.settings.seed},{' '}
            {LABELS.correlationMode[uncertainty.settings.correlation_mode ?? 'SYSTEMATIC']}
            {' '}기준입니다.
          </>
        )}
      </p>

      {uncertainty && (
        <p className="muted small">
          피팅 오차와 측정 오차 전파는 서로 다른 것을 재는 값이라 합치지 않고 따로
          보여줍니다. 전자는 데이터가 모델 주위로 얼마나 흩어져 있는지를, 후자는 입력값이
          말씀하신 만큼 틀렸을 때 결과가 얼마나 움직이는지를 나타냅니다.
        </p>
      )}
    </section>
  )
}
