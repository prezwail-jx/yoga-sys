import { ActionGuard, adminService, navigationService, storageService } from "../../../services/index"
import type { MemberInput } from "../../../types/admin"
import { memberView } from "../../../utils/admin-presenter"

const guard = new ActionGuard()
Page({
  data: { mode: "loading", message: "正在加载会员", keyword: "", showCreate: false, members: [] as ReturnType<typeof memberView>[], form: { name: "", phone: "", joinDate: "" } as MemberInput, pending: false, error: "" },
  onLoad() { if (storageService.user()?.role !== "admin") return navigationService.routeForbidden(); void this.load() },
  updateKeyword(e: WechatMiniprogram.Input) { this.setData({ keyword: e.detail.value.trim() }) },
  updateField(e: WechatMiniprogram.Input) { this.setData({ [`form.${String(e.currentTarget.dataset.field)}`]: e.detail.value }) },
  updateDate(e: WechatMiniprogram.PickerChange) { this.setData({ "form.joinDate": String(e.detail.value) }) },
  toggleCreate() { this.setData({ showCreate: !this.data.showCreate, error: "" }) },
  async load() { this.setData({ mode: "loading" }); try { const page = await adminService.members({ keyword: this.data.keyword, limit: 100 }); this.setData({ members: page.items.map(memberView), mode: page.items.length ? "ready" : "empty", message: page.items.length ? "" : "没有符合条件的会员" }) } catch { this.setData({ mode: "error", message: "会员加载失败" }) } },
  async create() {
    const form = this.data.form
    if (!form.name.trim() || !form.phone.trim() || !form.joinDate) return this.setData({ error: "请完整填写姓名、手机号和入会日期" })
    this.setData({ pending: true, error: "" })
    try { await guard.run("create-member", () => adminService.createMember(form)); this.setData({ showCreate: false, form: { name: "", phone: "", joinDate: "" }, pending: false }); await this.load() }
    catch { this.setData({ pending: false, error: "新增会员失败，请检查填写内容" }) }
  },
  open(e: WechatMiniprogram.TouchEvent) { navigationService.open(`/packageAdmin/pages/member-detail/index?id=${encodeURIComponent(String(e.currentTarget.dataset.id))}`) },
})
