/**
 * Typed wrappers around the API.
 *
 * Every type here is re-exported from `generated.ts`, which is produced from
 * the running backend by `npm run gen:api`. Nothing in this file describes the
 * shape of a request or a response by hand. That is the point: when the backend
 * changes a field, this project finds out at build time rather than as a blank
 * screen.
 */
import type { components } from './generated'

type S = components['schemas']

export type Dataset = S['Dataset']
export type Settings = S['Settings']
export type UncertaintySettings = S['UncertaintySettingsIn']
export type ParseResponse = S['ParseResponse']
export type LambdaResponse = S['LambdaResponse']
export type AnalyzeResponse = S['AnalyzeResponse']
export type FitResult = S['FitResultOut']
export type FittedParameter = S['FittedParameter']
export type DiagnosticReport = S['DiagnosticReportOut']
export type UncertaintyResult = S['UncertaintyResultOut']
export type ParameterDistribution = S['ParameterDistribution']
export type SuperfluidCurve = S['SuperfluidCurveOut']
export type ExampleSummary = S['ExampleSummary']
export type Example = S['Example']
export type JobStatus = S['JobStatus']
export type WarningOut = S['WarningOut']
export type ErrorPayload = S['ErrorPayload']

export type CoherenceSource = S['CoherenceSource']
export type GapModel = S['GapModel']
export type FitRoute = S['FitRoute']
export type CorrelationMode = S['CorrelationMode']
export type JcUnit = S['JcUnit']
export type XiUnit = S['XiUnit']

/**
 * A failure the backend reported as a code.
 *
 * The backend never sends a sentence meant for a person, so the code and its
 * parameters are all there is; turning them into Korean is `errorMessages.ts`.
 */
export class ApiError extends Error {
  readonly code: string
  readonly params: Record<string, unknown>
  readonly status: number

  constructor(payload: ErrorPayload, status: number) {
    super(`${payload.code} ${JSON.stringify(payload.params)}`)
    this.name = 'ApiError'
    this.code = payload.code
    this.params = (payload.params ?? {}) as Record<string, unknown>
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch {
    // The server is not answering at all: a different problem from a rejected
    // request, and it needs a different sentence.
    throw new ApiError({ code: 'NETWORK_UNREACHABLE', params: {} }, 0)
  }

  if (!response.ok) {
    let payload: ErrorPayload
    try {
      const body = await response.json()
      payload = typeof body?.code === 'string'
        ? (body as ErrorPayload)
        // FastAPI's own validation failures have a different shape. They mean
        // the request was malformed rather than the data unusable, which is a
        // bug in this frontend, so they are labelled as such.
        : { code: 'REQUEST_REJECTED', params: { detail: JSON.stringify(body?.detail ?? body) } }
    } catch {
      payload = { code: 'REQUEST_REJECTED', params: { detail: String(response.status) } }
    }
    throw new ApiError(payload, response.status)
  }

  return response.json() as Promise<T>
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

export interface AnalyzeRequest {
  dataset: Dataset
  settings: Settings
}

export const api = {
  health: () => request<{ status: string; version: string }>('/api/health'),

  parse: (text: string) => post<ParseResponse>('/api/parse', { text }),

  examples: () => request<ExampleSummary[]>('/api/examples'),

  example: (name: string) => request<Example>(`/api/examples/${encodeURIComponent(name)}`),

  lambdaTable: (body: AnalyzeRequest) => post<LambdaResponse>('/api/lambda', body),

  analyze: (body: AnalyzeRequest) => post<AnalyzeResponse>('/api/analyze', body),

  startUncertainty: (body: AnalyzeRequest & { uncertainty: UncertaintySettings }) =>
    post<{ job_id: string }>('/api/uncertainty', body),

  job: (jobId: string) => request<JobStatus>(`/api/jobs/${encodeURIComponent(jobId)}`),

  /** The per-measurement table: one row per measured temperature (FR-027). */
  downloadCsv: (result: AnalyzeResponse) =>
    download('/api/export/csv', result, 'nodeless_sc_result.csv'),

  /** The fitted curve as numbers, for replotting elsewhere (FR-027a). */
  downloadCurveCsv: (result: AnalyzeResponse) =>
    download('/api/export/curve.csv', result, 'nodeless_sc_curve.csv'),
}

/** Fetches a CSV and hands it to the browser as a download. */
async function download(path: string, result: AnalyzeResponse, filename: string) {
  const response = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(result),
  })
  if (!response.ok) {
    throw new ApiError({ code: 'REQUEST_REJECTED', params: {} }, response.status)
  }
  const blob = await response.blob()
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}
