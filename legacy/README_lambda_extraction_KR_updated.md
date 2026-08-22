# Self-field 임계전류밀도로부터 penetration depth 추출

## 1. 목적

이 패키지는 type-II 초전도 thin film의 self-field transport 임계전류밀도 데이터로부터
London penetration depth, lambda(T)를 추출하기 위한 세 개의 Python 프로그램으로 구성되어 있습니다.

세 프로그램은 다음과 같습니다.

1. `lambda_from_T_Jc_Hc2.py`
   - 입력: T, Jc, Hc2
   - Hc2(T)로부터 xi(T)를 계산
   - 온도에 따라 변하는
     kappa(T) = lambda(T)/xi(T)
     를 고려하여 lambda(T)를 계산

2. `lambda_from_T_Jc_xi.py`
   - 입력: T, Jc, xi
   - 사용자가 제공한 xi(T)를 사용
   - 온도에 따라 변하는
     kappa(T) = lambda(T)/xi(T)
     를 고려하여 lambda(T)를 계산

3. `lambda_from_T_Jc_constant_kappa.py`
   - 입력: T, Jc
   - 사용자가 하나의 고정된 kappa = lambda/xi 값을 입력
   - lambda(T)를 명시적으로 계산하고, 동시에 추정된 xi(T)도 출력

세 프로그램 모두 사용자가 지정한 상대적인 실험 오차를 Monte Carlo 방식으로
lambda의 오차에 전파할 수 있습니다.

---


## 2. 기호, 변수 및 물리량 설명

이 절에서는 프로그램과 README 전체에서 사용되는 주요 변수와 물리량을 정의합니다.
별도의 언급이 없는 한, 프로그램 내부 계산은 SI 단위계로 수행됩니다.

### T — 온도

`T`는 시료의 온도입니다.

    기호: T
    일반적인 입력 단위: K
    프로그램 내부 단위: K

입력 파일의 각 행은 하나의 온도점을 의미합니다. 프로그램은 입력 데이터의
온도 의존성을 특정 함수 형태로 가정하지 않으며, 각 온도에서 xi(T), lambda(T),
kappa(T)를 서로 독립적으로 계산합니다.

### Jc — 임계전류밀도

`Jc`는 초전도체의 임계전류밀도(critical current density)입니다. 본 방법에서
사용하는 Jc는 Talantsev-Tallon thin-film 분석의 가정에 맞는
**self-field transport critical current density**여야 합니다. 즉, 의도적으로
외부 자기장을 인가하지 않은 상태에서 transport 측정으로 얻은 임계전류밀도를
의미합니다.

    기호: Jc
    허용 입력 단위: A/cm^2 또는 A/m^2
    프로그램 내부 SI 단위: A/m^2

측정한 임계전류 Ic로부터 Jc를 계산하는 경우,

    Jc = Ic / A

이며, 여기서 `A`는 bridge 또는 film에서 실제 전류가 흐르는 단면적입니다.
따라서 bridge width와 film thickness의 불확도는 Jc의 오차에 직접 포함될 수 있습니다.

식 (4)에서는 로그 보정을 제외하면 대략

    Jc proportional to lambda^(-3)

이므로, 일반적으로 Jc가 클수록 추출되는 lambda는 작아지는 경향이 있습니다.

### Hc2 / Bc2 — 상부 임계자기장

`Hc2`는 type-II 초전도체의 upper critical field, 즉 상부 임계자기장입니다.
이 자기장에 도달하면 초전도 상태가 사라지고 정상상태로 전이합니다.

    실험에서 흔히 사용하는 기호: Hc2
    Program 1의 입력 단위: T

엄밀하게는 자기장 세기 `H`의 SI 단위는 A/m이고, magnetic induction `B`의
단위는 tesla입니다. 그러나 초전도 실험 문헌에서는 일반적으로 "Hc2"라고
표기하면서 그 값을 tesla 단위로 직접 제시합니다. 따라서 Program 1에서는
tesla 단위로 입력된 Hc2 값을 수치적으로

    Bc2 = mu0 Hc2

의 tesla 값으로 취급합니다.

