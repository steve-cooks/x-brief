import { NextResponse } from "next/server"

export const dynamic = "force-static"

export async function GET() {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="192" height="192" viewBox="0 0 192 192" fill="none">
  <rect width="192" height="192" rx="36" fill="#0D1117"/>
  <text x="50%" y="54%" text-anchor="middle" dominant-baseline="middle" fill="#1D9BF0" font-family="Inter, Arial, sans-serif" font-size="96" font-weight="700">𝕏</text>
</svg>`

  return new NextResponse(svg, {
    headers: {
      "Content-Type": "image/svg+xml",
      "Cache-Control": "public, max-age=31536000, immutable",
    },
  })
}
