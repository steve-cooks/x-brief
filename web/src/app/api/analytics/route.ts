import { NextResponse } from "next/server"

export const dynamic = "force-dynamic"

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
 * Accept client-side analytics dump and log to stdout (for now).
 * Can be extended to write to a file or database.
 */
export async function POST(request: Request) {
  try {
    const body = await request.json()
    const events = Array.isArray(body) ? body : body.events || []
    // Log to stdout for collection by systemd journal
    console.log(`[analytics] Received ${events.length} events`)
    return NextResponse.json({ received: events.length })
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 })
  }
}
