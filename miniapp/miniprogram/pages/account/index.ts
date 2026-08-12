import { navigationService, sessionService, storageService } from "../../services/index"

Page({
  data: {
    username: "",
    roleLabel: "",
  },
  onLoad() {
    const user = storageService.user()
    if (!user) {
      navigationService.routeStartup()
      return
    }
    this.setData({
      username: user.username,
      roleLabel: user.role === "member" ? "会员" : "教练",
    })
  },
  logout() {
    sessionService.logout()
  },
  security() {
    wx.navigateTo({ url: "/pages/account/security/index" })
  },
})
