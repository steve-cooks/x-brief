import { exec } from "child_process"
import { readFile } from "fs/promises"
import path from "path"
import { promisify } from "util"

import { NextResponse } from "next/server"

const execAsync = promisify(exec)

export const dynamic = "force-dynamic"

const COOLDOWN_MINUTES = 15

export async function POST() {
  try {
    // Check cooldown
    try {
      const statusPath = path.resolve(process.cwd(), "..", "data/pipeline-status.json")
      const raw = await readFile(statusPath, "utf-8")
      const status = JSON.parse(raw)
      if (status.last_success) {
        const lastSuccess = new Date(status.last_success).getTime()
        const minutesSince = Math.floor((Date.now() - lastSuccess) / 60000)
        if (minutesSince < COOLDOWN_MINUTES) {
          const retryAfter = COOLDOWN_MINUTES - minutesSince
          return NextResponse.json(
            {
              error: `Too soon. Last scan was ${minutesSince} minutes ago. Try again later.`,
              retryAfterMinutes: retryAfter,
            },
            { status: 429 }
          )
        }
      }
    } catch {
      // File missing or unreadable — proceed with scan
    }

    const scanCommand = process.env.XBRIEF_SCAN_COMMAND
    if (!scanCommand) {
      return NextResponse.json(
        { error: "XBRIEF_SCAN_COMMAND is not configured." },
        { status: 500 }
      )
    }

    const { stdout } = await execAsync(scanCommand)

    return NextResponse.json({
      ok: true,
      enqueued: true,
      jobId: process.env.XBRIEF_CRON_JOB_ID || "not-configured",
      output: stdout,
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
