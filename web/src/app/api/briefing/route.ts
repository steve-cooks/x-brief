import { NextResponse } from "next/server"
import { readFile } from "fs/promises"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

export const dynamic = "force-dynamic"

interface StoredPost {
  id: string
  author: string
  handle: string
  text: string
  url: string
  tab: string
  scraped_at: string
  seen: boolean
}

interface BriefingPayload {
  generated_at?: string
  updated_at?: string
  period_hours?: number
  tldr?: string
  sections?: Array<{
    title: string
    emoji: string
    posts: unknown[]
  }>
  stats?: Record<string, unknown>
}

function getDataDir() {
  const routeDir = dirname(fileURLToPath(import.meta.url))
  const defaultDataDir = join(routeDir, "..", "..", "..", "..", "..", "..", "data")
  return process.env.X_BRIEF_DATA_DIR || defaultDataDir
}

function normalizeTab(tab: string) {
  return tab === "following" ? "following" : "for_you"
}

function buildFallbackBriefing(posts: StoredPost[], briefing?: BriefingPayload) {
  const unseenPosts = posts.filter((post) => !post.seen)
  const uniqueHandles = new Set(posts.map((post) => post.handle).filter(Boolean))
  const generatedAt =
    briefing?.generated_at ||
    briefing?.updated_at ||
    unseenPosts[0]?.scraped_at ||
    posts[0]?.scraped_at ||
    new Date().toISOString()

  const sections = [
    {
      title: "Can't Miss 🔥",
      emoji: "⚡",
      posts: [],
    },
    {
      title: "For You 📌",
      emoji: "📌",
      posts: unseenPosts
        .filter((post) => post.tab === "foryou")
        .map((post) => ({
          authorName: post.author,
          authorUsername: post.handle,
          text: post.text,
          postUrl: post.url,
          source: normalizeTab(post.tab),
          timestamp: post.scraped_at,
          createdAt: post.scraped_at,
        })),
    },
    {
      title: "Following 👥",
      emoji: "👥",
      posts: unseenPosts
        .filter((post) => post.tab === "following")
        .map((post) => ({
          authorName: post.author,
          authorUsername: post.handle,
          text: post.text,
          postUrl: post.url,
          source: normalizeTab(post.tab),
          timestamp: post.scraped_at,
          createdAt: post.scraped_at,
        })),
    },
  ]

  return {
    generated_at: generatedAt,
    period_hours: briefing?.period_hours ?? 4,
    tldr: briefing?.tldr ?? (unseenPosts.length === 0 ? "Nothing new since your last check." : undefined),
    sections,
    stats: {
      posts_scanned: posts.length,
      accounts_tracked: uniqueHandles.size,
      interests_detected: 0,
      breakout_posts: 0,
      unseen_count: unseenPosts.length,
      ...(briefing?.stats ?? {}),
    },
  }
}

export async function GET() {
  const dataDir = getDataDir()
  const briefingPaths = [
    join(dataDir, "latest-briefing.json"),
    join(process.cwd(), "..", "data", "latest-briefing.json"),
  ]
  const postsPaths = [join(dataDir, "posts.json"), join(process.cwd(), "..", "data", "posts.json")]

  let latestBriefing: BriefingPayload | null = null

  for (const briefingPath of briefingPaths) {
    try {
      const data = await readFile(briefingPath, "utf-8")
      latestBriefing = JSON.parse(data)
      if (Array.isArray(latestBriefing?.sections) && latestBriefing.sections.length > 0) {
        return NextResponse.json(latestBriefing)
      }
      break
    } catch {
      // Try next fallback path.
    }
  }

  for (const postsPath of postsPaths) {
    try {
      const data = await readFile(postsPath, "utf-8")
      const posts = JSON.parse(data)
      if (Array.isArray(posts)) {
        return NextResponse.json(buildFallbackBriefing(posts, latestBriefing ?? undefined))
      }
    } catch {
      // Try next fallback path.
    }
  }

  return NextResponse.json(
    { error: "No briefing available. Run the pipeline first.", sections: [], stats: {} },
    { status: 404 }
  )
}
