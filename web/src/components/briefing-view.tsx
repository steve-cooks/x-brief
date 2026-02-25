"use client"

import { useEffect, useState, useCallback } from "react"
import { useTheme } from "next-themes"
import { PostCard } from "@/components/x-brief/post-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { RefreshCw, Sun, Moon, AlertTriangle } from "lucide-react"

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
      linkCard?: {
        title: string
        description?: string
        thumbnail?: string | null
        domain?: string
        url?: string
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

// Map section titles → display info
const SECTION_DISPLAY: Record<string, { label: string; id: string }> = {
  "TOP STORIES": { label: "Top Stories", id: "top_stories" },
  "TRENDING IN YOUR NICHES": { label: "Trending", id: "trending" },
  "WORTH A LOOK": { label: "Picks", id: "worth_a_look" },
  "VIRAL 🔥": { label: "Viral 🔥", id: "viral" },
  "YOUR CIRCLE": { label: "Your Circle", id: "your_circle" },
}

// Preferred tab order
const TAB_ORDER = ["top_stories", "viral", "your_circle", "trending", "worth_a_look"]

function formatStat(num: number): string {
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

function formatLastUpdated(generatedAt: string): string {
  const date = new Date(generatedAt)
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
  }) + " at " + date.toLocaleTimeString("en-US", {
    hour: "numeric",
    minute: "2-digit",
  })
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

function ThemeToggle() {
  const { theme, setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null // avoid hydration mismatch

  const isDark = resolvedTheme === "dark"

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="flex items-center justify-center h-8 w-8 rounded-full text-muted-foreground hover:bg-[rgba(29,155,240,0.1)] hover:text-[#1d9bf0] transition-colors"
    >
      {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
    </button>
  )
}

export function BriefingView() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [minutesAgo, setMinutesAgo] = useState<number>(0)
  const [activeTab, setActiveTab] = useState<string>("")

  // Derive tabs from actual briefing data — only sections that have posts
  const availableTabs = briefing
    ? briefing.sections
        .filter((s) => s.posts.length > 0 && SECTION_DISPLAY[s.title])
        .map((s) => ({
          ...SECTION_DISPLAY[s.title],
          posts: s.posts,
          count: s.posts.length,
        }))
        .sort((a, b) => {
          const ai = TAB_ORDER.indexOf(a.id)
          const bi = TAB_ORDER.indexOf(b.id)
          return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
        })
    : []

  // Set default active tab when briefing loads
  useEffect(() => {
    if (availableTabs.length > 0 && !activeTab) {
      setActiveTab(availableTabs[0].id)
    }
  }, [availableTabs.length, activeTab])

  const fetchBriefing = useCallback(async (showRefreshing = false) => {
    if (showRefreshing) setRefreshing(true)
    try {
      const response = await fetch("/api/briefing")
      const data = await response.json()
      if (!briefing || data.generated_at !== briefing.generated_at) {
        setBriefing(data)
      }
      setLoading(false)
    } catch (error) {
      console.error("Failed to fetch briefing:", error)
      setLoading(false)
    } finally {
      if (showRefreshing) setRefreshing(false)
    }
  }, [briefing])

  // Initial fetch
  useEffect(() => {
    fetchBriefing()
  }, [])

  // Poll every 5 minutes
  useEffect(() => {
    const interval = setInterval(() => fetchBriefing(), 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchBriefing])

  // Update "X ago" every minute
  useEffect(() => {
    if (!briefing?.generated_at) return
    const update = () => {
      const diff = Math.floor((Date.now() - new Date(briefing.generated_at).getTime()) / 60000)
      setMinutesAgo(diff)
    }
    update()
    const interval = setInterval(update, 60000)
    return () => clearInterval(interval)
  }, [briefing?.generated_at])

  const isStale = minutesAgo > 720 // 12 hours

  const relativeTime =
    minutesAgo < 1
      ? "just now"
      : minutesAgo < 60
      ? `${minutesAgo}m ago`
      : minutesAgo < 1440
      ? `${Math.floor(minutesAgo / 60)}h ago`
      : `${Math.floor(minutesAgo / 1440)}d ago`

  return (
    <div className="min-h-screen bg-background overflow-x-hidden">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-background/95 backdrop-blur-md border-b border-border">
        <div className="max-w-[598px] mx-auto">
          <div className="flex items-center justify-between px-4 h-[53px]">
            {/* Logo + timestamp */}
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-foreground tracking-tight">
                𝕏 Brief
              </h1>
              {briefing && (
                <div className="flex items-center gap-1.5">
                  <span className="text-[13px] text-muted-foreground">
                    Updated {relativeTime}
                  </span>
                  {isStale && (
                    <span
                      title="Data may be stale — last update was over 12 hours ago"
                      className="flex items-center gap-0.5 text-[12px] text-amber-500 dark:text-amber-400"
                    >
                      <AlertTriangle className="h-3 w-3" />
                      Stale
                    </span>
                  )}
                </div>
              )}
            </div>

            {/* Actions */}
            <div className="flex items-center gap-1">
              {briefing && (
                <button
                  onClick={() => fetchBriefing(true)}
                  disabled={refreshing}
                  aria-label="Refresh briefing"
                  className="flex items-center justify-center h-8 w-8 rounded-full text-muted-foreground hover:bg-[rgba(29,155,240,0.1)] hover:text-[#1d9bf0] transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
                </button>
              )}
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {/* Loading */}
      {loading && <LoadingSkeleton />}

      {/* Main content */}
      {!loading && briefing && availableTabs.length > 0 && (
        <div className="w-full overflow-hidden">
          <Tabs
            key={briefing.generated_at}
            value={activeTab}
            onValueChange={setActiveTab}
            className="w-full"
          >
            {/* Tab navigation */}
            <div className="sticky top-[53px] z-40 bg-background/95 backdrop-blur-md border-b border-border">
              <div className="max-w-[598px] mx-auto overflow-x-auto scrollbar-hide">
                <TabsList className="w-full h-auto p-0 bg-transparent rounded-none border-0 flex">
                  {availableTabs.map((tab) => (
                    <TabsTrigger
                      key={tab.id}
                      value={tab.id}
                      className="relative flex-1 py-4 px-3 rounded-none border-0 bg-transparent text-[15px] font-medium text-muted-foreground hover:bg-foreground/[0.03] data-[state=active]:text-foreground data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:font-bold transition-colors after:absolute after:bottom-0 after:left-1/2 after:-translate-x-1/2 after:w-14 after:h-1 after:bg-[#1d9bf0] after:rounded-full after:opacity-0 data-[state=active]:after:opacity-100 after:transition-all after:duration-200"
                    >
                      <span className="text-[15px] whitespace-nowrap">
                        {tab.label}
                      </span>
                    </TabsTrigger>
                  ))}
                </TabsList>
              </div>
            </div>

            {/* Tab content */}
            <div className="max-w-[598px] w-full mx-auto md:border-x md:border-border min-h-screen overflow-hidden">
              {availableTabs.map((tab) => (
                <TabsContent
                  key={tab.id}
                  value={tab.id}
                  className="mt-0 focus-visible:outline-none focus-visible:ring-0 animate-fade-in"
                >
                  <div>
                    {tab.posts.map((post, index) => (
                      <div
                        key={`${post.authorUsername}-${index}`}
                        className="px-4 py-3 border-b border-border cursor-pointer hover:bg-foreground/[0.03] transition-colors overflow-hidden"
                        onClick={() => {
                          if (post.postUrl) window.open(post.postUrl, "_blank", "noopener,noreferrer")
                        }}
                      >
                        <PostCard {...post} />
                      </div>
                    ))}
                  </div>
                </TabsContent>
              ))}
            </div>
          </Tabs>
        </div>
      )}

      {/* No briefing yet */}
      {!loading && (!briefing || availableTabs.length === 0) && (
        <div className="max-w-[598px] mx-auto md:border-x md:border-border px-4 text-center py-20">
          <p className="text-[15px] text-muted-foreground">
            No briefing available yet.
          </p>
          <p className="text-[13px] text-muted-foreground mt-2">
            Run the pipeline to generate your first briefing.
          </p>
        </div>
      )}

      {/* Footer */}
      {!loading && briefing && (
        <div className="max-w-[598px] mx-auto md:border-x md:border-border px-4 py-8 border-t border-t-border">
          <p className="text-center text-[12px] text-muted-foreground/60">
            Scanned {formatStat(briefing.stats.posts_scanned)} posts from{" "}
            {briefing.stats.accounts_tracked} accounts
          </p>
          <p className="text-center text-[11px] text-muted-foreground/40 mt-1">
            Last updated {formatLastUpdated(briefing.generated_at)}
          </p>
        </div>
      )}
    </div>
  )
}
