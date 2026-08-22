import { test, expect, type Page } from '@playwright/test'

/**
 * The acceptance walkthrough of specs/001-jc-to-gap/quickstart.md, executed.
 *
 * Every test here names the scenario or requirement it stands for. A scenario
 * that is only ever performed by hand is a scenario that quietly stops being
 * performed, and these are the ones that decide whether the feature is done.
 */

const heading = (page: Page, name: string) => page.getByRole('heading', { name })

async function loadExample(page: Page, name: string) {
  await page.goto('/')
  await page.getByRole('button', { name }).click()
  await expect(heading(page, '읽은 결과 확인')).toBeVisible()
}

async function analyse(page: Page) {
  await page.getByRole('button', { name: '분석 실행' }).click()
  await expect(heading(page, '피팅 결과')).toBeVisible()
}

/** The value cell of one row of the fit summary. */
function fitValue(page: Page, quantity: string) {
  return page.locator('table.results tr', { has: page.locator(`th:text-is("${quantity}")`) })
    .locator('td.value').first()
}

async function fitNumber(page: Page, quantity: string): Promise<number> {
  const text = await fitValue(page, quantity).innerText()
  return Number(text.split('±')[0].trim())
}

// --- AS-9, FR-028: the tool works before you have data ----------------------

test('a first-time user can run the whole thing from a built-in example', async ({ page }) => {
  await page.goto('/')
  await expect(heading(page, 'Nodeless 초전도체 갭 추출')).toBeVisible()

  // No data yet, so nothing can be analysed.
  await expect(page.getByRole('button', { name: '분석 실행' })).toBeDisabled()

  await page.getByRole('button', { name: 'nbti_like' }).click()
  await expect(page.getByText('22개 데이터, 3개 열')).toBeVisible()
  await analyse(page)
  await expect(fitValue(page, 'Δ(0)')).not.toBeEmpty()
})

// --- AS-1, FR-006..FR-012: analysis from the upper critical field -----------

test('recovers the parameters the example was generated from', async ({ page }) => {
  await loadExample(page, 'nbti_like')
  await analyse(page)

  // The header of nbti_like states lambda(0) = 250 nm, Delta(0) = 1.3993 meV,
  // Tc = 9.2 K. Scatter on Jc is 0.2 %, so a few tenths of a per cent is the
  // most that should be missed.
  expect(await fitNumber(page, 'λ(0)')).toBeCloseTo(250.0, 0)
  expect(await fitNumber(page, 'Δ(0)')).toBeCloseTo(1.3993, 2)
  expect(await fitNumber(page, 'Tc')).toBeCloseTo(9.2, 1)
  expect(await fitNumber(page, '2Δ(0)/k_BTc')).toBeCloseTo(3.53, 1)

  await expect(page.getByText('BCS 약결합', { exact: true })).toBeVisible()
  // FR-012: every fitted parameter carries a standard uncertainty.
  await expect(page.locator('section.card', { hasText: '피팅 결과' })
    .locator('table.results').first()).toContainText('±')
})

// --- AS-3, FR-006: the fixed-kappa route ------------------------------------

test('the fixed-kappa route reports the coherence length it implies', async ({ page }) => {
  await loadExample(page, 'nb3sn_like')
  await expect(page.getByLabel('κ = λ/ξ')).toHaveValue('30')
  await analyse(page)

  expect(await fitNumber(page, 'λ(0)')).toBeCloseTo(120, -1)
  // xi is an output here, not an input, and must appear in the table.
  const table = page.locator('section.card', { hasText: '온도별 결과' })
  await expect(table).toContainText('ξ [nm]')
  await expect(table.locator('tbody tr').first()).toContainText('30.00')
})

// --- AS-5, FR-011: the two routes agree -------------------------------------

