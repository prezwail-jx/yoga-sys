import { sessionService } from "../../services/index"

Page({
  restart() {
    sessionService.logout()
  },
})
