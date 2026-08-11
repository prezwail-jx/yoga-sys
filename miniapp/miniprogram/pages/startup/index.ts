import { sessionService } from "../../services/index"

Page({
  data: {
    mode: "loading",
    message: "正在恢复你的工作台",
  },
  onLoad() {
    void this.start()
  },
  async start() {
    this.setData({ mode: "loading", message: "正在恢复你的工作台" })
    try {
      await sessionService.bootstrapAndRoute()
    } catch {
      this.setData({ mode: "error", message: "暂时无法连接，请检查网络后重试" })
    }
  },
})
