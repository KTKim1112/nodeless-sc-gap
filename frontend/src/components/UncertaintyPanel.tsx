/**
 * Propagating the measurement uncertainty. FR-015 to FR-018, FR-029, FR-030.
 *
 * The correlation mode is the control that matters here and it is easy to get
 * wrong, so it is explained rather than merely offered: the same stated "5 % on
 * Jc" moves the gap by nothing at all or by several per cent depending on which
 * kind of error it is (research R8.3).
 *
 * The run is a background job because it takes tens of seconds to minutes, and
 * the page has to stay usable while it goes (FR-018).
 */
import { useEffect, useRef, useState } from 'react'
import {
  api,
  ApiError,
  type AnalyzeRequest,
  type CoherenceSource,
  type UncertaintyResult,
  type UncertaintySettings,
} from '../api/client'
import { errorMessage, LABELS } from '../errorMessages'
import { percent } from '../format'

export const DEFAULT_UNCERTAINTY: UncertaintySettings = {
  jc_error_percent: 5,
  hc2_error_percent: 0,
  xi_error_percent: 0,
  kappa_error_percent: 0,
  correlation_mode: 'SYSTEMATIC',
  n_samples: 5000,
  confidence_percent: 68.27,
  seed: 12345,
}

interface Props {
  request: AnalyzeRequest | null
  coherenceSource: CoherenceSource
  onResult: (result: UncertaintyResult) => void
}

type Phase = 'idle' | 'running' | 'failed'

