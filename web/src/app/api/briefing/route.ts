import { NextResponse } from "next/server"
import { readFile } from "fs/promises"
import { join } from "path"

export const dynamic = "force-dynamic"

export async function GET() {
  try {
    // Read from the pipeline-generated JSON
    const briefingPath = join(process.cwd(), "..", "data", "latest-briefing.json")
    const data = await readFile(briefingPath, "utf-8")
    return NextResponse.json(JSON.parse(data))
  } catch (err) {
    // Fallback: try alternative path
    try {
      const altPath = "/home/cluvis/projects/x-brief/data/latest-briefing.json"
      const data = await readFile(altPath, "utf-8")
      return NextResponse.json(JSON.parse(data))
    } catch {
      return NextResponse.json(
        { error: "No briefing available. Run the pipeline first.", sections: [], stats: {} },
        { status: 404 }
      )
    }
  }
}
