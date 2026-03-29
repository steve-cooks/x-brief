import { NextResponse } from "next/server"
import { readFile } from "fs/promises"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

export const dynamic = "force-dynamic"

async function loadReadIds(dataDir: string): Promise<Set<string>> {
  try {
    const raw = await readFile(join(dataDir, "read-state.json"), "utf-8")
    const parsed = JSON.parse(raw)
    return new Set(Array.isArray(parsed?.ids) ? parsed.ids : [])
  } catch {
    return new Set()
  }
}

interface MediaItem {
  type: string
  url?: string
  preview_image_url?: string
  video_url?: string
  alt_text?: string
}

interface Metrics {
  likes?: number
  reposts?: number
  views?: number
  replies?: number
  bookmarks?: number
}

interface ThreadPost {
  id?: string | null
  text: string
  url?: string | null
}

interface LinkCard {
  title: string
  description?: string
  thumbnail?: string | null
  domain?: string
  url?: string
}

interface CommunityNote {
  text: string
  url?: string | null
}

interface QuotedPost {
  authorName: string
  authorUsername: string
  authorAvatarUrl?: string
  verified?: string | null
  text: string
  media?: MediaItem[]
  metrics?: Metrics
  postUrl?: string
  timestamp?: string
  createdAt?: string
  linkCard?: LinkCard
}

interface StoredPost {
  id: string
  author: string
  handle: string
  text: string
  url: string
  tab: string
  scraped_at: string
  seen: boolean
  authorAvatarUrl?: string
  verified?: string | null
  media?: MediaItem[]
  metrics?: Metrics
  source?: "for_you" | "following" | null
  is_article?: boolean
  article_url?: string | null
  thread_posts?: ThreadPost[]
  quotedPost?: QuotedPost
  linkCard?: LinkCard
  communityNote?: CommunityNote | null
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
        .slice(0, 10)
        .map((post) => ({
          id: post.id,
          authorName: post.author,
          authorUsername: post.handle,
          authorAvatarUrl: post.authorAvatarUrl,
          verified: post.verified,
          text: post.text,
          media: post.media,
          metrics: post.metrics,
          postUrl: post.url,
          source: post.source ?? normalizeTab(post.tab),
          is_article: post.is_article,
          article_url: post.article_url,
          thread_posts: post.thread_posts,
          quotedPost: post.quotedPost,
          linkCard: post.linkCard,
          communityNote: post.communityNote,
          timestamp: post.scraped_at,
          createdAt: post.scraped_at,
        })),
    },
    {
      title: "Following 👥",
      emoji: "👥",
      posts: unseenPosts
        .filter((post) => post.tab === "following")
        .slice(0, 10)
        .map((post) => ({
          id: post.id,
          authorName: post.author,
          authorUsername: post.handle,
          authorAvatarUrl: post.authorAvatarUrl,
          verified: post.verified,
          text: post.text,
          media: post.media,
          metrics: post.metrics,
          postUrl: post.url,
          source: post.source ?? normalizeTab(post.tab),
          is_article: post.is_article,
          article_url: post.article_url,
          thread_posts: post.thread_posts,
          quotedPost: post.quotedPost,
          linkCard: post.linkCard,
          communityNote: post.communityNote,
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

  const readIds = await loadReadIds(dataDir)

  // Filter posts within a briefing section by read-state and 24h scan age
  const cutoff = Date.now() - 24 * 60 * 60 * 1000
  function filterSection(posts: unknown[]): unknown[] {
    return posts.filter((post) => {
      const p = post as Record<string, unknown>
      const id = typeof p.id === "string" ? p.id : null
      if (id && readIds.has(id)) return false
      const ts = typeof p.timestamp === "string" ? new Date(p.timestamp).getTime() : 0
      const createdAt = typeof p.createdAt === "string" ? new Date(p.createdAt).getTime() : 0
      const scannedAt = ts || createdAt
      return scannedAt === 0 || scannedAt >= cutoff
    })
  }

  let latestBriefing: BriefingPayload | null = null

  for (const briefingPath of briefingPaths) {
    try {
      const data = await readFile(briefingPath, "utf-8")
      latestBriefing = JSON.parse(data)
      if (Array.isArray(latestBriefing?.sections) && latestBriefing.sections.length > 0) {
        // Filter each section's posts by read-state + 24h cutoff
        const filtered = {
          ...latestBriefing,
          sections: latestBriefing.sections.map((section) => ({
            ...section,
            posts: filterSection(section.posts ?? []),
          })),
        }
        return NextResponse.json(filtered)
      }
      break
    } catch {
      // Try next fallback path.
    }
  }

  for (const postsPath of postsPaths) {
    try {
      const data = await readFile(postsPath, "utf-8")
      const posts: StoredPost[] = JSON.parse(data)
      if (Array.isArray(posts)) {
        // Filter by read-state and 24h cutoff before building fallback briefing
        const filtered = posts.filter((p) => {
          if (readIds.has(p.id) || p.seen) return false
          const scannedAt = p.scraped_at ? new Date(p.scraped_at).getTime() : 0
          return scannedAt === 0 || scannedAt >= cutoff
        })
        return NextResponse.json(buildFallbackBriefing(filtered, latestBriefing ?? undefined))
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
