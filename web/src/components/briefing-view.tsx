"use client"

import { useEffect, useState } from "react"
import { PostCard } from "@/components/x-brief/post-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

interface BriefingData {
  generated_at: string
  period_hours: number
  sections: Array<{
    title: string
    emoji: string
    posts: Array<{
      authorName: string
      authorUsername: string
      authorAvatarUrl?: string
      verified?: string | null
      text: string
      media?: Array<{
        type: string
        url?: string
        preview_image_url?: string
        video_url?: string
        alt_text?: string
      }>
      metrics?: { likes?: number; reposts?: number; views?: number; replies?: number; bookmarks?: number }
      postUrl?: string
      timestamp?: string
      createdAt?: string
      category?: string
      quotedPost?: {
        authorName: string
        authorUsername: string
        authorAvatarUrl?: string
        verified?: string | null
        text: string
        media?: Array<{
          type: string
          url?: string
          preview_image_url?: string
          video_url?: string
          alt_text?: string
        }>
        metrics?: { likes?: number; reposts?: number; views?: number; replies?: number; bookmarks?: number }
        postUrl?: string
        timestamp?: string
        createdAt?: string
      }
    }>
  }>
  stats: {
    posts_scanned: number
    accounts_tracked: number
    interests_detected: number
    breakout_posts: number
  }
}

