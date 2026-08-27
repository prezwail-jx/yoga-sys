import type {
  LoginOptions,
  DownloadFileOptions,
  OpenDocumentOptions,
  MiniProgramRuntime,
  RequestOptions,
  SafeLogManager,
} from "../../miniprogram/platform/runtime"

export class FakeRuntime implements MiniProgramRuntime {
  readonly storage = new Map<string, unknown>()
  readonly requests: RequestOptions<unknown>[] = []
  readonly relaunches: string[] = []
  readonly navigations: string[] = []
  readonly logs: Array<{ level: string; message: string; metadata?: Record<string, unknown> }> = []
  readonly downloads: DownloadFileOptions[] = []
  readonly openedDocuments: OpenDocumentOptions[] = []
  loginCode = "wx-code"
  loginCalls = 0
  envVersion: "develop" | "trial" | "release" = "develop"
  requestHandler: (options: RequestOptions<unknown>) => void = (options) => {
    options.success({ data: {}, statusCode: 200, header: {} })
  }
  downloadHandler: (options: DownloadFileOptions) => void = (options) => options.success({ tempFilePath: "/tmp/report.xlsx", statusCode: 200 })
  openDocumentHandler: (options: OpenDocumentOptions) => void = (options) => options.success()

  request<T>(options: RequestOptions<T>): unknown {
    const genericOptions = options as unknown as RequestOptions<unknown>
    this.requests.push(genericOptions)
    this.requestHandler(genericOptions)
    return {}
  }

  login(options: LoginOptions): void {
    this.loginCalls += 1
    options.success({ code: this.loginCode })
  }

  downloadFile(options: DownloadFileOptions): unknown {
    this.downloads.push(options)
    this.downloadHandler(options)
    return {}
  }

  openDocument(options: OpenDocumentOptions): void {
    this.openedDocuments.push(options)
    this.openDocumentHandler(options)
  }

  getStorageSync(key: string): unknown {
    return this.storage.get(key) ?? ""
  }

  setStorageSync(key: string, value: unknown): void {
    this.storage.set(key, value)
  }

  removeStorageSync(key: string): void {
    this.storage.delete(key)
  }

  reLaunch(options: { url: string }): void {
    this.relaunches.push(options.url)
  }

  navigateTo(options: { url: string }): void {
    this.navigations.push(options.url)
  }

  getAccountInfoSync(): { miniProgram: { envVersion: "develop" | "trial" | "release" } } {
    return { miniProgram: { envVersion: this.envVersion } }
  }

  getLogManager(): SafeLogManager {
    return {
      info: (message, metadata) => this.logs.push({ level: "info", message, metadata }),
      warn: (message, metadata) => this.logs.push({ level: "warn", message, metadata }),
      error: (message, metadata) => this.logs.push({ level: "error", message, metadata }),
    }
  }
}