Program 1에서 사용하는 표준 isotropic/effective Ginzburg-Landau 관계는

    Bc2(T) = PHI0 / [2*pi*xi(T)^2]

입니다.

따라서 Hc2가 커질수록 계산되는 GL coherence length xi는 작아집니다.

### xi — 초전도 coherence length

`xi`(그리스 문자 ξ)는 superconducting coherence length입니다.
Ginzburg-Landau 이론에서는 초전도 order parameter가 공간적으로 변하는
특성 길이척도를 나타냅니다.

    기호: xi = ξ
    Program 2에서 허용되는 입력 단위: m, nm, um
    프로그램 내부 SI 단위: m

Program 1에서는 Hc2로부터

    xi(T) = sqrt[PHI0 / (2*pi*Bc2(T))]

를 이용해 xi를 계산합니다.

이렇게 얻은 xi는 입력한 Hc2 데이터에 대응하는 Ginzburg-Landau 또는
effective coherence length로 해석하는 것이 적절합니다. 특히 Pauli limiting,
multiband superconductivity, 강한 비등방성, vortex dynamics, 넓은 resistive
transition 등이 실험적으로 정의한 Hc2에 영향을 주는 경우에는 이 xi가
microscopic Cooper-pair size와 반드시 동일하다고 볼 수 없습니다.

### lambda — London penetration depth

`lambda`(그리스 문자 λ)는 London magnetic penetration depth입니다.
초전도체 내부로 자기장이 침투하여 감쇠하는 특성 길이를 나타냅니다.

    기호: lambda = λ
    프로그램 내부 SI 단위: m
    프로그램 출력 단위: m 및 nm

London electrodynamics에서는

    lambda^(-2) proportional to ns / m*

관계가 성립하며, 여기서 `ns`는 superconducting superfluid density,
`m*`는 effective carrier mass입니다. 따라서 일반적으로 lambda가 클수록
superfluid stiffness가 작다는 의미를 가집니다.

본 프로그램의 핵심 목적은 Talantsev-Tallon의 type-II thin-film 식을 사용하여
self-field Jc로부터 lambda(T)를 추출하는 것입니다.

### kappa — Ginzburg-Landau parameter

`kappa`(κ)는 Ginzburg-Landau parameter이며,

    kappa(T) = lambda(T) / xi(T)

로 정의됩니다.

즉 magnetic penetration length와 coherence length의 비입니다.

    기호: kappa = κ
    단위: 무차원

전통적인 type-I/type-II 경계는

    kappa = 1/sqrt(2)

입니다.

명확한 type-II 초전도체에서는 kappa가 이 값보다 크며, 여기에서 주로 다루는
strong type-II 물질의 경우 kappa가 1보다 훨씬 클 수 있습니다.

Program 1과 Program 2에서는 lambda를 계산한 뒤 각 온도마다 kappa를 다시
계산합니다. Program 3에서는 사용자가 지정한 하나의 kappa 값을 모든 온도에서
고정한다고 가정합니다.

### Hc1 — 하부 임계자기장

`Hc1`은 type-II 초전도체의 lower critical field, 즉 하부 임계자기장입니다.
Hc1보다 낮은 영역에서는 bulk가 Meissner state를 유지하고, Hc1을 넘으면
vortex 형태로 magnetic flux가 침투하기 시작합니다.

본 프로그램에서 사용하는 Talantsev-Tallon thin-film self-field 관계는

    Jc^II(sf) = Hc1 / lambda

로 쓸 수 있습니다.

그리고 large-kappa 근사에서 Hc1의 표준 표현을 사용하면 논문의 식 (4),

    Jc^II(sf)
      = PHI0 / (4*pi*MU0*lambda^3) * [ln(kappa) + 0.5]

형태를 얻습니다.

세 프로그램 모두 Hc1을 직접 입력값으로 사용하지는 않습니다.

### PHI0 — 자기선속 양자

`PHI0`는 superconducting magnetic flux quantum, 즉 자기선속 양자입니다.

    PHI0 = h / (2e)
         = 2.067833848e-15 Wb

    기호: Phi0 = Φ0
    SI 단위: weber (Wb)

