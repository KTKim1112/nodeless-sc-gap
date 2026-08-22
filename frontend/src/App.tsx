/**
 * The page.
 *
 * Holds the state, calls the API, and lays the panels out in the order the work
 * happens: data in, check how it was read, choose settings, look at results.
 */
import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  api,
  ApiError,
  type AnalyzeResponse,
  type Dataset,
  type Example,
  type JcUnit,
  type ParseResponse,
  type Settings,
  type XiUnit,
} from './api/client'
import { errorMessage, warningMessage, LABELS } from './errorMessages'
import { ColumnPreview } from './components/ColumnPreview'
import { DataInput } from './components/DataInput'
import { FitSummary } from './components/FitSummary'
import { LambdaTable } from './components/LambdaTable'
import { SettingsPanel } from './components/SettingsPanel'

const DEFAULT_SETTINGS: Settings = {
  coherence_source: 'FROM_HC2',
  kappa_fixed: null,
  gap_model: 'CLEAN',
  fit_route: 'TWO_STEP',
  tc_fixed_K: null,
  film_thickness_nm: null,
}

/** Build the request body from the parsed table and the chosen units. */
function buildDataset(
  parsed: ParseResponse,
  settings: Settings,
  jcUnit: JcUnit,
  xiUnit: XiUnit,
): Dataset {
  const column = (i: number) => parsed.values.map((row) => row[i])
  const dataset: Dataset = {
    temperature_K: column(0),
    jc: column(1),
    jc_unit: jcUnit,
    hc2_T: null,
    xi: null,
    xi_unit: xiUnit,
  }
  if (settings.coherence_source === 'FROM_HC2') dataset.hc2_T = column(2)
  if (settings.coherence_source === 'EXPLICIT_XI') dataset.xi = column(2)
  return dataset
}

