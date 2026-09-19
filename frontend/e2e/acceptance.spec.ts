import { test, expect, type Page } from '@playwright/test'
import { readFileSync } from 'node:fs'
import { join } from 'node:path'

/**
 * The acceptance walkthrough of specs/001-jc-to-gap/quickstart.md, executed.
 *
 * Every test here names the scenario or requirement it stands for. A scenario
 * that is only ever performed by hand is a scenario that quietly stops being
 * performed, and these are the ones that decide whether the feature is done.
 *
 * The data are pasted in from the backend's fixtures rather than loaded from
 * the application. FR-028 was withdrawn and the built-in examples went with
 * it, so what these tests now drive is the path a user's own file takes: text
 * into the box, settings chosen by hand.
 */

const heading = (page: Page, name: string) => page.getByRole('heading', { name })

const FIXTURES = join('..', 'backend', 'tests', 'data')

/** The two fixtures, with the settings each is meant to be read under.
 *
 * `hc2` needs none: the page already defaults to FROM_HC2, CLEAN, TWO_STEP,
 * which is worth saying here because a test below reads as though it set
 * nothing. `kappa` has no Hc2 column and has to be told so.
 */
const DATA = {
  hc2: 'weak_coupling_clean_hc2.txt',
  kappa: 'strong_coupling_dirty_kappa.txt',
} as const

async function loadFixture(page: Page, which: keyof typeof DATA) {
  await page.goto('/')
  await page.locator('textarea.data-input')
    .fill(readFileSync(join(FIXTURES, DATA[which]), 'utf8'))
  await expect(heading(page, '읽은 결과 확인')).toBeVisible()

  if (which === 'kappa') {
    await page.getByLabel('코히런스 길이 ξ 결정 방식').selectOption('FIXED_KAPPA')
    await page.getByLabel('κ = λ/ξ').fill('30')
    await page.getByLabel('갭 모델').selectOption('DIRTY')
  }
}

/** The assumptions panel, found by its heading rather than by its text.
 *
 * By text it matched two cards the moment the fit summary started pointing
 * the reader to this panel by name (FR-023a). The same trap as the charts
 * card, whose title also occurs in other cards' prose.
 */
const assumptionsPanel = (page: Page) =>
  page.locator('section.card').filter({
    has: page.getByRole('heading', { name: '가정과 주의사항', exact: true }),
  })

async function analyse(page: Page) {
  await page.getByRole('button', { name: '분석 실행' }).click()
  await expect(heading(page, '피팅 결과')).toBeVisible()
}

/** The value cell of one row of the fit summary.
 *
 * Scoped to the card, because the diagnostics panel below it uses the same
 * table markup and would otherwise be matched too.
 */
function fitValue(page: Page, quantity: string) {
  return page.locator('section.card', { hasText: '피팅 결과' })
    .locator('table.results tr', { has: page.locator(`th:text-is("${quantity}")`) })
    .locator('td.value').first()
}

async function fitNumber(page: Page, quantity: string): Promise<number> {
  const text = await fitValue(page, quantity).innerText()
  return Number(text.split('±')[0].trim())
}

// --- FR-029a: what an empty page offers, now that it offers no data ---------

test('the empty page explains the format and hands out nothing to run',
  async ({ page }) => {
    await page.goto('/')
    await expect(heading(page, 'Nodeless 초전도체 갭 추출')).toBeVisible()

    // No data yet, so nothing can be analysed.
    await expect(page.getByRole('button', { name: '분석 실행' })).toBeDisabled()

    // And nothing on the page will supply any. FR-028 was withdrawn because a
    // manufactured dataset shipped beside a measurement tool reads as a claim
    // about real samples, and the buttons that loaded one are gone. Asserted
    // rather than assumed, because putting one back would be an easy kindness.
    const toolbar = page.locator('section.card', { hasText: '1. 데이터 입력' })
    await expect(toolbar.getByRole('button')).toHaveCount(2)   // 파일 열기, 지우기
    await expect(page.getByText('예제', { exact: false })).toHaveCount(0)

    // What replaces it is the layout itself.
    const box = page.locator('textarea.data-input')
    const placeholder = await box.getAttribute('placeholder')
    expect(placeholder).toContain('T_K')
    expect(placeholder).toContain('Hc2_T')
    expect(placeholder).toContain('최소 4점')
    // The illustrative rows must be too few to run, so that a format example
    // cannot be mistaken for a dataset.
    const rows = placeholder!.split('\n').filter(l => /^\s+[\d.]+\s/.test(l))
    expect(rows.length).toBeLessThan(4)
  })

