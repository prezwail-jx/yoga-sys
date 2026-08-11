import { ApiError, memberService, navigationService, storageService } from "../../../services/index"
import type { MemberCardView } from "../../../types/member"
import { memberCardView } from "../../../utils/member-presenter"

Page({
  data: {
    cards: [] as MemberCardView[],
    mode: "loading",
    message: "正在读取卡项",
  },
  onLoad() {
    if (storageService.user()?.role !== "member") {
      navigationService.routeForbidden()
      return
    }
    void this.load()
  },
  async load() {
    this.setData({ mode: "loading", message: "正在读取卡项" })
    try {
      const cards = (await memberService.cards()).map(memberCardView)
      this.setData({ cards, mode: cards.length ? "ready" : "empty", message: cards.length ? "" : "当前没有会员卡" })
    } catch (error) {
      this.setData({ mode: "error", message: error instanceof ApiError ? error.message : "卡项加载失败" })
    }
  },
})
