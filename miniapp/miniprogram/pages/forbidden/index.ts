import { sessionService } from "../../services"

Page({
  restart() {
    sessionService.logout()
  },
})