test('a pasted file runs the whole thing', async ({ page }) => {
  await loadFixture(page, 'hc2')
  await expect(page.getByText('22개 데이터, 3개 열')).toBeVisible()
  await analyse(page)
  await expect(fitValue(page, 'Δ(0)')).not.toBeEmpty()
})

// --- AS-1, FR-006..FR-012: analysis from the upper critical field -----------

test('recovers the parameters the example was generated from', async ({ page }) => {
  await loadFixture(page, 'hc2')
  await analyse(page)

  // The fixture's header states lambda(0) = 250 nm, Delta(0) = 1.3993 meV,
  // Tc = 9.2 K. Scatter on Jc is 0.2 %, so a few tenths of a per cent is the
  // most that should be missed.
  expect(await fitNumber(page, 'λ(0)')).toBeCloseTo(250.0, 0)
  expect(await fitNumber(page, 'Δ(0)')).toBeCloseTo(1.3993, 2)
  expect(await fitNumber(page, 'Tc')).toBeCloseTo(9.2, 1)
  expect(await fitNumber(page, '2Δ(0)/k_BTc')).toBeCloseTo(3.53, 1)

  await expect(page.locator('span.badge.regime-WEAK_COUPLING_BCS')).toBeVisible()
  // FR-012: every fitted parameter carries a standard uncertainty.
  await expect(page.locator('section.card', { hasText: '피팅 결과' })
    .locator('table.results').first()).toContainText('±')
})

// --- AS-3, FR-006: the fixed-kappa route ------------------------------------

test('the fixed-kappa route reports the coherence length it implies', async ({ page }) => {
  await loadFixture(page, 'kappa')
  await analyse(page)

  expect(await fitNumber(page, 'λ(0)')).toBeCloseTo(120, -1)
  // xi is an output here, not an input, and must appear in the table.
  const table = page.locator('section.card', { hasText: '온도별 결과' })
  await expect(table).toContainText('ξ [nm]')
  await expect(table.locator('tbody tr').first()).toContainText('30.00')
})

// --- AS-5, FR-011: the two routes agree -------------------------------------

test('the two extraction routes agree', async ({ page }) => {
  await loadFixture(page, 'hc2')
  await analyse(page)
  const twoStep = await fitNumber(page, 'Δ(0)')

  await page.getByLabel('추출 경로').selectOption('DIRECT')
  await analyse(page)
  const direct = await fitNumber(page, 'Δ(0)')

  expect(Math.abs(direct - twoStep) / twoStep).toBeLessThan(0.02)
})

// --- AS-4, FR-020: the models are compared ----------------------------------

test('a decisive model comparison is reported when the data support one', async ({ page }) => {
  await loadFixture(page, 'hc2')   // 0.2 % scatter: separable
  await analyse(page)
  const assumptions = assumptionsPanel(page)
  await expect(assumptions).not.toContainText('판정할 수 없습니다')
})

test('and refused when they do not', async ({ page }) => {
  await loadFixture(page, 'kappa')  // 3 % scatter: not separable
  await analyse(page)
  const assumptions = assumptionsPanel(page)
  await expect(assumptions).toContainText('판정할 수 없습니다')
  await expect(assumptions).toContainText('ΔAIC')
})

// --- FR-023a: data that do not determine the coupling ratio ------------------