이는 기본 물리상수이며 세 프로그램 내부에서 고정값으로 사용됩니다.

### MU0 — 진공 투자율

`MU0`는 vacuum permeability, 즉 진공 투자율입니다.

    MU0 = 4*pi*10^(-7) H/m

    기호: mu0 = μ0
    SI 단위: H/m

이 값 역시 프로그램 내부에서 고정되어 있습니다.

### Ic — 임계전류

`Ic`는 선택한 superconducting-to-resistive transition criterion에 도달할 때의
실험적 transport current입니다.

    기호: Ic
    일반적인 단위: A

세 프로그램은 Ic를 직접 입력받지 않습니다. 실험 결과가 Ic로 주어졌다면,
시료의 전류 운반 단면적으로 나누어 먼저 Jc로 변환해야 합니다.

### Film thickness와 bridge width

Jc가 이미 계산되어 있다면 본 코드는 film thickness나 bridge width를 직접
입력받지 않습니다. 그러나 이 geometry 변수들은 두 가지 점에서 중요합니다.

1. Ic를 Jc로 변환할 때 직접 사용됩니다.
2. Talantsev-Tallon 모델 자체가 thin-film/self-field model이므로, film 두께가
   해당 thin-film 표현이 물리적으로 유효한 범위에 있어야 합니다.

### Self-field

`Self-field`는 transport current 자체가 만들어내는 자기장을 의미합니다.
즉, 의도적으로 외부 자기장을 인가하지 않은 상태입니다.

따라서 Talantsev-Tallon 식 (4)에 입력하는 Jc는 self-field transport Jc여야 합니다.

### Error percentage, sigma, confidence interval

다음과 같은 command-line option

    --jc-error-percent
    --hc2-error-percent
    --xi-error-percent
    --kappa-error-percent

은 모두 상대적인 1-standard-deviation, 즉 1-sigma uncertainty로 해석됩니다.

예를 들어

    --jc-error-percent 5

는

    sigma_Jc / Jc = 0.05

를 의미합니다.

Monte Carlo 과정은 이러한 입력 uncertainty를 비선형 계산 전체에 전파하여
lambda의 분포와 error bar를 계산합니다.

`--confidence 68.27`은 central 68.27% interval을 의미하며,
Gaussian distribution에서는 대략 ±1 sigma에 해당합니다.

### 주요 기호 요약

| 물리량 | 기호 | 의미 | 일반적인/입력 단위 |
| --- | --- | --- | --- |
| 온도 | T | 시료 온도 | K |
| 임계전류밀도 | Jc | Self-field transport critical current density | A/cm^2 또는 A/m^2 |
| 상부 임계자기장 | Hc2 / Bc2 | 초전도 상태가 사라지는 임계 자기장 | T |
| Coherence length | xi (ξ) | GL order parameter의 공간적 특성 길이 | m, nm, um |
| Penetration depth | lambda (λ) | 자기장 침투 특성 길이 | m, nm |
| GL parameter | kappa (κ) | lambda/xi | 무차원 |
| 하부 임계자기장 | Hc1 | vortex penetration이 시작되는 임계 자기장 | A/m 또는 보통 mu0 Hc1을 T로 표기 |
| 자기선속 양자 | PHI0 (Φ0) | h/(2e) | Wb |
| 진공 투자율 | MU0 (μ0) | magnetic constant | H/m |
| 임계전류 | Ic | Jc로 변환하기 전의 transport critical current | A |

---

## 3. 주요 참고문헌과 사용한 식

이 구현은 다음 논문을 기반으로 합니다.

E. F. Talantsev and J. L. Tallon,  
"Universal self-field critical current for thin-film superconductors,"  
Nature Communications 6, 7820 (2015).  
DOI: 10.1038/ncomms8820

self-field 조건의 type-II thin-film 초전도체에 대해, 해당 논문의 식 (4)는

    Jc^II(sf) = Hc1/lambda
              = PHI0 / (4*pi*MU0*lambda^3) * [ln(kappa) + 0.5]

이며,

    kappa = lambda/xi

입니다.

