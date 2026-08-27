import { ActionGuard, adminService, navigationService, storageService } from "../../../services/index"
import type { CardProduct, ManagedMemberCard, Member, MemberUpdateInput, TimelineEvent } from "../../../types/admin"
import { cardTypeLabels, memberCardStatusLabels, memberStatusLabels } from "../../../utils/admin-presenter"
import { confirmAction, promptAction } from "../../../utils/modal"

type CardView = ManagedMemberCard & { statusLabel: string; typeLabel: string; balanceLabel: string }
type MemberView = Member & { statusLabel: string }
const guard = new ActionGuard()
Page({
  data: { id: "", mode: "loading", message: "正在加载会员详情", member: null as MemberView | null, showProfileForm: false, profileForm: { name: "", gender: null, birthday: null, note: "", emergencyContact: "" } as MemberUpdateInput, genderIndex: 0, genderNames: ["未设置", "男", "女", "其他", "未知"], genderValues: [null, "male", "female", "other", "unknown"] as Array<string | null>, cards: [] as CardView[], timeline: [] as TimelineEvent[], products: [] as CardProduct[], productNames: [] as string[], productIndex: 0, pendingId: "", error: "" },
  onLoad(query: Record<string, string | undefined>) { if (storageService.user()?.role !== "admin") return navigationService.routeForbidden(); this.setData({ id: query.id ?? "" }); void this.load() },
  async load() {
    try {
      const [member, cards, products, timeline] = await Promise.all([adminService.member(this.data.id), adminService.memberCards(this.data.id), adminService.products(true), adminService.memberTimeline(this.data.id)])
      const genderIndex = Math.max(0, this.data.genderValues.indexOf(member.gender))
      this.setData({ member: { ...member, statusLabel: memberStatusLabels[member.status] }, profileForm: { name: member.name, gender: member.gender, birthday: member.birthday, note: member.note ?? "", emergencyContact: member.emergencyContact ?? "" }, genderIndex, cards: cards.items.map(card => ({ ...card, statusLabel: memberCardStatusLabels[card.status], typeLabel: cardTypeLabels[card.cardType], balanceLabel: card.remainingTimes === null ? "不限次数" : `剩余 ${card.remainingTimes} 次` })), timeline: timeline.items, products: products.items, productNames: products.items.map(item => `${item.name} · ¥${item.price}`), mode: "ready", message: "", error: "" })
    } catch { this.setData({ mode: "error", message: "会员详情加载失败" }) }
  },
  chooseProduct(e: WechatMiniprogram.PickerChange) { this.setData({ productIndex: Number(e.detail.value) }) },
  toggleProfileForm() { this.setData({ showProfileForm: !this.data.showProfileForm, error: "" }) },
  profileField(e: WechatMiniprogram.Input) { this.setData({ [`profileForm.${String(e.currentTarget.dataset.field)}`]: e.detail.value }) },
  profileGender(e: WechatMiniprogram.PickerChange) { const genderIndex = Number(e.detail.value); this.setData({ genderIndex, "profileForm.gender": this.data.genderValues[genderIndex] }) },
  profileBirthday(e: WechatMiniprogram.PickerChange) { this.setData({ "profileForm.birthday": String(e.detail.value) }) },
  clearBirthday() { this.setData({ "profileForm.birthday": null }) },
  async saveProfile() {
    const form = this.data.profileForm
    if (!form.name?.trim()) return this.setData({ error: "会员姓名不能为空" })
    const input: MemberUpdateInput = { name: form.name.trim(), gender: form.gender ?? null, birthday: form.birthday || null, note: form.note?.trim() || null, emergencyContact: form.emergencyContact?.trim() || null }
    await this.run("profile", () => adminService.updateMember(this.data.id, input))
    this.setData({ showProfileForm: false })
  },
  async purchase() {
    const product = this.data.products[this.data.productIndex]
    if (!product || this.data.pendingId) return
    if (!await confirmAction("确认购卡", `为 ${this.data.member?.name ?? "该会员"} 办理“${product.name}”，金额 ¥${product.price}？`)) return
    await this.run("purchase", () => adminService.transaction({ txnType: "purchase", memberId: this.data.id, cardProductId: product.id }))
  },
  async setStatus(e: WechatMiniprogram.TouchEvent) {
    const status = String(e.currentTarget.dataset.status) as Member["status"]
    if (!await confirmAction("确认修改状态", `将会员状态改为“${memberStatusLabels[status]}”？`)) return
    await this.run(`status:${status}`, () => adminService.updateMember(this.data.id, { status }))
  },
  async resetPassword() { const password = await promptAction("重置会员密码", "至少 8 位"); if (!password || password.length < 8) return this.setData({ error: "新密码至少 8 位" }); if (!await confirmAction("确认重置密码", "旧密码将立即失效。")) return; await this.run("reset-password", () => adminService.resetPassword("members", this.data.id, password)) },
  async cardAction(e: WechatMiniprogram.TouchEvent) {
    const id = String(e.currentTarget.dataset.id); const action = String(e.currentTarget.dataset.action)
    const card = this.data.cards.find(item => item.id === id); if (!card || this.data.pendingId) return
    if (action === "renew" || action === "reissue" || action === "refund") {
      const titles = { renew: "续费", reissue: "补卡", refund: "退款" } as const
      if (!await confirmAction(`确认${titles[action]}`, `对“${card.productName}”执行${titles[action]}？`)) return
      const input = action === "refund" ? { txnType: action as "refund", memberId: this.data.id, memberCardId: id, originTransactionId: card.refundableTransactionId ?? undefined } : { txnType: action as "renew" | "reissue", memberId: this.data.id, memberCardId: id }
      if (action === "refund" && !card.refundableTransactionId) return this.setData({ error: "当前卡没有可退款的原交易" })
      await this.run(`${action}:${id}`, () => adminService.transaction(input)); return
    }
    if (action === "extend") {
      const value = await promptAction("延期天数", "请输入正整数天数"); const days = Number(value)
      if (!Number.isInteger(days) || days <= 0) return this.setData({ error: "延期天数必须为正整数" })
      if (!await confirmAction("确认延期", `为“${card.productName}”延期 ${days} 天？`)) return
      await this.run(`extend:${id}`, () => adminService.transaction({ txnType: "extend", memberId: this.data.id, memberCardId: id, validDaysDelta: days })); return
    }
    if (action === "freeze") {
      const until = await promptAction("冻结截止日期", "请输入 YYYY-MM-DD"); if (!until) return
      const reason = await promptAction("冻结原因", "必填"); if (!reason) return this.setData({ error: "冻结原因不能为空" })
      if (!await confirmAction("确认冻结", `冻结至 ${until}，原因：${reason}`)) return
      await this.run(`freeze:${id}`, () => adminService.freeze(id, until, reason)); return
    }
    if (action === "unfreeze") {
      const reason = await promptAction("解冻说明", "可选"); if (reason === null) return
      if (!await confirmAction("确认解冻", `立即解冻“${card.productName}”？`)) return
      await this.run(`unfreeze:${id}`, () => adminService.unfreeze(id, reason)); return
    }
    if (action === "adjust") {
      const value = await promptAction("调整次数", "正数增加，负数扣减"); const delta = Number(value)
      if (!Number.isInteger(delta) || delta === 0) return this.setData({ error: "调整次数必须为非零整数" })
      const reason = await promptAction("调整原因", "必填，将写入审计记录"); if (!reason) return this.setData({ error: "调整原因不能为空" })
      if (!await confirmAction("再次确认次数调整", `${card.productName}：${delta > 0 ? "+" : ""}${delta} 次\n原因：${reason}`)) return
      await this.run(`adjust:${id}`, () => adminService.adjustTimes(id, delta, reason))
    }
  },
  async createAccount() {
    const username = await promptAction("开通会员账号", "请输入用户名"); if (!username) return
    const password = await promptAction("初始密码", "至少 8 位"); if (!password || password.length < 8) return this.setData({ error: "初始密码至少 8 位" })
    if (!await confirmAction("确认开通", `为 ${this.data.member?.name ?? "会员"} 开通账号 ${username}？`)) return
    await this.run("account", () => adminService.createAccount("members", this.data.id, username, password))
  },
  async run(action: string, task: () => Promise<unknown>) { this.setData({ pendingId: action, error: "" }); try { await guard.run(action, task); wx.showToast({ title: "操作成功", icon: "success" }); await this.load() } catch { this.setData({ error: "操作失败，请核对当前状态和填写内容" }) } finally { this.setData({ pendingId: "" }) } },
})
