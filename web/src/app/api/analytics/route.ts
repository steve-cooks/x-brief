import { NextResponse } from "next/server"

export const dynamic = "force-dynamic"
const MAX_ANALYTICS_PAYLOAD_BYTES = 50 * 1024

/**
 * GET /api/analytics
 *
 * Analytics are stored client-side in localStorage. This endpoint exists
 * so clients can POST their analytics for server-side collection, or
 * as a simple health-check. The actual data dump is done client-side
 * via the analytics.ts getAnalytics() function.
 *
 * For now, returns a stub explaining that analytics are client-side.
 */
export async function GET() {
  return NextResponse.json({
    message: "Analytics are stored client-side in localStorage. Use the browser console: JSON.parse(localStorage.getItem('x-brief-analytics'))",
    storage_key: "x-brief-analytics",
    instructions: "POST to this endpoint to upload client-side analytics for server collection.",
  })
}

/**
 * POST /api/analytics
 *
 * Accept client-side analytics dump.
 * Can be extended to write to a file or database.
 */
export async function POST(request: Request) {
  try {
    // SECURITY NOTE: Disable this endpoint or enforce strict auth/rate limits before production deployment.
    const rawBody = await request.text()
    if (new TextEncoder().encode(rawBody).length > MAX_ANALYTICS_PAYLOAD_BYTES) {
      return NextResponse.json({ error: "Payload too large" }, { status: 413 })
    }

    const body = JSON.parse(rawBody)
    const events = Array.isArray(body) ? body : body.events || []
    return NextResponse.json({ received: events.length })
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 })
  }
}
