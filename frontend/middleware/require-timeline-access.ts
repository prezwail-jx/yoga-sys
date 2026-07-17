export default defineNuxtRouteMiddleware(async (to) => {
  const { user, loadUser } = useAuth()
  try {
    if (!user.value) await loadUser()
  } catch {
    return navigateTo("/login")
  }
  if (user.value?.role === "admin") return
  if (user.value?.role === "member" && user.value.memberId === String(to.params.memberId)) return
  return navigateTo("/forbidden")
})
