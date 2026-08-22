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

type Tab = 'rho_s' | 'lambda' | 'residuals'

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
