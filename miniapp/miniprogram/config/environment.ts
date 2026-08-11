import type { MiniProgramRuntime } from "../platform/runtime"

export type EnvironmentVersion = "develop" | "trial" | "release"

const API_BASE_URLS: Record<EnvironmentVersion, string> = {
  develop: "http://127.0.0.1:8000",
  trial: "https://yoga.tuitukj.com/backend",
  release: "https://yoga.tuitukj.com/backend",
}

export function environmentVersion(runtime: MiniProgramRuntime): EnvironmentVersion {
  try {
    return runtime.getAccountInfoSync?.().miniProgram.envVersion ?? "develop"
  } catch {
    return "develop"
  }
}

export function apiBaseUrl(runtime: MiniProgramRuntime): string {
  return API_BASE_URLS[environmentVersion(runtime)]
}

export function passwordLoginEnabled(runtime: MiniProgramRuntime): boolean {
  return environmentVersion(runtime) !== "release"
}
