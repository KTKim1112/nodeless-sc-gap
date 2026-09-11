/**
 * Error and warning codes to Korean sentences.
 *
 * The backend never sends display prose (constitution IV), so this is where
 * every sentence the user reads about a failure or an assumption lives. Keeping
 * them together also means they can be reviewed as a set, which matters: a
 * warning nobody understands is a warning the user learns to ignore.
 *
 * Codes come from specs/001-jc-to-gap/data-model.md. An unknown code renders
 * visibly rather than silently, so a missing translation is obvious.
 */
import type { WarningOut } from './api/client'

type Params = Record<string, unknown>

function num(value: unknown, digits = 4): string {
  const n = Number(value)
  if (!Number.isFinite(n)) return String(value)
  if (n !== 0 && (Math.abs(n) < 1e-3 || Math.abs(n) >= 1e5)) return n.toExponential(3)
  return n.toLocaleString('ko-KR', { maximumFractionDigits: digits })
}

const MESSAGES: Record<string, (p: Params) => string> = {
  // --- 입력 ---
  EMPTY_INPUT: () =>
    '데이터가 비어 있습니다. 숫자가 들어 있는 파일을 올리거나 표를 붙여넣어 주세요.',
  COLUMN_COUNT_MISMATCH: (p) =>
    `${p.line}번째 줄의 열 개수가 다릅니다. ${p.expected}개여야 하는데 ${p.found}개입니다. ` +
    '구분자가 섞여 있거나 값이 빠지지 않았는지 확인해 주세요.',
  NOT_A_NUMBER: (p) =>
    `${p.line}번째 줄, ${p.column}번째 열의 "${p.value}"를 숫자로 읽을 수 없습니다. ` +
    '측정 장비가 남긴 표시(OL, ---, NaN 등)가 아닌지 확인해 주세요.',
  NON_POSITIVE_VALUE: (p) =>
    `${p.row}번째 데이터의 ${p.column} 값이 ${num(p.value)}입니다. ` +
    '온도, 임계전류밀도, 상부임계자기장, 코히런스 길이는 모두 0보다 커야 합니다.',
  TOO_FEW_POINTS: (p) =>
    `데이터가 ${p.found}개뿐입니다. 최소 ${p.required}개가 필요합니다. ` +
    '자유 파라미터가 3개이므로 그보다 적으면 피팅에 의미가 없습니다.',
  UNKNOWN_UNIT: (p) => `알 수 없는 단위입니다: ${p.unit}`,
  LENGTH_MISMATCH: (p) =>
    `${p.name} 열의 길이가 온도 열과 다릅니다. ${p.expected}개여야 하는데 ${p.found}개입니다.`,
  MISSING_COLUMN: (p) =>
    `선택하신 방식(${p.coherence_source})에는 ${p.missing} 값이 필요한데 없습니다.`,

  // --- 침투깊이 추출 ---
  KAPPA_TOO_SMALL: (p) =>
    `kappa = ${num(p.kappa)}는 너무 작습니다. ln(kappa) + 0.5가 양수여야 하므로 ` +
    `${num(p.floor)}보다 커야 합니다. 이보다 작으면 식이 음수 Jc를 내놓아 의미가 없습니다.`,
  NOT_TYPE_II: (p) =>
    `kappa = ${num(p.kappa)}는 제2종 초전도체의 경계값 ${num(p.boundary)} 이하입니다. ` +
    '이 분석은 제2종 초전도체를 전제로 합니다.',
  NO_ROOT_TYPE_II: (p) =>
    `${num(p.temperature_K)} K에서 물리적으로 가능한 침투깊이가 없습니다. ` +
    `이 코히런스 길이에서 식이 낼 수 있는 최대 Jc는 ${num(p.jc_max)} A/m²인데 ` +
    `입력값은 ${num(p.jc)} A/m²입니다. 데이터가 kappa ≤ 1을 의미하므로 ` +
    'strong type-II 취급이 적용되지 않습니다. Jc 단위와 Hc2 값을 확인해 주세요.',
  ROOT_BRACKETING_FAILED: (p) =>
    `${num(p.temperature_K)} K에서 해를 찾지 못했습니다. 입력값의 자릿수를 확인해 주세요.`,

  // --- 피팅 ---
  TC_FIXED_BELOW_DATA: (p) =>
    `고정하신 Tc = ${num(p.tc_fixed_K)} K가 측정 최고온도 ${num(p.t_max_K)} K보다 낮습니다. ` +
    'Tc는 모든 측정 온도보다 높아야 합니다.',
  FIT_DID_NOT_CONVERGE: (p) =>
    `피팅이 수렴하지 않았습니다 (경로 ${p.route}, 모델 ${p.model}). ` +
    '온도 범위가 너무 좁거나 데이터 산포가 큰 경우입니다. 결과를 표시하지 않습니다.',

  // --- 불확도 ---
  MC_TOO_MANY_FAILURES: (p) =>
    `Monte Carlo 표본 ${p.n_requested}개 중 ${p.n_valid}개만 유효해 ` +
    `기준치 ${p.n_required}개에 못 미칩니다. 실패한 표본은 극단값 쪽에 몰리므로 ` +
    '남은 것만으로 계산하면 오차가 실제보다 좁게 나옵니다. 입력 오차를 줄여 다시 시도해 주세요.',

  // --- 기타 ---
  JOB_NOT_FOUND: () => '해당 계산 작업을 찾을 수 없습니다. 서버가 재시작되었을 수 있습니다.',
  NETWORK_UNREACHABLE: () =>
    '서버에 연결할 수 없습니다. 백엔드가 실행 중인지 확인해 주세요.',
  REQUEST_REJECTED: (p) =>
    `요청 형식이 서버가 기대하는 것과 다릅니다. (${p.detail ?? ''})`,
  INTERNAL: (p) => `서버 내부 오류입니다. (${p.detail ?? ''})`,
}

