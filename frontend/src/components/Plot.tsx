/**
 * A thin React wrapper around Plotly.
 *
 * Written by hand rather than pulling in react-plotly.js: that package is one
 * more dependency to keep current, and all it does is what the twenty lines
 * below do. Plotly itself earns its place -- it gives interactive zoom, hover
 * readout, and a PNG download button, which is half of FR-027 with no code.
 */
import { useEffect, useRef } from 'react'
import Plotly from 'plotly.js-basic-dist-min'
import type { Data, Layout, LayoutAxis } from 'plotly.js'

export interface PlotProps {
  data: Data[]
  layout: Partial<Layout>
  /** Used in the filename when the user saves the plot as an image. */
  filename: string
  height?: number
}

/** Colours read from the stylesheet, so the plots follow the page theme. */
function themeColours() {
  const style = getComputedStyle(document.documentElement)
  const value = (name: string, fallback: string) =>
    style.getPropertyValue(name).trim() || fallback
  return {
    text: value('--text', '#1a1f2b'),
    muted: value('--text-muted', '#626b7d'),
    grid: value('--border', '#d8dde5'),
    accent: value('--accent', '#2557a7'),
    surface: value('--surface', '#ffffff'),
  }
}

export function Plot({ data, layout, filename, height = 320 }: PlotProps) {
  const node = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const element = node.current
    if (!element) return
    const c = themeColours()

    const axis: Partial<LayoutAxis> = {
      gridcolor: c.grid,
      zerolinecolor: c.grid,
      linecolor: c.grid,
      tickfont: { color: c.muted, size: 11 },
      // `titlefont` was the old spelling; current Plotly nests it under title.
      title: { font: { color: c.text, size: 12 } },
      automargin: true,
    }

    void Plotly.react(
      element,
      data,
      {
        height,
        // Generous on the left: the residual axis title is long enough to be
        // clipped at a tighter margin even with automargin on.
        margin: { l: 78, r: 16, t: 10, b: 48 },
        paper_bgcolor: 'rgba(0,0,0,0)',
        plot_bgcolor: 'rgba(0,0,0,0)',
        font: { color: c.text, size: 12 },
        showlegend: true,
        legend: { orientation: 'h', y: 1.14, x: 0, font: { size: 11 } },
        hovermode: 'closest',
        ...layout,
        xaxis: { ...axis, ...layout.xaxis },
        yaxis: { ...axis, ...layout.yaxis },
      },
      {
        displaylogo: false,
        responsive: true,
        // The buttons that do not apply to a static scientific plot only get in
        // the way; the camera icon is the one that matters (FR-027).
        modeBarButtonsToRemove: ['lasso2d', 'select2d', 'toggleSpikelines'],
        toImageButtonOptions: { format: 'png', filename, scale: 3 },
      },
    )
  }, [data, layout, filename, height])

  useEffect(() => {
    const element = node.current
    return () => { if (element) Plotly.purge(element) }
  }, [])

  return <div ref={node} className="plot" />
}
