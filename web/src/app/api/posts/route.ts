import { NextResponse } from "next/server"
import { mkdir, readFile, writeFile } from "fs/promises"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

export const dynamic = "force-dynamic"

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

interface Post {
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

function getDataDir() {
  const routeDir = dirname(fileURLToPath(import.meta.url))
  const defaultDataDir = join(routeDir, "..", "..", "..", "..", "..", "..", "data")
  return process.env.X_BRIEF_DATA_DIR || defaultDataDir
}

function getPostsPath() {
  return join(getDataDir(), "posts.json")
}

function getReadStatePath() {
  return join(getDataDir(), "read-state.json")
}

async function loadReadState(): Promise<Set<string>> {
  try {
    const raw = await readFile(getReadStatePath(), "utf-8")
    const parsed = JSON.parse(raw)
    const ids = Array.isArray(parsed?.ids) ? parsed.ids : []
    return new Set(ids)
  } catch {
    return new Set()
  }
}

async function loadPosts(): Promise<Post[]> {
  const filePath = getPostsPath()
  try {
    const raw = await readFile(filePath, "utf-8")
    const parsed = JSON.parse(raw)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

async function savePosts(posts: Post[]) {
  const filePath = getPostsPath()
  await mkdir(dirname(filePath), { recursive: true })
  await writeFile(filePath, JSON.stringify(posts, null, 2), "utf-8")
}

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const showAll = searchParams.get("all") === "true"
  const [posts, readIds] = await Promise.all([loadPosts(), loadReadState()])

  // Only serve posts scanned within the last 24 hours
  const cutoff = Date.now() - 24 * 60 * 60 * 1000
  const recent = posts.filter((post) => {
    const scannedAt = post.scraped_at ? new Date(post.scraped_at).getTime() : 0
    return scannedAt >= cutoff
  })

  // A post is "seen" if it's in read-state.json OR if posts.json marks it seen
  const isRead = (post: Post) => readIds.has(post.id) || post.seen

  const filtered = showAll ? recent : recent.filter((post) => !isRead(post))
  return NextResponse.json({
    posts: filtered,
    total: recent.length,
    unseen: recent.filter((post) => !isRead(post)).length,
  })
}

export async function POST(request: Request) {
  try {
    const body = await request.json()
    const ids = Array.isArray(body?.ids) ? body.ids.filter((id: unknown) => typeof id === "string") : []

    if (ids.length === 0) {
      return NextResponse.json({ error: "Expected ids: string[]" }, { status: 400 })
    }

    const posts = await loadPosts()
    const idSet = new Set(ids)

    for (const post of posts) {
      if (idSet.has(post.id)) {
        post.seen = true
      }
    }

    await savePosts(posts)
    return NextResponse.json({ marked: ids.length })
  } catch {
    return NextResponse.json({ error: "Invalid JSON" }, { status: 400 })
  }
}
