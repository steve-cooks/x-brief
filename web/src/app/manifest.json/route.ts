import { NextResponse } from "next/server"

export const dynamic = "force-static"

export async function GET() {
  return NextResponse.json({
    name: "X Brief",
    short_name: "X Brief",
    description: "AI-powered X timeline briefing",
    start_url: "/",
    display: "standalone",
    background_color: "#0D1117",
    theme_color: "#0D1117",
    icons: [
      {
        src: "/api/pwa-icon-192",
        sizes: "192x192",
        type: "image/svg+xml",
      },
      {
        src: "/api/pwa-icon-512",
        sizes: "512x512",
        type: "image/svg+xml",
      },
    ],
  })
}
