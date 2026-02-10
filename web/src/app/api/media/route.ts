import { NextRequest, NextResponse } from "next/server"

// Proxy video/image from Twitter CDN to avoid referer blocking
export async function GET(request: NextRequest) {
  const url = request.nextUrl.searchParams.get("url")
  
  if (!url) {
    return NextResponse.json({ error: "Missing url parameter" }, { status: 400 })
  }

  // Only allow Twitter CDN domains
  const allowed = ["video.twimg.com", "pbs.twimg.com"]
  try {
    const parsed = new URL(url)
    if (!allowed.some(d => parsed.hostname === d)) {
      return NextResponse.json({ error: "Domain not allowed" }, { status: 403 })
    }
  } catch {
    return NextResponse.json({ error: "Invalid URL" }, { status: 400 })
  }

  try {
    const resp = await fetch(url, {
      headers: {
        "User-Agent": "Mozilla/5.0",
      },
      // No referer sent from server-side fetch
    })

    if (!resp.ok) {
      return NextResponse.json({ error: `Upstream ${resp.status}` }, { status: 502 })
    }

    const contentType = resp.headers.get("content-type") || "application/octet-stream"
    const contentLength = resp.headers.get("content-length")
    
    const headers: Record<string, string> = {
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=86400, immutable",
      "Access-Control-Allow-Origin": "*",
    }
    if (contentLength) headers["Content-Length"] = contentLength

    // Stream the response body through
    return new NextResponse(resp.body, { status: 200, headers })
  } catch (e) {
    return NextResponse.json({ error: "Fetch failed" }, { status: 502 })
  }
}
