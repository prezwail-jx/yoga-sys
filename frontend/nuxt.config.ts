export default defineNuxtConfig({
  app: {
    head: {
      title: "Yoga SYS",
      htmlAttrs: { lang: "zh-CN" },
    },
  },
  modules: ["@nuxt/ui", "@nuxt/eslint"],
  css: ["~/assets/css/main.css", "~/assets/css/admin.css"],
  devtools: { enabled: true },
  ui: {
    fonts: false,
  },
  runtimeConfig: {
    backendBaseUrl: process.env.NUXT_BACKEND_BASE_URL || "http://127.0.0.1:8000",
  },
  typescript: {
    strict: true,
  },
})
