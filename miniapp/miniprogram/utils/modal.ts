export function confirmAction(title: string, content: string): Promise<boolean> {
  return new Promise((resolve) => {
    wx.showModal({
      title,
      content,
      confirmColor: "#173f35",
      success: (result) => resolve(result.confirm),
      fail: () => resolve(false),
    })
  })
}

export function promptAction(title: string, placeholder: string): Promise<string | null> {
  return new Promise((resolve) => {
    wx.showModal({
      title,
      editable: true,
      placeholderText: placeholder,
      confirmColor: "#173f35",
      success: (result) => resolve(result.confirm ? (result.content ?? "").trim() : null),
      fail: () => resolve(null),
    })
  })
}