test('the two extraction routes agree', async ({ page }) => {
  await loadExample(page, 'nbti_like')
  await analyse(page)
  const twoStep = await fitNumber(page, 'Δ(0)')

  await page.getByLabel('추출 경로').selectOption('DIRECT')
  await analyse(page)
  const direct = await fitNumber(page, 'Δ(0)')

  expect(Math.abs(direct - twoStep) / twoStep).toBeLessThan(0.02)
})

// --- AS-4, FR-020: the models are compared ----------------------------------

test('a decisive model comparison is reported when the data support one', async ({ page }) => {
  await loadExample(page, 'nbti_like')   // 0.2 % scatter: separable
  await analyse(page)
  const assumptions = page.locator('section.card', { hasText: '가정과 주의사항' })
  await expect(assumptions).not.toContainText('판정할 수 없습니다')
})

test('and refused when they do not', async ({ page }) => {
  await loadExample(page, 'nb3sn_like')  // 3 % scatter: not separable
  await analyse(page)
  const assumptions = page.locator('section.card', { hasText: '가정과 주의사항' })
  await expect(assumptions).toContainText('판정할 수 없습니다')
  await expect(assumptions).toContainText('ΔAIC')
})

// --- AS-7, FR-022: an assumption that fails ---------------------------------

test('a kappa below the model floor is refused with an explanation', async ({ page }) => {
  await loadExample(page, 'nb3sn_like')
  await page.getByLabel('κ = λ/ξ').fill('0.5')
  await page.getByRole('button', { name: '분석 실행' }).click()

  const message = page.locator('.message.error')
  await expect(message).toContainText('ln(kappa) + 0.5')
  await expect(message).toContainText('0.6065')
  await expect(heading(page, '피팅 결과')).toHaveCount(0)
})

test('a kappa inside type-II but near the boundary warns rather than refuses', async ({ page }) => {
  await loadExample(page, 'nb3sn_like')
  await page.getByLabel('κ = λ/ξ').fill('2')
  await analyse(page)
  await expect(page.locator('section.card', { hasText: '가정과 주의사항' }))
    .toContainText('Hc1 근사')
})

// --- FR-024: assumptions travel with the result -----------------------------

test('the self-field requirement is stated on every result', async ({ page }) => {
  for (const example of ['nbti_like', 'nb3sn_like']) {
    await loadExample(page, example)
    await analyse(page)
    await expect(page.locator('section.card', { hasText: '가정과 주의사항' }))
      .toContainText('self-field 조건에서 transport 방식')
  }
})

test('a thickness beyond the thin-film regime warns', async ({ page }) => {
  await loadExample(page, 'nbti_like')
  await page.getByLabel('시료 두께 [nm]').fill('5000')     // lambda(0) is 250 nm
  await analyse(page)
  await expect(page.locator('section.card', { hasText: '가정과 주의사항' }))
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
  await loadExample(page, 'nbti_like')
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
  await loadExample(page, 'nbti_like')
  await analyse(page)
  await page.getByRole('button', { name: 'nb3sn_like' }).click()
  await expect(heading(page, '피팅 결과')).toHaveCount(0)
  await analyse(page)
  await expect(page.getByLabel('κ = λ/ξ')).toHaveValue('30')
})

// --- AS-10, FR-027: taking the results away ---------------------------------

test('the results can be downloaded as a table with units in the headers', async ({ page }) => {
  await loadExample(page, 'nbti_like')
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

  expect(csv).toContain('T_K,Jc_A_per_m2,xi_nm,lambda_nm,kappa')
  expect(csv).toContain('SELF_FIELD_TRANSPORT_REQUIRED')
  expect(csv).toContain('lambda(0) [nm]')
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

  await loadExample(page, 'nbti_like')
  await analyse(page)

  await expect(page.getByRole('heading', { name: '피팅 결과' })).toBeVisible()
  for (const body of bodies) {
    expect(body, 'an API response contained non-ASCII text').toMatch(/^[\x00-\x7F]*$/)
  }
})
