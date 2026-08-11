import { navigationForRole, navigationService, storageService } from "../../services"

Page({
  data: {
    username: "",
    roleLabel: "",
    items: [] as ReturnType<typeof navigationForRole>,
  },
  onShow() {
    const user = storageService.user()
    if (!user) {
      navigationService.routeStartup()
      return
    }
    this.setData({
      username: user.username,
      roleLabel: user.role === "member" ? "会员空间" : "教练空间",
      items: navigationForRole(user.role),
    })
  },
  open(event: WechatMiniprogram.CustomEvent<{ path: string }>) {
    const path = event.currentTarget.dataset.path as string
    navigationService.open(path)
  },
  account() {
    navigationService.open("/pages/account/index")
  },
})
