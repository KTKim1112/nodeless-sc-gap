/**
 * Show how the file was read, before anything is computed with it (FR-003).
 *
 * A misread column is the cheapest error to make and one of the most expensive
 * to notice later: it does not crash, it produces a plausible gap. So the user
 * is shown which column the program thinks is which, and told plainly when the
 * count does not match what the chosen method needs.
 */
import type { CoherenceSource, ParseResponse } from '../api/client'

interface Props {
  parsed: ParseResponse
  coherenceSource: CoherenceSource
}

const THIRD_COLUMN: Record<CoherenceSource, string | null> = {
  FROM_HC2: 'Hc2',
  EXPLICIT_XI: 'ξ',
  FIXED_KAPPA: null,
}

export function ColumnPreview({ parsed, coherenceSource }: Props) {
  const third = THIRD_COLUMN[coherenceSource]
  const expected = third === null ? 2 : 3
  const roles = third === null ? ['온도 T', 'Jc'] : ['온도 T', 'Jc', third]
  const enough = parsed.n_columns >= expected

  return (
    <section className="card">
      <h2>2. 읽은 결과 확인</h2>

      <p className="muted small">
        {parsed.n_rows}개 데이터, {parsed.n_columns}개 열
        {parsed.header_detected ? ' · 첫 줄을 머리글로 인식' : ' · 머리글 없음'}
      </p>

      {!enough && (
        <p className="message error">
          선택하신 방식에는 열이 {expected}개 필요한데 {parsed.n_columns}개만 있습니다.
          {third !== null && ` 세 번째 열에 ${third} 값이 있어야 합니다.`}
          {third === null && ' κ 고정 방식에서는 온도와 Jc 두 열만 사용합니다.'}
        </p>
      )}

      <div className="table-scroll">
        <table className="preview">
          <thead>
            <tr>
              <th className="index" />
              {Array.from({ length: parsed.n_columns }, (_, i) => (
                <th key={i} className={i < expected ? 'used' : 'unused'}>
                  <span className="role">{roles[i] ?? '사용 안 함'}</span>
                  <span className="source">
                    {parsed.header_detected ? parsed.column_names[i] : `${i + 1}번째 열`}
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {parsed.preview.map((row, r) => (
              <tr key={r}>
                <td className="index">{r + 1}</td>
                {row.map((value, c) => (
                  <td key={c} className={c < expected ? 'used' : 'unused'}>
                    {value}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {parsed.n_rows > parsed.preview.length && (
        <p className="muted small">
          … 아래로 {parsed.n_rows - parsed.preview.length}개 더 있습니다.
        </p>
      )}

      <p className="muted small">
        열의 역할은 순서로 정해집니다. 위 표시가 실제 데이터와 다르면 파일의 열 순서를
        바꾸거나, 아래에서 다른 방식을 선택하세요.
      </p>
    </section>
  )
}
