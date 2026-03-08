import { NextResponse } from "next/server"
import { mkdir, readFile, writeFile } from "fs/promises"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

export const dynamic = "force-dynamic"

interface SavedPostsFile {
  urls: string[]
}

function getSavedPath() {
  const routeDir = dirname(fileURLToPath(import.meta.url))
  const defaultDataDir = join(routeDir, "..", "..", "..", "..", "..", "..", "data")
  const dataDir = process.env.X_BRIEF_DATA_DIR || defaultDataDir
  return join(dataDir, "saved-posts.json")
}

async function loadSaved(): Promise<SavedPostsFile> {
  const filePath = getSavedPath()
  try {
    const raw = await readFile(filePath, "utf-8")
    const parsed = JSON.parse(raw)
    const urls = Array.isArray(parsed?.urls)
      ? parsed.urls.filter((url: unknown) => typeof url === "string")
      : []
    return { urls }
  } catch {
    return { urls: [] }
  }
}

async function saveSaved(state: SavedPostsFile) {
  const filePath = getSavedPath()
  await mkdir(dirname(filePath), { recursive: true })
  await writeFile(filePath, JSON.stringify(state, null, 2), "utf-8")
}

export async function GET() {
  const state = await loadSaved()
  return NextResponse.json(state)
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const incoming = Array.isArray(body?.urls)
      ? body.urls.filter((url: unknown) => typeof url === "string")
      : []

    if (incoming.length === 0) {
      return NextResponse.json({ error: "Expected urls: string[]" }, { status: 400 })
    }

    const current = await loadSaved()
    const merged = new Set(current.urls)
    for (const url of incoming) merged.add(url)

    const next: SavedPostsFile = { urls: Array.from(merged) }
    await saveSaved(next)
    return NextResponse.json(next)
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 })
  }
}
