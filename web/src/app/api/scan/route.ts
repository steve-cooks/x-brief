import { exec } from "child_process"
import { promisify } from "util"

import { NextResponse } from "next/server"

const execAsync = promisify(exec)

export const dynamic = "force-dynamic"

const OPENCLAW_CRON_JOB_ID = "3c6f01a1-7e41-4089-b11d-bd7508e9f6e6"

export async function POST() {
  try {
    const { stdout } = await execAsync(`/home/cluvis/.npm-global/bin/openclaw cron run ${OPENCLAW_CRON_JOB_ID}`)

    return NextResponse.json({
      ok: true,
      enqueued: true,
      jobId: OPENCLAW_CRON_JOB_ID,
      output: stdout,
    })
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 })
  }
}
