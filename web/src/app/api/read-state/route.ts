import { NextResponse } from "next/server"
import { mkdir, readFile, writeFile } from "fs/promises"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

export const dynamic = "force-dynamic"

interface ReadStateFile {
  ids: string[]
}

function getReadStatePath() {
  const routeDir = dirname(fileURLToPath(import.meta.url))
  const defaultDataDir = join(routeDir, "..", "..", "..", "..", "..", "..", "data")
  const dataDir = process.env.X_BRIEF_DATA_DIR || defaultDataDir
  return join(dataDir, "read-state.json")
}

async function loadReadState(): Promise<ReadStateFile> {
  const filePath = getReadStatePath()
  try {
    const raw = await readFile(filePath, "utf-8")
    const parsed = JSON.parse(raw)
    const ids = Array.isArray(parsed?.ids) ? parsed.ids.filter((id: unknown) => typeof id === "string") : []
    return { ids }
  } catch {
    return { ids: [] }
  }
}

async function saveReadState(state: ReadStateFile) {
  const filePath = getReadStatePath()
  await mkdir(dirname(filePath), { recursive: true })
  await writeFile(filePath, JSON.stringify(state, null, 2), "utf-8")
}

export async function GET() {
  const state = await loadReadState()
  return NextResponse.json(state)
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const incoming = Array.isArray(body?.ids)
      ? body.ids.filter((id: unknown) => typeof id === "string")
      : []

    if (incoming.length === 0) {
      return NextResponse.json({ error: "Expected ids: string[]" }, { status: 400 })
    }

    const current = await loadReadState()
    const merged = new Set(current.ids)
    for (const id of incoming) merged.add(id)

    const next: ReadStateFile = { ids: Array.from(merged) }
    await saveReadState(next)
    return NextResponse.json(next)
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 })
  }
}