export default function App() {
  const [text, setText] = useState('')
  const [parsed, setParsed] = useState<ParseResponse | null>(null)
  const [parseError, setParseError] = useState<string | null>(null)
  /**
   * The text that `parsed` actually describes.
   *
   * Comparing it against the current text is what tells us whether `parsed` is
   * stale. A boolean flag set from the effect does not work: between the click
   * that changes the text and the effect that would set the flag there is a
   * render in which the button is still enabled and `parsed` still holds the
   * previous dataset, so pasting new data and clicking straight away analyses
   * the old data. Derived state has no such window. Found by the end-to-end
   * test doing exactly that, twice.
   */
  const [parsedText, setParsedText] = useState<string | null>(null)

  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS)
  const [jcUnit, setJcUnit] = useState<JcUnit>('A_PER_CM2')
  const [xiUnit, setXiUnit] = useState<XiUnit>('NM')

  const [result, setResult] = useState<AnalyzeResponse | null>(null)
  const [analysisError, setAnalysisError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Parse whenever the text settles. Debounced, because this runs on every
  // keystroke while someone is pasting or editing.
  useEffect(() => {
    if (!text.trim()) {
      setParsed(null)
      setParsedText(null)
      setParseError(null)
      return
    }
    let cancelled = false
    const timer = setTimeout(() => {
      api.parse(text)
        .then((p) => {
          if (cancelled) return
          setParsed(p)
          setParsedText(text)
          setParseError(null)
        })
        .catch((e) => {
          if (cancelled) return
          setParsed(null)
          setParsedText(text)     // this text is known-bad, not merely unparsed
          setParseError(e instanceof ApiError ? errorMessage(e.code, e.params) : String(e))
        })
    }, 250)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [text])

  // A new dataset invalidates whatever was on screen.
  useEffect(() => { setResult(null); setAnalysisError(null) }, [parsed, settings, jcUnit, xiUnit])

  const onExampleChosen = useCallback((example: Example) => {
    setText(example.text)
    setSettings({ ...DEFAULT_SETTINGS, ...example.suggested_settings })
    setJcUnit('A_PER_CM2')
  }, [])

  const columnsNeeded = settings.coherence_source === 'FIXED_KAPPA' ? 2 : 3
  /** `parsed` describes an older version of the text than the one on screen. */
  const stale = text.trim() !== '' && parsedText !== text
  const ready = useMemo(() => {
    if (stale) return false
    if (!parsed || parsed.n_columns < columnsNeeded) return false
    if (settings.coherence_source === 'FIXED_KAPPA' && !settings.kappa_fixed) return false
    return true
  }, [stale, parsed, columnsNeeded, settings])

  async function runAnalysis() {
    if (!parsed) return
    setBusy(true)
    setAnalysisError(null)
    try {
      const body = {
        dataset: buildDataset(parsed, settings, jcUnit, xiUnit),
        settings,
      }
      setResult(await api.analyze(body))
    } catch (e) {
      setResult(null)
      setAnalysisError(e instanceof ApiError ? errorMessage(e.code, e.params) : String(e))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page">
      <header className="page-header">
        <h1>Nodeless 초전도체 갭 추출</h1>
        <p className="muted">
          수송 측정으로 얻은 self-field 임계전류밀도 Jc(T)와 상부임계자기장 Hc2로부터
          침투깊이 λ(T)와 초전도 갭 Δ(0)를 구합니다.
        </p>
      </header>

      <DataInput
        text={text}
        onTextChange={setText}
        onExampleChosen={onExampleChosen}
        disabled={busy}
      />

      {parseError && <p className="message error">{parseError}</p>}

      {parsed && (
        <ColumnPreview parsed={parsed} coherenceSource={settings.coherence_source} />
      )}

      <SettingsPanel
        settings={settings}
        jcUnit={jcUnit}
        xiUnit={xiUnit}
        onSettingsChange={setSettings}
        onJcUnitChange={setJcUnit}
        onXiUnitChange={setXiUnit}
        disabled={busy}
      />

      <div className="actions">
        <button type="button" disabled={!ready || busy} onClick={() => void runAnalysis()}>
          {busy ? '계산 중…' : '분석 실행'}
        </button>
        {result && (
          <button
            type="button"
            className="secondary"
            onClick={() => void api.downloadCsv(result)}
          >
            결과 CSV 내려받기
          </button>
        )}
        {!ready && (parsed || stale) && (
          <span className="muted small">
            {stale
              ? '데이터를 읽는 중…'
              : settings.coherence_source === 'FIXED_KAPPA' && !settings.kappa_fixed
                ? 'κ 값을 입력해 주세요.'
                : `열이 ${columnsNeeded}개 필요합니다.`}
          </span>
        )}
      </div>

      {analysisError && <p className="message error">{analysisError}</p>}

      {result && (
        <>
          <FitSummary result={result} />
          <Assumptions result={result} />
          <LambdaTable table={result.lambda_table} />
        </>
      )}

      <footer className="page-footer muted small">
        Talantsev &amp; Tallon, <em>Nature Communications</em> <b>6</b>, 7820 (2015),
        식 (4)에 기반합니다.
      </footer>
    </div>
  )
}

/**
 * Assumptions and warnings, always shown alongside the numbers.
 *
 * Constitution VI: a result derived under an assumption that could invalidate
 * it must carry that assumption. The list is never empty -- the self-field
 * requirement is unconditional.
 */
function Assumptions({ result }: { result: AnalyzeResponse }) {
  const warnings = result.diagnostics.warnings
  if (warnings.length === 0) return null

  const order = { ERROR: 0, WARNING: 1, INFO: 2 } as const
  const sorted = [...warnings].sort((a, b) => order[a.severity] - order[b.severity])

  return (
    <section className="card">
      <h2>가정과 주의사항</h2>
      <ul className="warnings">
        {sorted.map((w, i) => (
          <li key={`${w.code}-${i}`} className={`severity-${w.severity}`}>
            <span className="tag">{LABELS.severity[w.severity]}</span>
            <span className="text">{warningMessage(w)}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}