test('data from a helium dip alone do not get a coupling regime', async ({ page }) => {
  // The hc2 fixture cut at 2.8 K, about 0.3 Tc: the dataset a 4.2 K bath and
  // a pump would give. Through the API this returns a ratio of 3.97 against a
  // true 3.53, which used to be labelled moderately strong coupling.
  const all = readFileSync(join(FIXTURES, DATA.hc2), 'utf8').split('\n')
  const cold = all.filter((line) => {
    if (line.trimStart().startsWith('#') || !line.trim()) return true
    return Number(line.trim().split(/\s+/)[0]) <= 2.8
  })
  await page.goto('/')
  await page.locator('textarea.data-input').fill(cold.join('\n'))
  await expect(heading(page, '읽은 결과 확인')).toBeVisible()
  await analyse(page)

  // No regime is named, and the badge says why rather than offering a fifth
  // answer.
  const summary = page.locator('section.card', { hasText: '피팅 결과' })
  await expect(summary.locator('.badge.regime-UNDETERMINED')).toContainText('판정 불가')
  for (const regime of ['약결합', '강결합']) {
    await expect(summary.locator('.badges .badge').first()).not.toContainText(regime)
  }
  // Nor is it named by the back door: a percentage of the BCS value, to a
  // tenth of a per cent, is a regime judgement in all but name.
  await expect(summary).not.toContainText('%입니다')
  await expect(summary).toContainText('BCS 값과 비교하지 않습니다')

  // The assumptions panel says so in words, names every reason, and does not
  // send the user off to fix Tc, which research R10 measured as no remedy.
  const assumptions = assumptionsPanel(page)
  await expect(assumptions).toContainText('결합비 2Δ(0)/k_BTc가 정해지지 않습니다')
  await expect(assumptions).toContainText('0.4배')
  await expect(assumptions).toContainText('Tc를 고정해도 해결되지 않습니다')
  // Tc was free here, so Delta(0) is not condemned wholesale: research R10
  // measured its own error bar as honest in this mode, and the fixture's
  // Delta(0) comes out right.
  await expect(assumptions).toContainText('Δ(0) 오차 막대는 정직했습니다')

  // lambda(0) is still reported, and still right: the coldest points set it.
  expect(await fitNumber(page, 'λ(0)')).toBeCloseTo(250, 0)
})

// --- AS-7, FR-022: an assumption that fails ---------------------------------

test('a kappa below the model floor is refused with an explanation', async ({ page }) => {
  await loadFixture(page, 'kappa')
  await page.getByLabel('κ = λ/ξ').fill('0.5')
  await page.getByRole('button', { name: '분석 실행' }).click()

  const message = page.locator('.message.error')
  await expect(message).toContainText('ln(kappa) + 0.5')
  await expect(message).toContainText('0.6065')
  await expect(heading(page, '피팅 결과')).toHaveCount(0)
})

test('a kappa inside type-II but near the boundary warns rather than refuses', async ({ page }) => {
  await loadFixture(page, 'kappa')
  await page.getByLabel('κ = λ/ξ').fill('2')
  await analyse(page)
  await expect(assumptionsPanel(page))
    .toContainText('Hc1 근사')
})

// --- FR-024: assumptions travel with the result -----------------------------

test('the self-field requirement is stated on every result', async ({ page }) => {
  for (const which of ['hc2', 'kappa'] as const) {
    await loadFixture(page, which)
    await analyse(page)
    await expect(assumptionsPanel(page))
      .toContainText('self-field 조건에서 transport 방식')
  }
})

test('a thickness beyond the thin-film regime warns', async ({ page }) => {
  await loadFixture(page, 'hc2')
  await page.getByLabel('시료 두께 [nm]').fill('5000')     // lambda(0) is 250 nm
  await analyse(page)
  await expect(assumptionsPanel(page))
    .toContainText('박막을 대상으로 유도된')
})

// --- FR-003, FR-005: bad input is caught early ------------------------------

test('a non-numeric cell is reported with its location, before any physics', async ({ page }) => {
  await page.goto('/')
  await page.locator('textarea').fill(
    'T Jc Hc2\n2 1e6 12\n4 OL 10\n6 6e5 8\n8 2e5 4\n'
  )
  const message = page.locator('.message.error')
  await expect(message).toContainText('"OL"')
  await expect(message).toContainText('3번째 줄')
  await expect(page.getByRole('button', { name: '분석 실행' })).toBeDisabled()
})

