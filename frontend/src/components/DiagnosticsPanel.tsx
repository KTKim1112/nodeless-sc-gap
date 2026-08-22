/**
 * Whether the result can be trusted. FR-019 to FR-021.
 *
 * The fit summary says what the answer is; this says how much weight it will
 * bear. Two judgements matter most and neither is visible in the parameters:
 * whether the data can tell the two gap models apart at all, and how the
 * coupling ratio sits against the BCS value.
 */
import type { AnalyzeResponse } from '../api/client'
import { LABELS } from '../errorMessages'
import { fmt } from '../format'

interface Props {
  result: AnalyzeResponse
}

export function DiagnosticsPanel({ result }: Props) {
  const d = result.diagnostics
  const bcs = d.bcs_ratio_reference
  const ratio = d.coupling_ratio

  const rows: { label: string; value: string; note: string }[] = [
    {
      label: '적합도 χ²_red',
      value: fmt(d.chi2_reduced),
      note: '잔차의 크기. 그래프 탭의 잔차 그림과 함께 보셔야 의미가 있습니다.',
    },
    {
      label: '결합 세기',
      value: `${fmt(ratio)}  (BCS ${bcs}의 ${fmt((ratio / bcs) * 100, 1)}%)`,
      note: LABELS.couplingRegime[d.coupling_regime],
    },
    {
      label: '저온 도달도 T_min/Tc',
      value: fmt(d.t_min_over_tc, 3),
      note: d.t_min_over_tc <= 0.3
        ? '충분합니다. Δ(0)는 저온의 지수적 거동에서 결정됩니다.'
        : '0.3 이하가 바람직합니다. 위쪽 경고를 확인하세요.',
    },
    {
      label: 'κ 범위',
      value: `${fmt(d.kappa_min, 2)} ~ ${fmt(d.kappa_max, 2)}`,
      note: d.kappa_min >= 5
        ? 'strong type-II 영역입니다. 사용한 Hc1 근사가 유효합니다.'
        : 'κ가 작습니다. 사용한 Hc1 근사의 정확도가 떨어집니다.',
    },
  ]

  const bothFitted = d.chi2_clean !== null && d.chi2_clean !== undefined
    && d.chi2_dirty !== null && d.chi2_dirty !== undefined

  return (
    <section className="card">
      <h2>피팅 품질 진단</h2>

      <div className="table-scroll">
        <table className="results">
          <tbody>
            {rows.map((row) => (
              <tr key={row.label}>
                <th scope="row" className="quantity">{row.label}</th>
                <td className="value">{row.value}</td>
                <td className="note muted small">{row.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {bothFitted && (
        <>
          <h3 className="subhead">clean과 dirty 중 어느 쪽인가</h3>
          <div className="table-scroll">
            <table className="results numeric compact">
              <thead>
                <tr>
                  <th>모델</th>
                  <th>χ²_red</th>
                  <th>판정</th>
                </tr>
              </thead>
              <tbody>
                {([
                  ['CLEAN', d.chi2_clean!],
                  ['DIRTY', d.chi2_dirty!],
                ] as const).map(([model, chi2]) => (
                  <tr key={model}>
                    <td style={{ textAlign: 'left' }}>{LABELS.gapModel[model]}</td>
                    <td>{fmt(chi2)}</td>
                    <td style={{ textAlign: 'left' }}>
                      {d.preferred_model === model
                        ? '선호'
                        : d.preferred_model === null || d.preferred_model === undefined
                          ? '—'
                          : ''}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="muted small">
            {d.preferred_model
              ? `ΔAIC = ${fmt(d.delta_aic, 1)}로 판정 기준 10을 넘으므로 `
                + `${LABELS.gapModel[d.preferred_model]}을 선호합니다. `
                + `상대 지지도 ${fmt((d.preferred_model_weight ?? 0) * 100, 1)}%.`
              : `ΔAIC = ${fmt(d.delta_aic, 1)}로 판정 기준 10에 못 미쳐 어느 쪽인지 `
                + '판정하지 않습니다. 두 모델의 Δ(0)는 약 20% 차이가 나므로, '
                + '보고하실 때 어느 모델을 쓰셨는지 함께 밝히셔야 합니다.'}
            {' '}ΔAIC = m·ln(χ²_나쁨 / χ²_좋음)이며 데이터 점 수 m을 반영합니다.
          </p>
        </>
      )}
    </section>
  )
}