function formatStat(num: number): string {
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

function LoadingSkeleton() {
  return (
    <div className="space-y-3 px-4 py-6 animate-pulse">
      {[1, 2, 3, 4].map((i) => (
        <Skeleton key={i} className="h-32 w-full rounded-xl" />
      ))}
    </div>
  )
}

// Fixed tab definitions — always show all 4 tabs
const TABS = [
  { id: "viral", label: "Viral", sectionTitle: "VIRAL \uD83D\uDD25" },
  { id: "top_stories", label: "Top Stories", sectionTitle: "TOP STORIES" },
  { id: "trending", label: "Trending", sectionTitle: "TRENDING IN YOUR NICHES" },
  { id: "worth_a_look", label: "Picks", sectionTitle: "WORTH A LOOK" },
] as const

type Post = BriefingData["sections"][number]["posts"][number]

function getPostsForTab(briefing: BriefingData, tabId: string): Post[] {
  const tab = TABS.find((t) => t.id === tabId)
  if (!tab) return []

  // Find the matching section by title
  const section = briefing.sections.find((s) => s.title === tab.sectionTitle)
  if (section) return section.posts

  // Fallback: also check for YOUR CIRCLE section posts in top_stories tab
  if (tabId === "top_stories") {
    const circle = briefing.sections.find((s) => s.title === "YOUR CIRCLE")
    if (circle) return circle.posts
  }

  return []
}

export function BriefingView() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [minutesAgo, setMinutesAgo] = useState<number>(0)

  // Fetch briefing data
  const fetchBriefing = async () => {
    try {
      const response = await fetch("/api/briefing")
      const data = await response.json()

      // Only update if data changed (compare generated_at timestamp)
      if (!briefing || data.generated_at !== briefing.generated_at) {
        setBriefing(data)
      }

      setLoading(false)
    } catch (error) {
      console.error("Failed to fetch briefing:", error)
      setLoading(false)
    }
  }

  // Initial fetch
  useEffect(() => {
    fetchBriefing()
  }, [])

  // Poll for updates every 5 minutes
  useEffect(() => {
    const pollInterval = setInterval(() => {
      fetchBriefing()
    }, 5 * 60 * 1000) // 5 minutes

    return () => clearInterval(pollInterval)
  }, [briefing])

  // Update "X minutes ago" based on generated_at (data freshness, not page load)
  useEffect(() => {
    if (!briefing?.generated_at) return

    const updateMinutes = () => {
      const now = new Date()
      const generatedAt = new Date(briefing.generated_at)
      const diff = Math.floor((now.getTime() - generatedAt.getTime()) / 60000)
      setMinutesAgo(diff)
    }

    updateMinutes()
    const minuteInterval = setInterval(updateMinutes, 60000) // Update every minute

    return () => clearInterval(minuteInterval)
  }, [briefing?.generated_at])

  const generatedDate = briefing
    ? new Date(briefing.generated_at).toLocaleDateString("en-US", {
        weekday: "long",
        month: "short",
        day: "numeric",
      })
    : ""

  return (
    <div className="min-h-screen bg-white dark:bg-black">
      {/* Header - Fixed like X */}
      <header className="sticky top-0 z-50 bg-white/95 dark:bg-black/95 backdrop-blur-md border-b border-[#eff3f4] dark:border-[#2f3336]">
        <div className="max-w-[598px] mx-auto">
          <div className="flex items-center justify-between px-4 h-[53px]">
            <h1 className="text-xl font-bold text-[#0f1419] dark:text-[#e7e9ea] tracking-tight">
              𝕏 Brief
            </h1>
            {briefing && (
              <div className="flex items-center gap-2">
                <span className="text-[13px] text-[#536471] dark:text-[#71767b]">
                  {minutesAgo < 1
                    ? "Updated just now"
                    : minutesAgo < 60
                    ? `Updated ${minutesAgo}m ago`
                    : minutesAgo < 1440
                    ? `Updated ${Math.floor(minutesAgo / 60)}h ago`
                    : `Updated ${Math.floor(minutesAgo / 1440)}d ago`}
                </span>
                {minutesAgo > 240 && (
                  <span className="text-[13px] text-[#536471] dark:text-[#71767b]">
                    · Data may be stale
                  </span>
                )}
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Loading state */}
      {loading && <LoadingSkeleton />}

      {/* Main content with tabs */}
      {!loading && briefing && (
        <Tabs key={briefing.generated_at} defaultValue="viral" className="w-full">
          {/* Tab navigation - X style */}
          <div className="sticky top-[57px] z-40 bg-white/95 dark:bg-black/95 backdrop-blur-md border-b border-[#eff3f4] dark:border-[#2f3336]">
            <div className="max-w-[598px] mx-auto overflow-x-auto scrollbar-hide">
              <TabsList className="w-full h-auto p-0 bg-transparent rounded-none border-0 flex">
                {TABS.map((tab) => (
                  <TabsTrigger
                    key={tab.id}
                    value={tab.id}
                    className="relative flex-1 py-4 rounded-none border-0 bg-transparent text-[15px] font-medium text-[#536471] dark:text-[#71767b] hover:bg-[rgba(0,0,0,0.03)] dark:hover:bg-[rgba(255,255,255,0.03)] data-[state=active]:text-[#0f1419] dark:data-[state=active]:text-[#e7e9ea] data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:font-bold transition-colors after:absolute after:bottom-0 after:left-1/2 after:-translate-x-1/2 after:w-14 after:h-[3px] after:bg-[#1d9bf0] after:rounded-full after:opacity-0 data-[state=active]:after:opacity-100 after:transition-all after:duration-200"
                  >
                    <span className="text-[15px]">{tab.label}</span>
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
          </div>

          {/* Tab content */}
          <div className="max-w-[598px] mx-auto border-x border-[#eff3f4] dark:border-[#2f3336] min-h-screen">
            {TABS.map((tab) => {
              const posts = getPostsForTab(briefing, tab.id)
              const isViral = tab.id === "viral"
              return (
                <TabsContent
                  key={tab.id}
                  value={tab.id}
                  className="mt-0 focus-visible:outline-none focus-visible:ring-0 animate-fade-in"
                >
                  {/* Posts feed */}
                  {posts.length > 0 && (
                    <div>
                      {posts.map((post, index) => (
                        <div
                          key={`${post.authorUsername}-${index}`}
                          className="px-4 py-3 border-b border-[#eff3f4] dark:border-[#2f3336] transition-colors cursor-pointer hover:bg-[rgba(0,0,0,0.03)] dark:hover:bg-[rgba(255,255,255,0.03)]"
                          onClick={() => {
                            if (post.postUrl) window.open(post.postUrl, "_blank", "noopener,noreferrer")
                          }}
                        >
                          {isViral && (
                            <div className="flex items-center gap-1 mb-1">
                              <span className="text-[13px] font-bold text-[#536471] dark:text-[#71767b]">
                                🔥 Viral
                              </span>
                            </div>
                          )}
                          <PostCard {...post} />
                        </div>
                      ))}
                    </div>
                  )}

                  {/* Empty state */}
                  {posts.length === 0 && (
                    <div className="text-center py-20">
                      <p className="text-[15px] text-[#536471] dark:text-[#71767b]">
                        No posts in this category
                      </p>
                    </div>
                  )}
                </TabsContent>
              )
            })}
          </div>
        </Tabs>
      )}

      {/* Empty state - no briefing */}
      {!loading && !briefing && (
        <div className="max-w-[598px] mx-auto border-x border-[#eff3f4] dark:border-[#2f3336] px-4 text-center py-20">
          <p className="text-[15px] text-[#536471] dark:text-[#71767b]">
            No briefing available yet.
          </p>
          <p className="text-[13px] text-[#536471] dark:text-[#71767b] mt-2">
            Run the pipeline to generate your first briefing.
          </p>
        </div>
      )}

      {/* Footer — subtle single line */}
      {!loading && briefing && (
        <div className="max-w-[598px] mx-auto border-x border-[#eff3f4] dark:border-[#2f3336] px-4 py-6">
          <p className="text-center text-[13px] text-[#536471] dark:text-[#71767b]">
            Scanned {formatStat(briefing.stats.posts_scanned)} posts from{" "}
            {briefing.stats.accounts_tracked} accounts · Generated{" "}
            {new Date(briefing.generated_at).toLocaleDateString("en-US", {
              month: "short",
              day: "numeric",
            })}{" "}
            at{" "}
            {new Date(briefing.generated_at).toLocaleTimeString("en-US", {
              hour: "numeric",
              minute: "2-digit",
            })}
          </p>
        </div>
      )}
    </div>
  )
}