test('too few points is refused', async ({ page }) => {
  await page.goto('/')
  await page.locator('textarea').fill('2 1e6 12\n4 9e5 10\n')
  await expect(page.locator('.message.error')).toContainText('최소 4개')
})

test('the column preview says which column is being used as what', async ({ page }) => {
  await loadFixture(page, 'hc2')
  const preview = page.locator('section.card', { hasText: '읽은 결과 확인' })
  await expect(preview).toContainText('온도 T')
  await expect(preview).toContainText('Hc2')

  // Switching to the fixed-kappa route drops the third column from use.
  await page.getByLabel('코히런스 길이 ξ 결정 방식').selectOption('FIXED_KAPPA')
  await expect(preview.locator('th.unused')).toHaveCount(1)
})

test('changing the data cannot leave the previous result on screen', async ({ page }) => {
  // The analyse button must not be usable while the text on screen has not been
  // parsed yet, or a paste followed by a quick click analyses the old dataset.
  await loadFixture(page, 'hc2')
  await analyse(page)

  await page.locator('textarea.data-input')
    .fill(readFileSync(join(FIXTURES, DATA.kappa), 'utf8'))
  await expect(heading(page, '피팅 결과')).toHaveCount(0)

  await page.getByLabel('코히런스 길이 ξ 결정 방식').selectOption('FIXED_KAPPA')
  await page.getByLabel('κ = λ/ξ').fill('30')
  await page.getByLabel('갭 모델').selectOption('DIRTY')
  await analyse(page)
  // The second dataset's own answer, not the first one's: lambda(0) is 120 nm
  // here and 250 nm there, so a stale result could not pass this.
  expect(await fitNumber(page, 'λ(0)')).toBeCloseTo(120, -1)
})

// --- AS-10, FR-027: taking the results away ---------------------------------

test('the results can be downloaded as a table with units in the headers', async ({ page }) => {
  await loadFixture(page, 'hc2')
  await analyse(page)

  const [download] = await Promise.all([
    page.waitForEvent('download'),
    page.getByRole('button', { name: '결과 CSV 내려받기' }).click(),
  ])
  expect(download.suggestedFilename()).toBe('nodeless_sc_result.csv')

  const stream = await download.createReadStream()
  const chunks: Buffer[] = []
  for await (const chunk of stream) chunks.push(chunk as Buffer)
  const csv = Buffer.concat(chunks).toString('utf8')

  expect(csv).toContain(
    'T_K,Jc_A_per_m2,Jc_model_A_per_m2,xi_nm,lambda_nm,kappa,rho_s_measured,fit_residual')
  expect(csv).toContain('SELF_FIELD_TRANSPORT_REQUIRED')
  expect(csv).toContain('lambda(0) [nm]')

  // FR-026a. The example is noiseless synthetic data generated from equation
  // (1), so the prediction has to land on the measurement it was fitted to.
  // A wrong column order, or a prediction built from someone else's xi, moves
  // this far enough to fail while still looking like a plausible number.
  const rows = csv.split('\n').filter(l => l && !l.startsWith('#') && !l.startsWith('T_K'))
  for (const row of rows) {
    const [, jc, jcModel] = row.split(',').map(Number)
    expect(jcModel).toBeGreaterThan(0)
    expect(Math.abs(jcModel / jc - 1)).toBeLessThan(0.02)
  }
})

// --- FR-027a: the fitted curve as numbers ------------------------------------