export function UncertaintyPanel({ request, coherenceSource, onResult }: Props) {
  const [settings, setSettings] = useState<UncertaintySettings>(DEFAULT_UNCERTAINTY)
  const [phase, setPhase] = useState<Phase>('idle')
  const [progress, setProgress] = useState(0)
  const [problem, setProblem] = useState<string | null>(null)
  const polling = useRef<number | null>(null)

  // Stop polling if the component goes away mid-run.
  useEffect(() => () => { if (polling.current) window.clearInterval(polling.current) }, [])

  const set = (patch: Partial<UncertaintySettings>) => setSettings({ ...settings, ...patch })

  /** Which second-quantity uncertainty applies depends on how xi was found. */
  const second = {
    FROM_HC2: { key: 'hc2_error_percent', label: 'Hc2 오차 [%]' },
    EXPLICIT_XI: { key: 'xi_error_percent', label: 'ξ 오차 [%]' },
    FIXED_KAPPA: { key: 'kappa_error_percent', label: 'κ 오차 [%]' },
  }[coherenceSource] as { key: keyof UncertaintySettings; label: string }

  async function run() {
    if (!request) return
    setPhase('running')
    setProgress(0)
    setProblem(null)

    let jobId: string
    try {
      // Only the uncertainty that applies to the chosen method is sent; the
      // others would be ignored, and sending them would suggest otherwise.
      const applicable: UncertaintySettings = {
        ...DEFAULT_UNCERTAINTY,
        jc_error_percent: settings.jc_error_percent,
        [second.key]: settings[second.key],
        correlation_mode: settings.correlation_mode,
        n_samples: settings.n_samples,
        confidence_percent: settings.confidence_percent,
        seed: settings.seed,
      }
      ;({ job_id: jobId } = await api.startUncertainty({ ...request, uncertainty: applicable }))
    } catch (e) {
      setPhase('failed')
      setProblem(e instanceof ApiError ? errorMessage(e.code, e.params) : String(e))
      return
    }

    polling.current = window.setInterval(async () => {
      try {
        const job = await api.job(jobId)
        setProgress(job.progress)
        if (job.state === 'SUCCEEDED' && job.result) {
          window.clearInterval(polling.current!)
          setPhase('idle')
          onResult(job.result)
        } else if (job.state === 'FAILED') {
          window.clearInterval(polling.current!)
          setPhase('failed')
          setProblem(job.error
            ? errorMessage(job.error.code, job.error.params as Record<string, unknown>)
            : '계산이 실패했습니다.')
        }
      } catch (e) {
        window.clearInterval(polling.current!)
        setPhase('failed')
        setProblem(e instanceof ApiError ? errorMessage(e.code, e.params) : String(e))
      }
    }, 1000)
  }

  const running = phase === 'running'

  return (
    <section className="card">
      <h2>측정 오차 전파 (선택)</h2>

      <p className="muted small">
        측정값이 말씀하신 만큼 틀렸을 때 Δ(0)와 λ(0)가 얼마나 움직이는지를
        Monte Carlo로 계산합니다. 표본마다 전체 분석을 다시 돌리므로 수십 초 걸립니다.
      </p>

      <div className="fields">
        <label className="field">
          <span className="label">Jc 오차 [%]</span>
          <input
            type="number" step="any" min="0" disabled={running}
            value={settings.jc_error_percent ?? 0}
            onChange={(e) => set({ jc_error_percent: Number(e.target.value) })}
          />
          <span className="hint">
            1-sigma 상대오차. Ic와 시료 폭·두께의 오차를 합치면
            √(σI/I)² + (σw/w)² + (σt/t)² 입니다.
          </span>
        </label>

        <label className="field">
          <span className="label">{second.label}</span>
          <input
            type="number" step="any" min="0" disabled={running}
            value={(settings[second.key] as number) ?? 0}
            onChange={(e) => set({ [second.key]: Number(e.target.value) } as Partial<UncertaintySettings>)}
          />
          <span className="hint">
            Hc2 오차는 λ에 거의 영향이 없습니다. κ = 40에서 Jc 5%가 1.81% 기여할 때
            Hc2 3%는 0.13%입니다.
          </span>
        </label>

        <label className="field">
          <span className="label">오차의 성격</span>
          <select
            disabled={running}
            value={settings.correlation_mode ?? 'SYSTEMATIC'}
            onChange={(e) =>
              set({ correlation_mode: e.target.value as UncertaintySettings['correlation_mode'] })
            }
          >
            {(['SYSTEMATIC', 'INDEPENDENT'] as const).map((v) => (
              <option key={v} value={v}>{LABELS.correlationMode[v]}</option>
            ))}
          </select>
          <span className="hint">
            {settings.correlation_mode === 'SYSTEMATIC'
              ? '시료 폭·두께 보정 오차처럼 모든 온도에 같은 배율로 걸리는 오차입니다. '
                + 'λ(0)만 움직이고 Δ(0)는 거의 그대로입니다 — ρs가 비율이라 배율이 소거되기 때문입니다.'
              : '온도마다 제각각인 산포입니다. Δ(0)까지 움직이며, 점이 많을수록 1/√n로 줄어듭니다.'}
          </span>
        </label>

        <label className="field">
          <span className="label">표본 수</span>
          <input
            type="number" step="100" min="100" max="200000" disabled={running}
            value={settings.n_samples ?? 5000}
            onChange={(e) => set({ n_samples: Number(e.target.value) })}
          />
          <span className="hint">
            늘려도 오차가 작아지지는 않고 안정될 뿐입니다. 5000이면 오차의 오차가 1%입니다.
          </span>
        </label>

        <label className="field">
          <span className="label">신뢰구간 [%]</span>
          <input
            type="number" step="any" min="1" max="99.9" disabled={running}
            value={settings.confidence_percent ?? 68.27}
            onChange={(e) => set({ confidence_percent: Number(e.target.value) })}
          />
          <span className="hint">68.27은 가우시안의 1σ, 95는 약 2σ에 해당합니다.</span>
        </label>

        <label className="field">
          <span className="label">난수 seed</span>
          <input
            type="number" step="1" disabled={running}
            value={settings.seed ?? 12345}
            onChange={(e) => set({ seed: Number(e.target.value) })}
          />
          <span className="hint">
            같은 seed는 항상 같은 결과를 냅니다. 논문에 적어두면 재현할 수 있습니다.
          </span>
        </label>
      </div>

      <div className="actions">
        <button type="button" disabled={!request || running} onClick={() => void run()}>
          {running ? '계산 중…' : '오차 전파 실행'}
        </button>
        {running && (
          <div className="progress" role="progressbar" aria-valuenow={Math.round(progress * 100)}>
            <div className="bar" style={{ width: percent(progress, 1) }} />
            <span className="label">{percent(progress)}</span>
          </div>
        )}
      </div>

      {problem && <p className="message error">{problem}</p>}
    </section>
  )
}
