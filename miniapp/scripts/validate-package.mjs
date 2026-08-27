import { access, readFile } from "node:fs/promises"
import { dirname, join } from "node:path"
import { stdout } from "node:process"
import { fileURLToPath } from "node:url"

const workspace = dirname(dirname(fileURLToPath(import.meta.url)))
const project = JSON.parse(await readFile(join(workspace, "project.config.json"), "utf8"))
const root = join(workspace, project.miniprogramRoot ?? "miniprogram")
const app = JSON.parse(await readFile(join(root, "app.json"), "utf8"))

if (project.compileType !== "miniprogram") throw new Error("compileType must be miniprogram")
if (!project.setting?.useCompilerPlugins?.includes("typescript")) {
  throw new Error("WeChat TypeScript compiler plugin must be enabled")
}
if (project.setting?.minified !== true) throw new Error("release minification must be enabled")
if (!Array.isArray(app.pages) || app.pages.length === 0) throw new Error("app.json must register pages")

const entries = new Set(app.pages)
for (const subpackage of app.subpackages ?? []) {
  if (!subpackage.root || !Array.isArray(subpackage.pages)) throw new Error("subpackage root and pages are required")
  for (const page of subpackage.pages) entries.add(`${subpackage.root}/${page}`)
}
for (const page of entries) {
  const pageConfig = JSON.parse(await readFile(join(root, `${page}.json`), "utf8"))
  for (const component of Object.values(pageConfig.usingComponents ?? {})) {
    if (typeof component === "string" && component.startsWith("/")) {
      entries.add(component.slice(1))
    }
  }
}

for (const entry of entries) {
  for (const extension of ["ts", "json", "wxml", "wxss"]) {
    await access(join(root, `${entry}.${extension}`))
  }
}
for (const file of ["app.ts", "app.json", "app.wxss", app.sitemapLocation]) {
  await access(join(root, file))
}

stdout.write(`Validated ${entries.size} pages and local components\n`)