test('the fitted curve can be downloaded and starts on the reported intercept',
  async ({ page }) => {
    await loadFixture(page, 'hc2')
    await analyse(page)

    // The number the summary reports, as the user reads it off the screen.
    const summary = page.locator('section.card', { hasText: '피팅 결과' })
    const lambda0 = await summary.getByRole('row', { name: /λ\(0\)/ }).innerText()
    const intercept = Number(lambda0.match(/([\d.]+)\s*±/)![1])

    const [download] = await Promise.all([
      page.waitForEvent('download'),
      page.getByRole('button', { name: '피팅 곡선 CSV 내려받기' }).click(),
    ])
    expect(download.suggestedFilename()).toBe('nodeless_sc_curve.csv')

    const stream = await download.createReadStream()
    const chunks: Buffer[] = []
    for await (const chunk of stream) chunks.push(chunk as Buffer)
    const csv = Buffer.concat(chunks).toString('utf8')

    expect(csv).toContain('T_K,rho_s_model,lambda_model_nm,Jc_model_A_per_m2')
    // Constitution VI: this file may be opened without the other one.
    expect(csv).toContain('SELF_FIELD_TRANSPORT_REQUIRED')

    const rows = csv.split('\n').filter(l => l && !l.startsWith('#') && !l.startsWith('T_K'))
    expect(rows.length).toBeGreaterThan(100)

    // FR-026: the first row is T = 0, and lambda there is the fitted lambda(0)
    // the user was just shown -- not an extrapolation towards it.
    const [t0, rho0, lam0] = rows[0].split(',').map(Number)
    expect(t0).toBe(0)
    expect(rho0).toBe(1)
    expect(lam0).toBeCloseTo(intercept, 2)

    // FR-026a: this example is fitted from Hc2, so the model Jc exists only
    // between the coldest and hottest measurement. Absolute zero is outside
    // that, and the cell there is blank rather than zero -- a spreadsheet
    // reads a blank as missing and a zero as a measured value.
    expect(rows[0].split(',')[3]).toBe('')
    expect(rows.some(r => r.split(',')[3] !== '')).toBe(true)
  })

// --- FR-026, FR-019: the plots ----------------------------------------------

test('all four plots draw', async ({ page }) => {
  await loadFixture(page, 'hc2')
  await analyse(page)
  const charts = page.locator('section.card').filter({
    has: page.getByRole('heading', { name: '그래프', exact: true }),
  })

  for (const tab of ['초전도 밀도 ρs(T)', '침투깊이 λ(T)', '임계전류밀도 Jc(T)', '잔차']) {
    await charts.getByRole('tab', { name: tab }).click()
    await expect(charts.locator('.js-plotly-plot')).toBeVisible()
    // Two traces on all but the residual tab (data and model), one there.
    const traces = charts.locator('.js-plotly-plot .scatterlayer .trace')
    await expect(traces.first()).toBeVisible()
  }
})

test('the Jc plot shows the measurement and the fitted curve together',
  async ({ page }) => {
    await loadFixture(page, 'hc2')
    await analyse(page)
    const charts = page.locator('section.card').filter({
      has: page.getByRole('heading', { name: '그래프', exact: true }),
    })
    await charts.getByRole('tab', { name: '임계전류밀도 Jc(T)' }).click()

    await expect(charts.locator('.js-plotly-plot .scatterlayer .trace')).toHaveCount(2)
    await expect(charts.getByText('측정', { exact: true })).toBeVisible()

    // FR-026a: the hint has to say why this curve stops where the measurements
    // do while the two beside it run from absolute zero to Tc. The example is
    // fitted from Hc2, so the restriction applies to it.
    await expect(charts.getByText(/측정 온도 범위 안에서만/)).toBeVisible()
  })

test('the plot offers a PNG download', async ({ page }) => {
  await loadFixture(page, 'hc2')
  await analyse(page)
  const charts = page.locator('section.card').filter({
    has: page.getByRole('heading', { name: '그래프', exact: true }),
  })
  await expect(charts.locator('.modebar-btn').first()).toBeAttached()
  expect(await charts.locator('.modebar-btn').count()).toBeGreaterThan(2)
})

// --- FR-019 to FR-021: the diagnostics panel --------------------------------

test('the diagnostics panel reports the basis for its judgements', async ({ page }) => {
  await loadFixture(page, 'hc2')
  await analyse(page)
  const panel = page.locator('section.card', { hasText: '피팅 품질 진단' })

  await expect(panel).toContainText('χ²_red')
  await expect(panel).toContainText('결합 세기')
  await expect(panel).toContainText('BCS 3.52775')     // FR-021
  await expect(panel).toContainText('저온 도달도')
  await expect(panel).toContainText('κ 범위')
  await expect(panel).toContainText('ΔAIC')            // FR-020
  await expect(panel).toContainText('선호')
})