따라서 xi가 독립적으로 알려져 있는 경우,

    Jc = PHI0 / (4*pi*MU0*lambda^3)
         * [ln(lambda/xi) + 0.5]

로 쓸 수 있습니다.

이 논문은 transport 방식으로 측정된 self-field Jc와 thin-film geometry를 강조합니다.
논문의 모델에서는 film의 전체 두께를 2b로 표기하며, relevant thickness scale이
lambda와 같은 차수이거나 그보다 크지 않은 영역을 주된 분석 대상으로 합니다.
또한 Methods에서는 magnetization으로부터 유도된 Jc가 아니라 transport Jc,
self-field 조건, weak-link가 없는 film을 중요하게 다룹니다.

중요한 차이는 다음과 같습니다.

- 원 논문에서는 kappa가 로그 안에만 들어가고, 그 온도 의존성이 결과에 미치는 영향이
  비교적 작기 때문에 kappa를 근사적으로 온도에 무관한 상수로 취급하는 경우가 많습니다.
- Program 1과 Program 2는 의도적으로 constant-kappa 조건을 강제하지 않습니다.
  대신 사용자가 요청한 self-consistent 절차,

      xi(T) -> lambda(T) 계산 -> kappa(T)=lambda(T)/xi(T)

  를 매 온도에서 반복합니다.
- Program 3은 constant-kappa 근사를 직접 구현합니다.

---

## 4. Program 1: T-Jc-Hc2 -> xi(T) -> lambda(T)

### 입력

다음 순서의 세 컬럼을 입력합니다.

    T(K)    Jc    Hc2(T)

입력 파일은 공백, 탭, 쉼표, 세미콜론 중 어떤 방식으로 구분되어 있어도 됩니다.
헤더는 있어도 되고 없어도 됩니다.

기본 Jc 단위:

    A/cm^2

다음과 같이 A/m^2를 사용할 수도 있습니다.

    --jc-unit A/m2

### Step A: Hc2로부터 coherence length 계산

프로그램은 표준적인 Ginzburg-Landau orbital upper-critical-field 관계식

    Bc2(T) = PHI0 / [2*pi*xi(T)^2]

을 사용합니다.

따라서

    xi(T) = sqrt[ PHI0 / (2*pi*Bc2(T)) ]

입니다.

실험 논문이나 데이터 테이블에서 "Hc2"가 tesla 단위로 주어질 경우,
프로그램은 그 수치값을 Bc2 = mu0 Hc2의 tesla 값으로 사용합니다.
이는 critical-field 그래프에서 Hc2를 T 단위로 표시할 때 흔히 사용하는 실험적 관례입니다.

### Step B: lambda에 대한 implicit equation 풀이

xi(T)를 계산한 뒤, 프로그램은 각 온도에서 독립적으로

    Jc(T) = PHI0/(4*pi*MU0*lambda(T)^3)
            * { ln[lambda(T)/xi(T)] + 0.5 }

를 풉니다.

lambda는 lambda^-3 항에도 들어가고 ln(lambda/xi) 내부에도 들어가기 때문에,
xi가 고정되어 있을 때 lambda를 단순한 초등함수 형태의 명시적 식으로 쓸 수 없습니다.
따라서 프로그램은 Brent의 bracketed root solver인
`scipy.optimize.brentq`를 사용합니다.

프로그램은 lambda > xi인 해 branch를 선택합니다.
이는 이 방법을 일반적으로 적용하는 strong type-II 계에 적합한 조건입니다.

### 출력

출력 CSV에는 다음 항목이 포함됩니다.

    T_K
    Jc_input
    Jc_A_per_m2
    Hc2_T
    xi_m
    xi_nm
    lambda_m
    lambda_nm
    kappa_lambda_over_xi

uncertainty propagation을 활성화한 경우에는 추가로 Monte Carlo 평균값,
표준편차, confidence interval, lambda의 상대 오차가 포함됩니다.

### 사용 예

    python lambda_from_T_Jc_Hc2.py sample_Hc2.txt \
        --jc-unit A/cm2 \
        --jc-error-percent 5 \
        --hc2-error-percent 3 \
        --mc-samples 10000 \
        --confidence 68.27 \
        --output result_Hc2.csv

