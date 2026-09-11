/**
 * Getting the measurement data into the page.
 *
 * Two ways in, a file on disk or the clipboard (FR-001). There was a third --
 * two generated datasets a first-time user could press -- and FR-028 was
 * withdrawn: a manufactured dataset shipped beside a measurement tool reads as
 * a claim about real samples. What replaces it is the placeholder below, which
 * shows the layout rather than supplying data (FR-029a).
 */
import { useRef, useState } from 'react'
import { errorMessage } from '../errorMessages'
import { ApiError } from '../api/client'

interface Props {
  text: string
  onTextChange: (text: string) => void
  disabled?: boolean
}

export function DataInput({ text, onTextChange, disabled }: Props) {
  const [problem, setProblem] = useState<string | null>(null)
  const fileInput = useRef<HTMLInputElement>(null)

  async function readFile(file: File) {
    setProblem(null)
    try {
      onTextChange(await file.text())
    } catch (e) {
      setProblem(e instanceof ApiError ? errorMessage(e.code, e.params) : String(e))
    }
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
      </div>

      <textarea
        className="data-input"
        spellCheck={false}
        disabled={disabled}
        value={text}
        onChange={(e) => onTextChange(e.target.value)}
        // FR-029a. This is the whole of the first-run experience now that no
        // dataset is shipped, so it has to carry the layout. The two rows are
        // an illustration of the format and deliberately fewer than the four
        // points the analysis needs, so that nothing here can be run as data
        // or mistaken for a measurement of anything.
        placeholder={
          '측정 데이터를 붙여넣거나 파일을 여세요.\n\n' +
          '열 순서:  온도[K]   Jc   그리고 Hc2[T] 또는 ξ  (선택한 방식에 따라)\n' +
          '구분자는 공백, 탭, 쉼표, 세미콜론 모두 됩니다.\n' +
          '# 로 시작하는 줄과 빈 줄은 무시하며, 첫 줄이 이름이면 머리글로 인식합니다.\n' +
          '최소 4점이 필요합니다.\n\n' +
          '형식 예시 (데이터가 아니라 줄 모양입니다)\n' +
          '#  T_K      Jc_A_per_cm2   Hc2_T\n' +
          '   2.0      6.50e6         13.0\n' +
          '   4.0      5.20e6         11.5'
        }
      />

      {problem && <p className="message error">{problem}</p>}
    </section>
  )
}
