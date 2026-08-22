/**
 * Everything the user chooses, in one place.
 *
 * Nothing is assumed silently (FR-004): units are always explicit, and the
 * fields that only matter for one coherence-length method appear only when that
 * method is selected, so the form never asks for a number it will not use.
 */
import type { JcUnit, Settings, XiUnit } from '../api/client'
import { LABELS } from '../errorMessages'

interface Props {
  settings: Settings
  jcUnit: JcUnit
  xiUnit: XiUnit
  onSettingsChange: (settings: Settings) => void
  onJcUnitChange: (unit: JcUnit) => void
  onXiUnitChange: (unit: XiUnit) => void
  disabled?: boolean
}

export function SettingsPanel({
  settings, jcUnit, xiUnit,
  onSettingsChange, onJcUnitChange, onXiUnitChange, disabled,
}: Props) {
  const set = (patch: Partial<Settings>) => onSettingsChange({ ...settings, ...patch })

  return (
    <section className="card">
      <h2>3. 분석 설정</h2>

      <div className="fields">
        <label className="field">
          <span className="label">Jc 단위</span>
          <select
            value={jcUnit}
            disabled={disabled}
            onChange={(e) => onJcUnitChange(e.target.value as JcUnit)}
          >
            <option value="A_PER_CM2">A/cm²</option>
            <option value="A_PER_M2">A/m²</option>
          </select>
          <span className="hint">
            자릿수를 확인하세요. 단위를 틀리면 침투깊이가 21.5배 어긋납니다.
          </span>
        </label>

        <label className="field">
          <span className="label">코히런스 길이 ξ 결정 방식</span>
          <select
            value={settings.coherence_source}
            disabled={disabled}
            onChange={(e) =>
              set({ coherence_source: e.target.value as Settings['coherence_source'] })
            }
          >
            {(['FROM_HC2', 'EXPLICIT_XI', 'FIXED_KAPPA'] as const).map((v) => (
              <option key={v} value={v}>{LABELS.coherenceSource[v]}</option>
            ))}
          </select>
          <span className="hint">
            {settings.coherence_source === 'FROM_HC2' &&
              'ξ = √(Φ₀ / 2πBc2). 세 번째 열에 Hc2[T] 값이 필요합니다.'}
            {settings.coherence_source === 'EXPLICIT_XI' &&
              '다른 방법으로 이미 구한 ξ를 세 번째 열에 넣습니다.'}
            {settings.coherence_source === 'FIXED_KAPPA' &&
              'κ를 모든 온도에서 같다고 두면 식이 명시형이 되어 ξ(T)가 결과로 나옵니다.'}
          </span>
        </label>

        {settings.coherence_source === 'EXPLICIT_XI' && (
          <label className="field">
            <span className="label">ξ 단위</span>
            <select
              value={xiUnit}
              disabled={disabled}
              onChange={(e) => onXiUnitChange(e.target.value as XiUnit)}
            >
              <option value="NM">nm</option>
              <option value="UM">µm</option>
              <option value="M">m</option>
            </select>
          </label>
        )}

        {settings.coherence_source === 'FIXED_KAPPA' && (
          <label className="field">
            <span className="label">κ = λ/ξ</span>
            <input
              type="number"
              step="any"
              min="0.61"
              value={settings.kappa_fixed ?? ''}
              disabled={disabled}
              onChange={(e) =>
                set({ kappa_fixed: e.target.value === '' ? null : Number(e.target.value) })
              }
            />
            <span className="hint">
              strong type-II 물질은 보통 수십 이상입니다. 5보다 작으면 사용한 Hc1 근사의
              정확도가 떨어진다는 경고가 붙습니다.
            </span>
          </label>
        )}

        <label className="field">
          <span className="label">갭 모델</span>
          <select
            value={settings.gap_model ?? 'CLEAN'}
            disabled={disabled}
            onChange={(e) => set({ gap_model: e.target.value as Settings['gap_model'] })}
          >
            {(['CLEAN', 'DIRTY'] as const).map((v) => (
              <option key={v} value={v}>{LABELS.gapModel[v]}</option>
            ))}
          </select>
          <span className="hint">
            어느 쪽이든 두 모델 모두 피팅해 비교 결과를 함께 보여줍니다.
          </span>
        </label>

        <label className="field">
          <span className="label">추출 경로</span>
          <select
            value={settings.fit_route ?? 'TWO_STEP'}
            disabled={disabled}
            onChange={(e) => set({ fit_route: e.target.value as Settings['fit_route'] })}
          >
            {(['TWO_STEP', 'DIRECT'] as const).map((v) => (
              <option key={v} value={v}>{LABELS.fitRoute[v]}</option>
            ))}
          </select>
          <span className="hint">
            {settings.fit_route === 'DIRECT'
              ? '중간 단계 오차가 쌓이지 않고, 해가 없어 실패하는 일도 없습니다.'
              : 'λ(T)를 먼저 뽑으므로 온도별 값을 직접 볼 수 있습니다.'}
          </span>
        </label>

        <label className="field">
          <span className="label">Tc 고정 [K]</span>
          <input
            type="number"
            step="any"
            placeholder="비워두면 피팅으로 결정"
            value={settings.tc_fixed_K ?? ''}
            disabled={disabled}
            onChange={(e) =>
              set({ tc_fixed_K: e.target.value === '' ? null : Number(e.target.value) })
            }
          />
          <span className="hint">
            따로 측정한 Tc가 있으면 넣으세요. 자유 파라미터가 하나 줄어듭니다.
          </span>
        </label>

        <label className="field">
          <span className="label">시료 두께 [nm]</span>
          <input
            type="number"
            step="any"
            placeholder="선택 사항"
            value={settings.film_thickness_nm ?? ''}
            disabled={disabled}
            onChange={(e) =>
              set({ film_thickness_nm: e.target.value === '' ? null : Number(e.target.value) })
            }
          />
          <span className="hint">
            계산에는 쓰이지 않고, 박막 가정이 깨졌는지 확인하는 데만 사용합니다.
          </span>
        </label>
      </div>
    </section>
  )
}
