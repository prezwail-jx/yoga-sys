Component({
  properties: {
    mode: { type: String, value: "loading" },
    message: { type: String, value: "正在加载" },
    retryLabel: { type: String, value: "重试" },
  },
  methods: {
    retry() {
      this.triggerEvent("retry")
    },
  },
})
