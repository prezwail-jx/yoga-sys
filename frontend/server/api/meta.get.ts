export default defineEventHandler(() => {
  return {
    appName: "瑜伽馆会员约课管理系统",
    roles: ["超级管理员", "教练", "会员"],
    today: new Date().toISOString().slice(0, 10),
  }
})
