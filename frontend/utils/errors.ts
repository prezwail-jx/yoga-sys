type ApiError = {
  statusMessage?: string
  data?: {
    statusMessage?: string
    detail?: string
  }
}

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!error) return fallback
  const apiError = error as ApiError
  return apiError.data?.statusMessage || apiError.data?.detail || apiError.statusMessage || fallback
}
