export default defineNuxtRouteMiddleware(async () => {
  const { user, loadUser } = useAuth()
  try {
    if (!user.value) await loadUser()
  } catch {
    return navigateTo("/login")
  }
})