const WARNINGS: Record<string, (p: Params) => string> = {
  SELF_FIELD_TRANSPORT_REQUIRED: () =>
    '이 분석은 self-field 조건에서 transport 방식으로 측정한 Jc를 전제로 합니다. ' +
    '자화 측정에서 유도한 Jc, 외부 자기장이 걸린 상태의 Jc, weak link가 있는 시료의 Jc에는 ' +
    '적용되지 않습니다. weak link나 균열로 Jc가 낮아졌다면 추출된 침투깊이가 실제보다 크게 나옵니다.',
  ISOTROPIC_GL_ASSUMED: () =>
    'Hc2에서 코히런스 길이를 구할 때 등방 Ginzburg-Landau 관계를 사용했습니다. ' +
    '비등방 초전도체라면 여기서 나온 값은 측정 자기장 방향에 대응하는 유효 코히런스 길이입니다. ' +
    'Pauli limiting, 다중밴드 효과, 넓은 저항 전이가 Hc2에 영향을 준 경우에도 마찬가지입니다.',
  CROSS_QUANTITY_CORRELATION_IGNORED: (p) =>
    `입력 오차의 상관 방식은 ${p.correlation_mode}로 계산했습니다. ` +
    '한 물리량 안의 상관은 이 설정으로 다루지만, Jc와 Hc2처럼 서로 다른 물리량 사이의 상관은 ' +
    '고려하지 않습니다. 온도 보정처럼 공통 원인이 있다면 실제 오차와 다를 수 있습니다.',
  KAPPA_NEAR_TYPE_I_BOUNDARY: (p) =>
    `kappa의 최솟값이 ${num(p.kappa_min, 2)}로 ${num(p.threshold ?? 5, 0)}보다 작습니다` +
    (p.temperature_K ? ` (${num(p.temperature_K, 2)} K).` : '.') +
    ' 사용한 식은 kappa가 충분히 클 때의 Hc1 근사에 기대고 있어, 이 영역에서는 정확도가 떨어집니다.',
  LOW_T_COVERAGE_WEAK: (p) =>
    `가장 낮은 측정 온도가 Tc의 ${num(p.t_min_over_tc, 2)}배입니다. ` +
    '갭은 저온의 지수적 거동에서 결정되므로, 이 범위에서는 Δ(0)의 신뢰도가 다소 낮습니다.',
  LOW_T_COVERAGE_INSUFFICIENT: (p) =>
    `가장 낮은 측정 온도가 Tc의 ${num(p.t_min_over_tc, 2)}배입니다. ` +
    'Δ(0)는 사실상 외삽값이며 측정으로 뒷받침되지 않습니다. 저온 데이터를 추가하시길 권합니다.',
  THIN_FILM_ASSUMPTION_STRAINED: (p) =>
    `입력하신 두께 ${num(Number(p.thickness_m) * 1e9, 1)} nm가 ` +
    `침투깊이의 2배(${num(Number(p.limit_m) * 1e9, 1)} nm)를 넘습니다. ` +
    '사용한 관계식은 두께가 침투깊이에 비해 크지 않은 박막을 대상으로 유도된 것입니다.',
  MODELS_INDISTINGUISHABLE: (p) =>
    `clean과 dirty 모델의 적합도가 비슷해 어느 쪽인지 판정할 수 없습니다 ` +
    `(ΔAIC = ${num(p.delta_aic, 1)}, 판정 기준 ${num(p.threshold, 0)}). ` +
    '두 모델이 주는 Δ(0)는 약 20% 차이가 나므로, 어느 쪽을 골랐는지 함께 밝히셔야 합니다. ' +
    '구분하려면 Jc의 산포가 0.5% 이하여야 합니다.',
  STDERR_UNAVAILABLE: (p) =>
    `${p.parameter}의 표준오차를 계산할 수 없었습니다. ` +
    '파라미터끼리 거의 완전히 상관되어 있다는 뜻이며, 보통 데이터가 부족한 경우입니다.',
  MC_SAMPLES_DISCARDED: (p) =>
    `Monte Carlo 표본 ${p.n_requested}개 중 ${p.n_valid}개만 유효했습니다. ` +
    '버려진 표본은 극단값 쪽에 몰려 있으므로 오차가 실제보다 약간 좁을 수 있습니다.',
}

