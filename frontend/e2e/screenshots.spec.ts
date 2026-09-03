import { test, expect } from '@playwright/test'

/**
 * Not assertions: a way to look at the page.
 *
 * Captures the states worth reviewing by eye into e2e/.shots/, so that layout,
 * spacing, and the Korean wording can be judged rather than guessed at. Run
 * with `npm run shots`.
 */

const SHOTS = 'e2e/.shots'

test('capture the states worth looking at', async ({ page }) => {
  test.setTimeout(120_000)

  // 1. Empty page, before anything has been entered.
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'Nodeless 초전도체 갭 추출' })).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/01-empty.png`, fullPage: true })

  // 2. An example loaded: the column preview and the settings it suggests.
  await page.getByRole('button', { name: 'nbti_like' }).click()
  await expect(page.getByRole('heading', { name: '읽은 결과 확인' })).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/02-example-loaded.png`, fullPage: true })

  // 3. The full result.
  await page.getByRole('button', { name: '분석 실행' }).click()
  await expect(page.getByRole('heading', { name: '피팅 결과' })).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/03-analysed.png`, fullPage: true })

  // 4. Just the results, at readable size.
  await page.locator('section.card', { hasText: '피팅 결과' })
    .screenshot({ path: `${SHOTS}/04-fit-summary.png` })

  // 4b. Each plot. These are the only way to see whether the model actually
  // follows the data, which no summary statistic can tell you.
  // Scoped by the heading, not by any text: '그래프' also occurs in the
  // diagnostics panel's prose.
  const charts = page.locator('section.card').filter({
    has: page.getByRole('heading', { name: '그래프', exact: true }),
  })
  for (const [tab, name] of [
    ['초전도 밀도 ρs(T)', 'rho-s'],
    ['침투깊이 λ(T)', 'lambda'],
    ['임계전류밀도 Jc(T)', 'jc'],
    ['잔차', 'residuals'],
  ] as const) {
    await charts.getByRole('tab', { name: tab }).click()
    await expect(charts.locator('.js-plotly-plot')).toBeVisible()
    await page.waitForTimeout(700)      // let Plotly finish drawing
    await charts.screenshot({ path: `${SHOTS}/04b-chart-${name}.png` })
  }
  await charts.getByRole('tab', { name: '초전도 밀도 ρs(T)' }).click()
  await page.locator('section.card', { hasText: '가정과 주의사항' })
    .screenshot({ path: `${SHOTS}/05-assumptions.png` })

  // 5. The other example, whose data cannot separate the two gap models.
  //
  // The assertions here are not decoration. Twice this step silently captured
  // the *previous* example's result, because the analyse button was still
  // enabled while the newly pasted text had not been parsed yet. Checking that
  // the settings actually changed is what caught it.
  await page.getByRole('button', { name: 'nb3sn_like' }).click()
  await expect(page.locator('section.card', { hasText: '분석 설정' })
    .getByRole('combobox').nth(1)).toHaveValue('FIXED_KAPPA')
  await page.getByRole('button', { name: '분석 실행' }).click()
  await expect(page.getByRole('heading', { name: '피팅 결과' })).toBeVisible()
  const assumptions = page.locator('section.card', { hasText: '가정과 주의사항' })
  await expect(assumptions).toContainText('clean과 dirty')      // MODELS_INDISTINGUISHABLE
  await expect(assumptions).not.toContainText('Ginzburg-Landau') // not the Hc2 route
  await assumptions.screenshot({ path: `${SHOTS}/06-models-indistinguishable.png` })

  // 5b. The Jc plot under a fixed kappa, which is the other half of FR-026a.
  // There the coherence length follows the fit, so the curve runs from absolute
  // zero to Tc instead of stopping at the data -- and falls orders of magnitude
  // past anything measured on the way, which is what the axis range in
  // Charts.tsx exists to keep from squashing the points into a strip.
  await charts.getByRole('tab', { name: '임계전류밀도 Jc(T)' }).click()
  await expect(charts.locator('.js-plotly-plot')).toBeVisible()
  await page.waitForTimeout(700)
  await charts.screenshot({ path: `${SHOTS}/06b-chart-jc-fixed-kappa.png` })

  // 6. A refusal, rendered in Korean rather than as a stack trace.
  //
  // kappa below exp(-0.5) makes ln(kappa) + 0.5 negative, so equation (1) would
  // return a negative Jc. The backend refuses with KAPPA_TOO_SMALL and the page
  // has to explain that rather than showing a blank result.
  await page.getByLabel('κ = λ/ξ').fill('0.5')
  await page.getByRole('button', { name: '분석 실행' }).click()
  await expect(page.locator('.message.error')).toContainText('ln(kappa) + 0.5')
  await page.screenshot({ path: `${SHOTS}/07-error.png`, fullPage: true })
  await page.locator('.message.error').screenshot({ path: `${SHOTS}/07b-error-detail.png` })

  // 7. A wrong unit is NOT a failure, and that is worth seeing.
  //
  // Both A/cm^2 and A/m^2 are physically possible, so nothing can detect the
  // mistake; it just moves lambda(0) by a factor of 21.5. This is what the
  // hint under the unit selector is warning about.
  await page.getByLabel('κ = λ/ξ').fill('30')
  await page.getByLabel('Jc 단위').selectOption('A_PER_M2')
  await page.getByRole('button', { name: '분석 실행' }).click()
  await expect(page.getByRole('heading', { name: '피팅 결과' })).toBeVisible()
  await page.locator('section.card', { hasText: '피팅 결과' })
    .screenshot({ path: `${SHOTS}/07c-wrong-unit-still-succeeds.png` })

  // 7. Narrow viewport, to see whether anything overflows.
  await page.setViewportSize({ width: 420, height: 900 })
  await page.goto('/')
  await page.getByRole('button', { name: 'nbti_like' }).click()
  await page.getByRole('button', { name: '분석 실행' }).click()
  await expect(page.getByRole('heading', { name: '피팅 결과' })).toBeVisible()
  await page.screenshot({ path: `${SHOTS}/08-narrow.png`, fullPage: true })
})
