/**
 * `plotly.js-basic-dist-min` ships no types of its own.
 *
 * It is the same API as `plotly.js` with only the trace types this project uses
 * (scatter and lines) compiled in -- 1.1 MB instead of about 4.5 MB, which is
 * worth having for a page that draws two line charts. Pointing its types at the
 * full package is accurate for everything we call.
 */
declare module 'plotly.js-basic-dist-min' {
  import type * as Plotly from 'plotly.js'
  const plotly: typeof Plotly
  export default plotly
}