---

## 5. Program 2: T-Jc-xi -> lambda(T)

### 입력

다음 세 컬럼을 입력합니다.

    T(K)    Jc    xi

기본값:

    Jc unit = A/m^2
    xi unit = m

다른 단위도 사용할 수 있습니다.

    --jc-unit A/cm2
    --xi-unit nm
    --xi-unit um

### 계산

각 데이터 행에 대해 프로그램은 직접

    Jc(T) = PHI0/(4*pi*MU0*lambda(T)^3)
            * { ln[lambda(T)/xi(T)] + 0.5 }

를 풉니다.

이 경우에도

    kappa(T) = lambda(T)/xi(T)

는 고정되지 않으며, 각 온도에서 개별적으로 다시 계산됩니다.

### 사용 예

    python lambda_from_T_Jc_xi.py sample_xi.txt \
        --jc-unit A/m2 \
        --xi-unit m \
        --jc-error-percent 5 \
        --xi-error-percent 4 \
        --mc-samples 10000 \
        --output result_xi.csv

---

## 6. Program 3: lambda/xi 비율이 일정한 T-Jc 데이터

kappa = lambda/xi를 모든 온도에서 고정하면 식 (4)는

    Jc(T) = PHI0/(4*pi*MU0*lambda(T)^3)
            * [ln(kappa) + 0.5]

가 됩니다.

이 경우 lambda는 명시적으로

    lambda(T)
      = { PHI0/[4*pi*MU0*Jc(T)]
          * [ln(kappa)+0.5] }^(1/3)

로 쓸 수 있습니다.

따라서 수치적인 root finding이 필요하지 않습니다.

lambda를 계산한 뒤에는

    xi(T) = lambda(T)/kappa

도 함께 출력합니다.

### 필요한 입력

두 컬럼:

    T(K)    Jc

그리고 사용자가 지정하는 하나의 고정된 kappa 값이 필요합니다.
예를 들어

    --kappa 40

과 같이 사용합니다.

### 사용 예

    python lambda_from_T_Jc_constant_kappa.py sample_Jc.txt \
        --jc-unit A/cm2 \
        --kappa 40 \
        --jc-error-percent 5 \
        --kappa-error-percent 3 \
        --mc-samples 10000 \
        --output result_constant_kappa.csv

---

## 7. 실험 오차 / error bar

`--error-percent`로 끝나는 옵션들은 모두 상대적인
1-standard-deviation, 즉 1-sigma uncertainty로 해석됩니다.

예를 들어

    --jc-error-percent 5

는

    sigma_Jc / Jc = 0.05

를 의미합니다.

Program 1에서는

    --jc-error-percent
    --hc2-error-percent

를 사용합니다.

Program 2에서는

    --jc-error-percent
    --xi-error-percent

를 사용합니다.

Program 3에서는

    --jc-error-percent
    --kappa-error-percent

를 사용합니다.

### Monte Carlo 절차

각 온도에서 다음 절차를 수행합니다.

1. uncertainty가 지정된 각 입력값에 대해 양의 random sample을 생성합니다.
2. sampling distribution은 log-normal distribution을 사용하며,
   그 상대 표준편차가 사용자가 입력한 퍼센트와 같도록 parameter를 설정합니다.
3. 필요한 경우 xi를 다시 계산합니다.
4. 모든 random sample에 대해 식 (4)를 다시 풀어 lambda를 계산합니다.
5. 다음 값을 출력합니다.
   - Monte Carlo 평균 lambda
   - 1-sigma 표준편차
   - central confidence interval
   - 퍼센트 단위의 상대 표준편차

Jc, Hc2, xi, kappa는 모두 양수인 물리량이므로 log-normal sampling을 사용합니다.
일반적인 Gaussian sampling은 uncertainty가 충분히 작지 않을 경우 음의 값을 생성할 수 있습니다.

### Confidence interval

기본값:

    --confidence 68.27

이는 Gaussian distribution에서 대략 1-sigma에 해당하는 central interval입니다.

약 95% confidence interval을 원하면

    --confidence 95

