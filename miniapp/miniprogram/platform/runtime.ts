export interface RequestSuccess<T> {
  data: T
  statusCode: number
  header: Record<string, string>
}

export interface RequestFailure {
  errMsg: string
  errno?: number
}

export interface RequestOptions<T> {
  url: string
  method: "GET" | "POST" | "PATCH" | "PUT" | "DELETE"
  data?: unknown
  header: Record<string, string>
  timeout: number
  success: (response: RequestSuccess<T>) => void
  fail: (error: RequestFailure) => void
}

export interface LoginOptions {
  success: (result: { code: string }) => void
  fail: (error: { errMsg: string }) => void
}

export interface DownloadFileOptions {
  url: string
  header: Record<string, string>
  timeout: number
  success: (result: { tempFilePath: string; statusCode: number }) => void
  fail: (error: RequestFailure) => void
}

export interface OpenDocumentOptions {
  filePath: string
  fileType?: string
  showMenu?: boolean
  success: () => void
  fail: (error: RequestFailure) => void
}

export interface SafeLogManager {
  info(message: string, metadata?: Record<string, unknown>): void
  warn(message: string, metadata?: Record<string, unknown>): void
  error(message: string, metadata?: Record<string, unknown>): void
}

export interface MiniProgramRuntime {
  request<T>(options: RequestOptions<T>): unknown
  login(options: LoginOptions): void
  downloadFile(options: DownloadFileOptions): unknown
  openDocument(options: OpenDocumentOptions): void
  getStorageSync(key: string): unknown
  setStorageSync(key: string, value: unknown): void
  removeStorageSync(key: string): void
  reLaunch(options: { url: string }): void
  navigateTo(options: { url: string }): void
  getAccountInfoSync?(): { miniProgram: { envVersion: "develop" | "trial" | "release" } }
  getLogManager?(options?: { level?: number }): SafeLogManager
}

export const runtime = wx as unknown as MiniProgramRuntime
