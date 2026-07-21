import type { CurrentUser } from "~/types/domain"

export function useAuth() {
  const user = useState<CurrentUser | null>("current-user", () => null)

  async function loadUser() {
    user.value = await $fetch<CurrentUser>("/api/auth/me", {
      headers: import.meta.server ? useRequestHeaders(["cookie"]) : undefined,
    })
    return user.value
  }

  async function login(username: string, password: string) {
    await $fetch("/api/auth/login", {
      method: "POST",
      body: { username, password },
    })
    return loadUser()
  }

  async function logout() {
    await $fetch("/api/auth/logout", { method: "POST" })
    user.value = null
    await navigateTo("/login")
  }

  return { user, loadUser, login, logout }
}