를 사용합니다.

### Monte Carlo sample 개수

기본값:

    --mc-samples 5000

최종적인 publication-quality uncertainty를 계산하려는 경우,
특히 uncertainty가 크거나 식의 비선형성이 강한 경우에는
일반적으로 10000-50000 sample이 더 안전합니다.

`--mc-samples`를 증가시키면 계산된 uncertainty 자체가 작아지는 것이 아니라,
Monte Carlo로 추정한 uncertainty의 통계적 안정성이 향상됩니다.

---

## 8. 수치 계산 정확도와 실험 uncertainty의 차이

이 두 개념은 서로 다릅니다.

### 실험 uncertainty

다음 옵션으로 조절합니다.

    --jc-error-percent
    --hc2-error-percent
    --xi-error-percent
    --kappa-error-percent

이 값들이 lambda의 물리적인 error bar를 결정합니다.

### 수치적인 root 계산 정확도

Program 1과 Program 2에서는 추가로

    --root-xtol
    --root-rtol

을 설정할 수 있습니다.

기본값:

    --root-xtol 1e-15  [m]
    --root-rtol 1e-12

이 값들은 Brent root solver의 종료 조건입니다.

실제 초전도 실험 데이터에서는 이 기본값으로 인한 수치적인 root error가
실험 uncertainty에 비해 매우 작습니다.
따라서 일반적으로 numerical tolerance를 불필요하게 더 엄격하게 하기보다는
실제 실험 uncertainty 값을 올바르게 설정하는 것이 더 중요합니다.

Program 3은 명시적인 식을 사용하므로 root solver가 필요하지 않습니다.

---

## 9. 중요한 물리적 가정과 한계

### A. Jc는 self-field transport Jc여야 함

Talantsev-Tallon 분석은 self-field critical current density를 대상으로 합니다.
상당한 외부 자기장이 인가된 상태에서 측정된 Jc를 식 (4)에 자동으로 대입해서는 안 됩니다.

### B. Thin-film regime

이 모델은 transverse thickness scale이 lambda와 비슷하거나 그보다 작은
thin conductor를 대상으로 개발되었습니다.

sample이 lambda보다 상당히 두꺼운 경우, 원 논문에서는 thickness correction과
lambda scaling의 crossover를 논의합니다.

### C. Weak link / sample quality

원 논문의 데이터 선택에서는 weak-link가 없는 film을 중요하게 다룹니다.

crack, weak link, connectivity loss, 불균일한 current path,
또는 intrinsic하지 않은 voltage criterion 때문에 Jc가 감소한 경우,
식 (4)로부터 얻은 apparent lambda가 실제보다 크게 나올 수 있습니다.

### D. Hc2로부터 얻은 xi는 model-dependent coherence length임

Program 1에서는

    xi = sqrt[PHI0/(2*pi*Hc2)]

를 사용합니다.

이는 표준 GL orbital relation입니다.

실험적으로 정의한 Hc2가 Pauli limiting, multiband effect,
넓은 resistive transition, vortex dynamics, dimensional crossover,
또는 임의의 resistive criterion에 강하게 영향을 받는 경우,
계산된 xi는 microscopic pair size라기보다 effective GL coherence length로
해석하는 것이 적절합니다.

### E. type-I/type-II 경계 근처의 kappa

수치 solver는 의도적으로 lambda > xi branch를 사용합니다.
이 프로그램의 주된 적용 대상이 명확한 type-II 물질이기 때문입니다.

계가

    kappa = 1/sqrt(2)

에 가까운 경우에는 simple strong-type-II treatment와
ln(kappa)+0.5를 포함하는 근사적인 Hc1 표현을 더 신중하게 다루어야 합니다.

### F. Constant-kappa 프로그램

Program 3은 kappa를 온도에 무관한 값으로 취급하는 것이 물리적으로 정당하거나,
의도적으로 그렇게 가정하고 싶은 경우에만 적합합니다.

세 프로그램 중 2015년 Talantsev-Tallon 논문에서 사용한 단순화에
가장 가까운 것이 Program 3입니다.

---

