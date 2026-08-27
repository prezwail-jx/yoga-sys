import { ActionGuard, adminService, navigationService, storageService } from "../../../services/index"
import type { CardProductInput } from "../../../types/admin"
import { productView } from "../../../utils/admin-presenter"
import { confirmAction, promptAction } from "../../../utils/modal"

const guard = new ActionGuard()
const emptyForm = (): CardProductInput => ({ name: "", cardType: "times", price: 0, totalTimes: null, validDays: null, activationMode: "immediate", applicableCourseScope: "group", absenceDeductEnabled: false, cancelRefundEnabled: false })
Page({
  data: { mode: "loading", message: "正在加载卡产品", products: [] as ReturnType<typeof productView>[], showForm: false, form: emptyForm(), typeNames: ["次数卡", "期限卡", "私教卡", "体验卡"], typeValues: ["times", "duration", "private", "trial"], activationNames: ["购卡即开", "首次约课开卡"], typeIndex: 0, pending: false, error: "" },
  onLoad() { if (storageService.user()?.role !== "admin") return navigationService.routeForbidden(); void this.load() },
  async load() { try { const page = await adminService.products(); this.setData({ products: page.items.map(productView), mode: page.items.length ? "ready" : "empty", message: page.items.length ? "" : "暂无卡产品" }) } catch { this.setData({ mode: "error", message: "卡产品加载失败" }) } },
  toggleForm() { this.setData({ showForm: !this.data.showForm, error: "" }) },
  field(e: WechatMiniprogram.Input) { const field = String(e.currentTarget.dataset.field); const numeric = ["price", "totalTimes", "validDays"].includes(field); this.setData({ [`form.${field}`]: numeric ? (e.detail.value === "" ? null : Number(e.detail.value)) : e.detail.value }) },
  chooseType(e: WechatMiniprogram.PickerChange) { const typeIndex = Number(e.detail.value); this.setData({ typeIndex, "form.cardType": this.data.typeValues[typeIndex] }) },
  chooseActivation(e: WechatMiniprogram.PickerChange) { this.setData({ "form.activationMode": Number(e.detail.value) === 0 ? "immediate" : "first_booking" }) },
  async create() {
    const form = this.data.form
    if (!form.name.trim() || form.price === null || form.price < 0) return this.setData({ error: "请填写名称和正确价格" })
    if ((form.cardType === "times" || form.cardType === "private") && (!form.totalTimes || form.totalTimes < 1)) return this.setData({ error: "次数卡和私教卡必须填写总次数" })
    if ((form.cardType === "times" || form.cardType === "duration") && (!form.validDays || form.validDays < 1)) return this.setData({ error: "次数卡和期限卡必须填写有效期天数" })
    this.setData({ pending: true, error: "" }); try { await guard.run("create-product", () => adminService.createProduct(form)); this.setData({ form: emptyForm(), showForm: false, pending: false }); await this.load() } catch { this.setData({ pending: false, error: "创建失败，请检查卡产品规则" }) }
  },
  async rename(e: WechatMiniprogram.TouchEvent) { const id = String(e.currentTarget.dataset.id); const name = await promptAction("修改产品名称", "请输入新名称"); if (!name) return; await this.run(`rename:${id}`, () => adminService.updateProduct(id, { name })) },
  async editRules(e: WechatMiniprogram.TouchEvent) { const id = String(e.currentTarget.dataset.id); const product = this.data.products.find(item => item.id === id); if (!product) return; const price = Number(await promptAction("修改售价", `当前 ¥${product.price}`)); if (!Number.isFinite(price) || price < 0) return this.setData({ error: "售价必须为非负数字" }); let totalTimes = product.totalTimes; if (product.cardType === "times" || product.cardType === "private") { totalTimes = Number(await promptAction("修改总次数", `当前 ${product.totalTimes ?? "未设置"}`)); if (!Number.isInteger(totalTimes) || totalTimes < 1) return this.setData({ error: "总次数必须为正整数" }) } let validDays = product.validDays; if (product.cardType === "times" || product.cardType === "duration") { validDays = Number(await promptAction("修改有效期天数", `当前 ${product.validDays ?? "未设置"}`)); if (!Number.isInteger(validDays) || validDays < 1) return this.setData({ error: "次数卡和期限卡必须设置有效期天数" }) } if (!await confirmAction("确认修改产品规则", "修改仅影响后续新发会员卡，不批量改写历史卡。")) return; await this.run(`rules:${id}`, () => adminService.updateProduct(id, { price, totalTimes, validDays })) },
  async toggle(e: WechatMiniprogram.TouchEvent) { const id = String(e.currentTarget.dataset.id); const enabled = e.currentTarget.dataset.enabled !== true; if (!await confirmAction(enabled ? "确认启用" : "确认停用", enabled ? "启用后可用于新购卡。" : "停用后不再用于新购卡，已发出的卡不受影响。")) return; await this.run(`toggle:${id}`, () => adminService.updateProduct(id, { enabled })) },
  async run(id: string, task: () => Promise<unknown>) { try { await guard.run(id, task); wx.showToast({ title: "操作成功", icon: "success" }); await this.load() } catch { this.setData({ error: "操作失败" }) } },
})
