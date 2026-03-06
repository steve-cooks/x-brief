import { NextResponse } from "next/server"
import { readFile } from "fs/promises"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

export const dynamic = "force-dynamic"

export async function GET() {
  const routeDir = dirname(fileURLToPath(import.meta.url))
  const defaultDataDir = join(routeDir, "..", "..", "..", "..", "..", "..", "data")
  const dataDir = process.env.X_BRIEF_DATA_DIR || defaultDataDir
  const briefingPaths = [
    join(dataDir, "latest-briefing.json"),
    join(process.cwd(), "..", "data", "latest-briefing.json"),
  ]

  for (const briefingPath of briefingPaths) {
    try {
      const data = await readFile(briefingPath, "utf-8")
      return NextResponse.json(JSON.parse(data))
    } catch {
      // Try next fallback path.
    }
  }

  return NextResponse.json(
    { error: "No briefing available. Run the pipeline first.", sections: [], stats: {} },
    { status: 404 }
  )
}
