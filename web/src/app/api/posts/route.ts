import { NextResponse } from "next/server"
import { mkdir, readFile, writeFile } from "fs/promises"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

export const dynamic = "force-dynamic"

interface Post {
  id: string
  author: string
  handle: string
  text: string
  url: string
  tab: string
  scraped_at: string
  seen: boolean
}

function getPostsPath() {
  const routeDir = dirname(fileURLToPath(import.meta.url))
  const defaultDataDir = join(routeDir, "..", "..", "..", "..", "..", "..", "data")
  const dataDir = process.env.X_BRIEF_DATA_DIR || defaultDataDir
  return join(dataDir, "posts.json")
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
  const posts = await loadPosts()
  const filtered = showAll ? posts : posts.filter((post) => !post.seen)
  return NextResponse.json({
    posts: filtered,
    total: posts.length,
    unseen: posts.filter((post) => !post.seen).length,
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
