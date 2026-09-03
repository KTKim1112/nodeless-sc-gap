/**
 * The plots. FR-026 and FR-019.
 *
 * Two things the numbers alone cannot tell you. Whether the model actually
 * follows the data -- a small chi-squared is compatible with a systematic
 * departure that is obvious the moment the curve is drawn through the points.
 * And whether the residuals scatter about zero or drift, which is the
 * difference between noise and the wrong model.
 */
import { useMemo, useState } from 'react'
import type { Data } from 'plotly.js'
import type { AnalyzeResponse } from '../api/client'
import { LABELS } from '../errorMessages'
import { Plot } from './Plot'

interface Props {
  result: AnalyzeResponse
}

type Tab = 'rho_s' | 'lambda' | 'jc' | 'residuals'

const TABS: { id: Tab; label: string; hint: string }[] = [
  {
    id: 'rho_s',
    label: '초전도 밀도 ρs(T)',
    hint: '갭이 결정되는 곳입니다. 저온에서 곡선이 1에 얼마나 평평하게 붙는지가 Δ(0)를 정합니다.',
  },
  {
    id: 'lambda',
    label: '침투깊이 λ(T)',
    hint: 'Tc 근처에서 발산합니다. 세로축이 로그인 이유입니다.',
  },
  {
    id: 'jc',
    label: '임계전류밀도 Jc(T)',
    hint: '측정값과 피팅 곡선입니다. κ를 고정한 경우가 아니면 곡선은 측정 온도 범위 안에서만 그려집니다 — 식 (1)에는 λ 외에 ξ도 필요한데, 측정 범위 밖에는 보간할 두 점이 없기 때문입니다.',
  },
  {
    id: 'residuals',
    label: '잔차',
    hint: '0 주위로 흩어져야 합니다. 한쪽으로 휘어 있으면 모델이 맞지 않는다는 뜻입니다.',
  },
]

export function Charts({ result }: Props) {
  const [tab, setTab] = useState<Tab>('rho_s')
  const { lambda_table: table, curve, fit } = result

  const marker = { size: 7, symbol: 'circle-open' as const, line: { width: 1.6 } }
  const modelName = `${LABELS.gapModel[fit.gap_model]} 피팅`

  const rhoData = useMemo<Data[]>(() => [
    {
      x: table.temperature_K,
      y: fit.rho_s_measured,
      mode: 'markers',
      type: 'scatter',
      name: '측정',
      marker,
    },
    {
      x: curve.temperature_K,
      y: curve.rho_s,
      mode: 'lines',
      type: 'scatter',
      name: modelName,
      line: { width: 2 },
    },
  ], [table, curve, fit, modelName])

  const lambdaData = useMemo<Data[]>(() => [
    {
      x: table.temperature_K,
      y: table.lambda_nm,
      mode: 'markers',
      type: 'scatter',
      name: '측정',
      marker,
    },
    {
      x: curve.temperature_K,
      y: curve.lambda_nm,
      mode: 'lines',
      type: 'scatter',
      name: modelName,
      line: { width: 2 },
    },
  ], [table, curve, modelName])

  // Drawn from the same dense curve as the two plots above, and stopping where
  // the measurements do unless kappa was fixed (FR-026a). The backend sends
  // null wherever equation (1) has no coherence length to work with, which
  // Plotly reads as a break in the line rather than as a point at zero.
  const jcData = useMemo<Data[]>(() => [
    {
      x: table.temperature_K,
      y: table.jc_A_per_m2,
      mode: 'markers',
      type: 'scatter',
      name: '측정',
      marker,
    },
    {
      x: curve.temperature_K,
      y: curve.jc_A_per_m2,
      mode: 'lines',
      type: 'scatter',
      name: modelName,
      line: { width: 2 },
    },
  ], [table, curve, modelName])

  // Under a fixed kappa the curve runs all the way to Tc, where Jc has fallen
  // by four orders of magnitude; left to itself the logarithmic axis would fit
  // all of that in and squash the measurements into a strip at the top. The
  // range is taken from the measured values instead, so the curve leaves the
  // frame rather than the data leaving the eye. Choosing an axis range is
  // presentation, not a physical quantity.
  const jcRange = useMemo(() => {
    const positive = table.jc_A_per_m2.filter((v) => v > 0)
    if (positive.length === 0) return undefined
    return [
      Math.log10(Math.min(...positive) / 3),
      Math.log10(Math.max(...positive) * 3),
    ]
  }, [table])

  const residualData = useMemo<Data[]>(() => [
    {
      x: table.temperature_K,
      y: fit.residuals,
      mode: 'markers',
      type: 'scatter',
      name: '잔차',
      marker,
    },
  ], [table, fit])

  const shared = { xaxis: { title: { text: '온도 T [K]' } } }

  return (
    <section className="card">
      <h2>그래프</h2>

      <div className="tabs" role="tablist">
        {TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            role="tab"
            aria-selected={tab === t.id}
            className={tab === t.id ? 'tab active' : 'tab'}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'rho_s' && (
        <Plot
          filename="rho_s"
          data={rhoData}
          layout={{
            ...shared,
            yaxis: { title: { text: 'ρs = λ²(0)/λ²(T)' }, range: [0, 1.05] },
          }}
        />
      )}

      {tab === 'lambda' && (
        <Plot
          filename="lambda"
          data={lambdaData}
          layout={{
            ...shared,
            yaxis: { title: { text: 'λ [nm]' }, type: 'log' },
          }}
        />
      )}

      {tab === 'jc' && (
        <Plot
          filename="jc"
          data={jcData}
          layout={{
            ...shared,
            // exponentformat: Jc runs to ~1e10 A/m2, and Plotly's default
            // labels that as "10B". Powers of ten instead, because a billion
            // is a word with two meanings and this axis has a unit.
            yaxis: {
              title: { text: 'Jc [A/m²]' },
              type: 'log',
              exponentformat: 'power',
              range: jcRange,
            },
          }}
        />
      )}

      {tab === 'residuals' && (
        <Plot
          filename="residuals"
          data={residualData}
          layout={{
            ...shared,
            yaxis: {
              title: {
                text: fit.fit_route === 'TWO_STEP'
                  ? 'ln λ_model − ln λ_측정'
                  : 'ln Jc_측정 − ln Jc_model',
              },
              zeroline: true,
              zerolinewidth: 1.5,
            },
            showlegend: false,
          }}
        />
      )}

      <p className="muted small">
        {TABS.find((t) => t.id === tab)?.hint}
        {' '}그래프 오른쪽 위 사진 아이콘으로 PNG 저장, 드래그로 확대할 수 있습니다.
      </p>
    </section>
  )
}