function render(table: Record<string, (p: Params) => string>,
                code: string, params: Params): string {
  const fn = table[code]
  if (!fn) return `[${code}] ${JSON.stringify(params)}`
  try {
    return fn(params)
  } catch {
    return `[${code}] ${JSON.stringify(params)}`
  }
}

export function errorMessage(code: string, params: Params = {}): string {
  return render(MESSAGES, code, params)
}

export function warningMessage(warning: WarningOut): string {
  return render(WARNINGS, warning.code, (warning.params ?? {}) as Params)
}

/** Short labels for the enumerations, used on buttons and in tables. */
export const LABELS = {
  coherenceSource: {
    FROM_HC2: 'Hc2에서 계산',
    EXPLICIT_XI: 'ξ 직접 입력',
    FIXED_KAPPA: 'κ 고정',
  },
  gapModel: { CLEAN: 'clean limit', DIRTY: 'dirty limit' },
  fitRoute: { TWO_STEP: '2단계 (λ(T) → 피팅)', DIRECT: '직접 (T–Jc 전역 피팅)' },
  correlationMode: {
    SYSTEMATIC: '계통 오차 (모든 온도에 동일)',
    INDEPENDENT: '산포 (온도마다 독립)',
  },
  couplingRegime: {
    BELOW_BCS: 'BCS 약결합보다 작음',
    WEAK_COUPLING_BCS: 'BCS 약결합',
    MODERATELY_STRONG: '중간 강결합',
    STRONG_COUPLING: '강결합',
  },
  severity: { INFO: '참고', WARNING: '주의', ERROR: '오류' },
} as const