### G. 비등방 초전도체와 Hc2의 방향

Program 1은 isotropic/effective GL 표현

    Bc2 = PHI0/(2*pi*xi^2)

을 사용합니다.

비등방 초전도체에서는 Hc2로부터 계산되는 coherence length가
자기장 방향에 따라 달라집니다.

예를 들어 uniaxial GL description에서는

    Bc2^c  = PHI0/(2*pi*xi_ab^2)

인 반면,

    Bc2^ab = PHI0/(2*pi*xi_ab*xi_c)

입니다.

따라서 물질의 비등방성이 강한 경우 Program 1에서 계산되는 xi는
입력된 Hc2 측정 geometry에 대응하는 effective coherence length로 해석해야 합니다.

또는 실험 geometry에 맞는 anisotropic GL relation을 사용하도록
프로그램을 수정해야 합니다.

### H. Correlated uncertainty

내장된 Monte Carlo 계산은 사용자가 입력한 Jc, Hc2/xi, kappa의 uncertainty가
통계적으로 서로 독립이라고 가정합니다.

두 물리량이 동일한 systematic error source를 공유하는 경우,
예를 들어 film thickness calibration, temperature calibration,
또는 공통 fitting procedure에 의해 오차가 생기는 경우에는
uncertainty들이 서로 correlated될 수 있습니다.

이 경우 independent Monte Carlo는 최종 lambda uncertainty를
과대평가하거나 과소평가할 수 있습니다.

correlated error가 알려져 있다면 covariance matrix를 이용한 sampling 방식으로
프로그램을 확장할 수 있습니다.

### I. Jc에서의 geometry uncertainty

Jc를 Ic를 cross-sectional area로 나누어 계산했다면,
film thickness와 bridge width의 uncertainty도 일반적으로 Jc uncertainty에 포함해야 합니다.

Ic, width w, thickness d의 오차가 서로 독립이라고 가정하면,
1차 근사에서

    (sigma_Jc/Jc)^2
      approximately
    (sigma_Ic/Ic)^2 + (sigma_w/w)^2 + (sigma_d/d)^2

로 쓸 수 있습니다.

이 식으로 얻은 상대오차를 `--jc-error-percent`에 입력하면 됩니다.

---

## 10. xi가 변해도 lambda가 상대적으로 약하게 변하는 이유

Program 1과 Program 2에서

    Jc proportional to [ln(lambda/xi)+0.5] / lambda^3

입니다.

xi는 로그 항을 통해서만 들어가지만,
lambda는 주로 lambda^-3 형태로 강하게 들어갑니다.

따라서 xi가 눈에 띄게 변하더라도 추출된 lambda의 상대적인 변화량은
그보다 작을 수 있습니다.

이 점은 원 논문에서 kappa의 온도 의존성을 비교적 약한 correction으로
취급할 수 있다고 본 이유이기도 합니다.

---

## 11. 필요한 Python 패키지

Python 3.10 이상을 권장합니다.

설치:

    pip install numpy pandas scipy

프로그램은 CSV 파일을 출력하며,
Excel이나 plotting library는 필요하지 않습니다.

---

## 12. 데이터 분석에 권장하는 workflow

T, self-field Jc, Hc2가 모두 측정된 데이터셋의 경우:

1. Program 1을 사용합니다.
2. xi(T), lambda(T), kappa(T)를 확인합니다.
3. kappa가 전체 온도 범위에서 충분히 type-II regime에 머무는지 확인합니다.
4. 대표적인 constant kappa 값을 사용하여 Program 3의 lambda(T)와 비교하고,
   kappa의 온도 의존성을 고려하는 것이 결과에 얼마나 중요한지 정량화합니다.
5. 현실적인 Jc 및 Hc2 uncertainty를 넣어 계산을 반복합니다.
6. 그 이후에 low-temperature lambda(T) 또는 superfluid density
   lambda^-2(T)를 gap model에 fitting하는 것이 좋습니다.

xi(T)가 이미 독립적인 방법으로 결정되어 있는 데이터셋의 경우에는
Program 2를 사용하고 Hc2-to-xi 변환 단계를 생략합니다.
