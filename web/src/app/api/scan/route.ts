import { NextResponse } from "next/server"

export const dynamic = "force-dynamic"

const OPENCLAW_CRON_JOB_ID = "3c6f01a1-7e41-4089-b11d-bd7508e9f6e6"
const OPENCLAW_GATEWAY_BASE_URL = "http://127.0.0.1:18789"

function buildGatewayUrls(jobId: string) {
  return [
    {
      kind: "primary" as const,
      url: `${OPENCLAW_GATEWAY_BASE_URL}/api/cron/${jobId}/run`,
    },
    {
      kind: "fallback" as const,
      url: `${OPENCLAW_GATEWAY_BASE_URL}/api/v1/cron/${jobId}/run`,
    },
  ]
}

async function readGatewayPayload(response: Response) {
  const raw = await response.text()

  if (!raw) {
    return null
  }

  try {
    return JSON.parse(raw) as unknown
  } catch {
    return raw
  }
}

export async function POST() {
  const token = process.env.OPENCLAW_GATEWAY_TOKEN
  if (!token) {
    return NextResponse.json(
      { error: "OPENCLAW_GATEWAY_TOKEN is not configured." },
      { status: 500 }
    )
  }

  let lastErrorStatus = 502
  let lastErrorDetails: unknown = null

  for (const attempt of buildGatewayUrls(OPENCLAW_CRON_JOB_ID)) {
    try {
      const response = await fetch(attempt.url, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${token}`,
        },
        cache: "no-store",
      })

      const payload = await readGatewayPayload(response)

      if (response.ok) {
        return NextResponse.json({
          ok: true,
          jobId: OPENCLAW_CRON_JOB_ID,
          endpoint: attempt.kind,
          data: payload,
        })
      }

      lastErrorStatus = response.status
      lastErrorDetails = payload
    } catch (error) {
      lastErrorStatus = 502
      lastErrorDetails = error instanceof Error ? error.message : "Unknown gateway error"
    }
  }

  return NextResponse.json(
    {
      error: "Failed to trigger OpenClaw cron job.",
      jobId: OPENCLAW_CRON_JOB_ID,
      details: lastErrorDetails,
    },
    { status: lastErrorStatus }
  )
}
