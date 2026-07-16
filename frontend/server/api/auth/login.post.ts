export default defineEventHandler(async (event) => {
  const body = await readBody<{ username: string; password: string }>(event)
  const result = await backendRequest<{ access_token: string; role: "admin" | "coach" | "member" }>(
    event,
    "/auth/login",
    { method: "POST", body, auth: false },
  )
  setCookie(event, "yoga_token", result.access_token, {
    httpOnly: true,
    sameSite: "lax",
    secure: process.env.NODE_ENV === "production",
    path: "/",
    maxAge: 60 * 60 * 24,
  })
  return { username: body.username, role: result.role }
})