test('the diagnostics panel declines to choose when it should', async ({ page }) => {
  await loadFixture(page, 'kappa')
  await analyse(page)
  await expect(page.locator('section.card', { hasText: '피팅 품질 진단' }))
    .toContainText('판정하지 않습니다')
})

// --- FR-015 to FR-018, FR-029, FR-030: uncertainty propagation --------------

test('uncertainty propagation runs in the background and reports intervals', async ({ page }) => {
  test.setTimeout(180_000)
  await loadFixture(page, 'kappa')
  await analyse(page)

  const panel = page.locator('section.card', { hasText: '측정 오차 전파' })
  await panel.getByLabel('Jc 오차 [%]').fill('5')
  await panel.getByLabel('오차의 성격').selectOption('INDEPENDENT')
  await panel.getByLabel('표본 수').fill('200')
  await panel.getByRole('button', { name: '오차 전파 실행' }).click()

  // FR-018: it says it is running, and the rest of the page keeps working.
  await expect(panel.getByRole('progressbar')).toBeVisible()
  await expect(page.getByRole('heading', { name: '그래프' })).toBeVisible()

  // FR-030: the propagated interval appears next to the fit standard error,
  // in its own column, rather than replacing it.
  const summary = page.locator('section.card', { hasText: '피팅 결과' })
  await expect(summary).toContainText('측정 오차 전파', { timeout: 150_000 })
  await expect(summary).toContainText('seed')
})

test('a systematic Jc error moves lambda but not the gap', async ({ page }) => {
  // Research R8.3, visible to the user: under a fixed kappa the superfluid
  // density is a ratio in which a common scale factor cancels, so a geometry
  // calibration error cannot move Delta(0) at all.
  test.setTimeout(180_000)
  await loadFixture(page, 'kappa')
  await analyse(page)

  const panel = page.locator('section.card', { hasText: '측정 오차 전파' })
  await panel.getByLabel('Jc 오차 [%]').fill('5')
  await panel.getByLabel('오차의 성격').selectOption('SYSTEMATIC')
  await panel.getByLabel('표본 수').fill('200')
  await panel.getByRole('button', { name: '오차 전파 실행' }).click()

  const summary = page.locator('section.card', { hasText: '피팅 결과' })
  await expect(summary).toContainText('측정 오차 전파', { timeout: 150_000 })

  const mcCell = (quantity: string) =>
    summary.locator('tr', { has: page.locator(`th:text-is("${quantity}")`) })
      .locator('td.value').nth(1)

  const read = async (quantity: string) => {
    const [mean, sd] = (await mcCell(quantity).innerText()).split('±')
    return Math.abs(Number(sd) / Number(mean))
  }
  // lambda(0) moves by about a third of the stated Jc error; the gap does not
  // move at all. Not exactly zero, because the optimiser stops at a tolerance
  // rather than at the exact minimum, so the invariance shows up as a relative
  // spread of order 1e-8 -- six orders below the lambda(0) one.
  const lambdaSpread = await read('λ(0)')
  const deltaSpread = await read('Δ(0)')
  expect(lambdaSpread).toBeGreaterThan(1e-2)
  expect(deltaSpread).toBeLessThan(1e-6)
})

// --- constitution VIII: the page is Korean, the payloads are not -------------

test('the page is in Korean and the API still speaks only codes', async ({ page }) => {
  const bodies: string[] = []
  page.on('response', async (r) => {
    if (r.url().includes('/api/') && r.request().method() !== 'GET') return
    if (r.url().includes('/api/')) {
      try { bodies.push(await r.text()) } catch { /* binary */ }
    }
  })

  await loadFixture(page, 'hc2')
  await analyse(page)

  await expect(page.getByRole('heading', { name: '피팅 결과' })).toBeVisible()
  for (const body of bodies) {
    expect(body, 'an API response contained non-ASCII text').toMatch(/^[\x00-\x7F]*$/)
  }
})
