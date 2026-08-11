import { navigationService, storageService } from "../../services/index"

Page({
  data: {
    destination: "",
  },
  onLoad(query: Record<string, string | undefined>) {
    const user = storageService.user()
    if (user?.role !== "coach") {
      navigationService.routeForbidden()
      return
    }
    this.setData({ destination: query.destination ?? "coach-home" })
  },
})
