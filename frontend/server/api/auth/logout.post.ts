export default defineEventHandler((event) => {
  deleteCookie(event, "yoga_token", { path: "/" })
  return { ok: true }
})
