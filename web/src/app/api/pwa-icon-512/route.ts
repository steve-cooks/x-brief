import { NextResponse } from "next/server"

export const dynamic = "force-static"

export async function GET() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="512" height="512" viewBox="0 0 512 512" fill="none">
  <rect width="512" height="512" rx="96" fill="#0D1117"/>
  <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" fill="#1D9BF0" font-family="Inter, Arial, sans-serif" font-size="256" font-weight="700">𝕏</text>
</svg>`

  return new NextResponse(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  })
}
