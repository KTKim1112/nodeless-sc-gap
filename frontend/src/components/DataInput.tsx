/**
 * Getting the measurement data into the page.
 *
 * Three ways in, because a researcher's data can be in any of three places:
 * a file on disk, the clipboard, or nowhere yet (FR-001, FR-028).
 */
import { useEffect, useRef, useState } from 'react'
import { api, ApiError, type Example, type ExampleSummary } from '../api/client'
import { errorMessage } from '../errorMessages'

interface Props {
  text: string
  onTextChange: (text: string) => void
  onExampleChosen: (example: Example) => void
  disabled?: boolean
}

export function DataInput({ text, onTextChange, onExampleChosen, disabled }: Props) {
  const [examples, setExamples] = useState<ExampleSummary[]>([])
  const [loading, setLoading] = useState<string | null>(null)
  const [problem, setProblem] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  useEffect(() => {
    api.examples().then(setExamples).catch(() => setExamples([]))
  }, [])

  async function chooseExample(name: string) {
    setLoading(name)
    setProblem(null)
    try {
      onExampleChosen(await api.example(name))
    } catch (e) {
      setProblem(e instanceof ApiError ? errorMessage(e.code, e.params) : String(e))
    } finally {
      setLoading(null)
    }
  }

  async function readFile(file: File) {
    setProblem(null)
    onTextChange(await file.text())
  }

  return (
    <section className="card">
      <h2>1. 데이터 입력</h2>

      <div className="row wrap gap">
        <button
          type="button"
          className="secondary"
          disabled={disabled}
          onClick={() => fileInput.current?.click()}
        >
          파일 열기
        </button>
        <input
          ref={fileInput}
          type="file"
          accept=".txt,.csv,.dat,.tsv,text/*"
          hidden
          onChange={(e) => {
            const file = e.target.files?.[0]
            if (file) void readFile(file)
            e.target.value = ''
          }}
        />
        <button
          type="button"
          className="secondary"
          disabled={disabled || !text}
          onClick={() => onTextChange('')}
        >
          지우기
        </button>

        {examples.length > 0 && (
          <>
            <span className="divider" aria-hidden />
            <span className="muted small">예제로 시작:</span>
            {examples.map((e) => (
              <button
                key={e.name}
                type="button"
                className="secondary"
                disabled={disabled || loading !== null}
                title={e.title}
                onClick={() => void chooseExample(e.name)}
              >
                {loading === e.name ? '불러오는 중…' : e.name}
              </button>
            ))}
          </>
        )}
      </div>

      <textarea
        className="data-input"
        spellCheck={false}
        disabled={disabled}
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        placeholder={
          '측정 데이터를 붙여넣거나 파일을 여세요.\n\n' +
          '열 순서:  온도[K]   Jc   그리고 Hc2[T] 또는 ξ  (선택한 방식에 따라)\n' +
          '구분자는 공백, 탭, 쉼표, 세미콜론 모두 됩니다.\n' +
          '# 로 시작하는 줄과 빈 줄은 무시하며, 첫 줄이 이름이면 머리글로 인식합니다.\n\n' +
          '예)\n' +
          '#  T_K      Jc_A_per_cm2   Hc2_T\n' +
          '   2.0      6.50e6         13.0\n' +
          '   4.0      5.20e6         11.5'
        }
      />

      {problem && <p className="message error">{problem}</p>}
    </section>
  )
}
