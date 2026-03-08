"use client"

import { useEffect, useState, useCallback, useMemo, useRef } from "react"
import { useTheme } from "next-themes"
import { PostCard } from "@/components/x-brief/post-card"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { RefreshCw, Sun, Moon, AlertTriangle, Search, X } from "lucide-react"
import { useSwipeTabs } from "@/hooks/use-swipe-tabs"
import { MediaViewer } from "@/components/media-viewer"
import { markPostsAsRead, getReadPostIds, clearOldReadState } from "@/lib/read-state"
import { trackEvent } from "@/lib/analytics"

interface Post {
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
  source?: "for_you" | "following" | null
  is_article?: boolean
  article_url?: string | null
  thread_posts?: Array<{ id?: string | null; text: string; url?: string | null }>
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
}

interface BriefingData {
  generated_at: string
  period_hours: number
  sections: Array<{
    title: string
    emoji: string
    posts: Post[]
  }>
  stats: {
    posts_scanned: number
    accounts_tracked: number
    interests_detected: number
    breakout_posts: number
  }
}

const SECTION_DISPLAY: Record<string, { label: string; id: string; emptyMessage: string }> = {
  "Can't Miss 🔥": {
    label: "Can't Miss 🔥",
    id: "cant_miss",
    emptyMessage: "Nothing major happened. Go live your life. ✌️",
  },
  "For You 📌": {
    label: "For You",
    id: "for_you",
    emptyMessage: "Your timeline is quiet. Check back later.",
  },
  "Following 👥": {
    label: "Following",
    id: "following",
    emptyMessage: "Your follows haven't posted much. That's okay.",
  },
}

const TAB_ORDER = ["cant_miss", "for_you", "following"]

function formatStat(num: number): string {
  if (num >= 1000) return `${(num / 1000).toFixed(1)}K`
  return num.toString()
}

function formatLastUpdated(generatedAt: string): string {
  const date = new Date(generatedAt)
  return (
    date.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
    }) +
    " at " +
    date.toLocaleTimeString("en-US", {
      hour: "numeric",
      minute: "2-digit",
    })
  )
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
  const { setTheme, resolvedTheme } = useTheme()
  const [mounted, setMounted] = useState(false)

  useEffect(() => {
    setMounted(true)
  }, [])

  if (!mounted) return null

  const isDark = resolvedTheme === "dark"

  return (
    <button
      onClick={() => setTheme(isDark ? "light" : "dark")}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="flex items-center justify-center h-7 w-7 sm:h-8 sm:w-8 rounded-full text-muted-foreground hover:bg-[rgba(29,155,240,0.1)] hover:text-[#1d9bf0] transition-colors"
    >
      {isDark ? <Sun className="h-3.5 w-3.5 sm:h-4 sm:w-4" /> : <Moon className="h-3.5 w-3.5 sm:h-4 sm:w-4" />}
    </button>
  )
}

function postIdFromUrl(postUrl?: string): string | null {
  if (!postUrl) return null
  const match = postUrl.match(/\/status\/(\d+)/)
  return match ? match[1] : null
}

export function BriefingView() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [minutesAgo, setMinutesAgo] = useState<number>(0)
  const [activeTab, setActiveTab] = useState<string>("")
  const [readIds, setReadIds] = useState<Set<string>>(new Set())
  const [searchExpanded, setSearchExpanded] = useState(false)
  const [searchQuery, setSearchQuery] = useState("")
  const [mediaViewer, setMediaViewer] = useState<{
    items: Array<{ type: string; url?: string; preview_image_url?: string; video_url?: string; alt_text?: string }>
    index: number
  } | null>(null)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const pendingReadRef = useRef<Set<string>>(new Set())

  useEffect(() => {
    let cancelled = false

    const init = async () => {
      clearOldReadState()
      const localRead = getReadPostIds()
      setReadIds(localRead)

      try {
        const response = await fetch("/api/read-state", { cache: "no-store" })
        if (response.ok) {
          const data = await response.json()
          const serverIds = Array.isArray(data?.ids) ? data.ids.filter((id: unknown) => typeof id === "string") : []
          if (!cancelled) {
            setReadIds(new Set([...localRead, ...serverIds]))
          }
        }
      } catch {
        // localStorage fallback already loaded
      }

      trackEvent("page_view")
    }

    void init()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    const flush = async () => {
      if (pendingReadRef.current.size === 0) return
      const ids = Array.from(pendingReadRef.current)
      pendingReadRef.current.clear()

      markPostsAsRead(ids)

      try {
        await fetch("/api/read-state", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ ids }),
        })
      } catch {
        // localStorage fallback already persisted
      }
    }

    const interval = setInterval(() => {
      void flush()
    }, 2000)

    return () => {
      clearInterval(interval)
      void flush()
    }
  }, [])

  useEffect(() => {
    observerRef.current = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            const postId = (entry.target as HTMLElement).dataset.postId
            if (postId) {
              pendingReadRef.current.add(postId)
              trackEvent("post_impression", { postId })
            }
            observerRef.current?.unobserve(entry.target)
          }
        }
      },
      { threshold: 0.5 }
    )
    return () => observerRef.current?.disconnect()
  }, [])

  const fetchBriefing = useCallback(
    async (showRefreshing = false) => {
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
    },
    [briefing]
  )

  useEffect(() => {
    void fetchBriefing()
  }, [fetchBriefing])

  useEffect(() => {
    const interval = setInterval(() => {
      void fetchBriefing()
    }, 5 * 60 * 1000)
    return () => clearInterval(interval)
  }, [fetchBriefing])

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

  const normalizedSearch = searchQuery.trim().toLowerCase()
  const matchesSearch = useCallback(
    (post: Post) => {
      if (!normalizedSearch) return true
      return (
        post.text.toLowerCase().includes(normalizedSearch) ||
        post.authorUsername.toLowerCase().includes(normalizedSearch)
      )
    },
    [normalizedSearch]
  )

  const availableTabs = useMemo(() => {
    if (!briefing) return [] as Array<{ label: string; id: string; posts: Post[]; count: number; totalCount: number; emptyMessage: string }>

    const dynamicTabs = briefing.sections
      .map((s) => {
        const display = SECTION_DISPLAY[s.title]
        if (!display) return null

        const unread = s.posts.filter((p) => {
          const id = postIdFromUrl(p.postUrl)
          return !id || !readIds.has(id)
        })

        const basePosts = unread.length > 0 ? unread : s.posts
        const postsToShow = basePosts.filter(matchesSearch)

        return {
          ...display,
          posts: postsToShow,
          count: postsToShow.length,
          totalCount: s.posts.length,
        }
      })
      .filter(Boolean) as Array<{ label: string; id: string; posts: Post[]; count: number; totalCount: number; emptyMessage: string }>

    return dynamicTabs.sort((a, b) => {
      const ai = TAB_ORDER.indexOf(a.id)
      const bi = TAB_ORDER.indexOf(b.id)
      return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi)
    })
  }, [briefing, matchesSearch, readIds])

  useEffect(() => {
    if (availableTabs.length === 0) return
    if (!activeTab || !availableTabs.some((tab) => tab.id === activeTab)) {
      setActiveTab(availableTabs[0].id)
    }
  }, [activeTab, availableTabs])

  const tabIds = useMemo(() => availableTabs.map((t) => t.id), [availableTabs])

  const handleTabChange = useCallback((tab: string) => {
    setActiveTab(tab)
    trackEvent("tab_switch", { tab })
  }, [])

  const swipeRef = useSwipeTabs({
    tabIds,
    activeTab,
    onTabChange: handleTabChange,
    enabled: availableTabs.length > 1,
  })

  const isStale = minutesAgo > 480
  const staleHours = Math.floor(minutesAgo / 60)

  const relativeTime =
    minutesAgo < 1
      ? "just now"
      : minutesAgo < 60
        ? `${minutesAgo}m ago`
        : minutesAgo < 1440
          ? `${Math.floor(minutesAgo / 60)}h ago`
          : `${Math.floor(minutesAgo / 1440)}d ago`

  const totalPosts = briefing?.sections.reduce((sum, section) => sum + section.posts.length, 0) ?? 0
  const readMinutes = Math.ceil(totalPosts / 2)

  return (
    <div className="min-h-screen bg-background overflow-x-hidden">
      <header className="sticky top-0 z-50 bg-background/95 backdrop-blur-md border-b border-border">
        <div className="max-w-[598px] mx-auto">
          <div className="flex items-center justify-between px-3 sm:px-4 h-12 sm:h-[53px]">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0">
              <h1 className="text-lg sm:text-xl font-bold text-foreground tracking-tight whitespace-nowrap">𝕏 Brief</h1>
              {briefing && (
                <div className="flex items-center gap-1 sm:gap-1.5 min-w-0">
                  <span className="text-xs sm:text-[13px] text-muted-foreground whitespace-nowrap">~{readMinutes} min read</span>
                  <span className="text-xs sm:text-[13px] text-muted-foreground whitespace-nowrap">•</span>
                  <span className="text-xs sm:text-[13px] text-muted-foreground whitespace-nowrap">Updated {relativeTime}</span>
                  {isStale && (
                    <span
                      title="Data may be stale — last update was over 8 hours ago"
                      className="flex items-center gap-0.5 text-[11px] sm:text-[12px] text-amber-500 dark:text-amber-400 whitespace-nowrap"
                    >
                      <AlertTriangle className="h-2.5 w-2.5 sm:h-3 sm:w-3" />
                      Stale
                    </span>
                  )}
                </div>
              )}
            </div>

            <div className="flex items-center gap-0.5 sm:gap-1 flex-shrink-0">
              {briefing && (
                <button
                  onClick={() => void fetchBriefing(true)}
                  disabled={refreshing}
                  aria-label="Refresh briefing"
                  className="flex items-center justify-center h-7 w-7 sm:h-8 sm:w-8 rounded-full text-muted-foreground hover:bg-[rgba(29,155,240,0.1)] hover:text-[#1d9bf0] transition-colors disabled:opacity-50"
                >
                  <RefreshCw className={`h-3.5 w-3.5 sm:h-4 sm:w-4 ${refreshing ? "animate-spin" : ""}`} />
                </button>
              )}
              <ThemeToggle />
            </div>
          </div>
        </div>
      </header>

      {loading && <LoadingSkeleton />}

      {!loading && briefing && availableTabs.length > 0 && (
        <div className="w-full" style={{ overflowX: "clip" }}>
          <Tabs key={briefing.generated_at} value={activeTab} onValueChange={handleTabChange} className="w-full">
            <div className="sticky top-12 sm:top-[54px] z-40 bg-background/95 backdrop-blur-md border-b border-border">
              <div className="max-w-[598px] mx-auto overflow-x-auto scrollbar-hide">
                <div className="flex items-center">
                  <TabsList className="flex-1 h-auto p-0 bg-transparent rounded-none border-0 flex flex-nowrap">
                    {availableTabs.map((tab) => (
                      <TabsTrigger
                        key={tab.id}
                        value={tab.id}
                        className="relative flex-1 min-w-0 py-3 sm:py-4 px-2 sm:px-3 rounded-none border-0 bg-transparent text-sm sm:text-[15px] font-medium text-muted-foreground hover:bg-foreground/[0.03] data-[state=active]:text-foreground data-[state=active]:bg-transparent data-[state=active]:shadow-none data-[state=active]:font-bold transition-colors after:absolute after:bottom-0 after:left-1/2 after:-translate-x-1/2 after:w-12 sm:after:w-14 after:h-1 after:bg-[#1d9bf0] after:rounded-full after:opacity-0 data-[state=active]:after:opacity-100 after:transition-all after:duration-200"
                      >
                        <span className="text-sm sm:text-[15px] whitespace-nowrap">{tab.label}</span>
                      </TabsTrigger>
                    ))}
                  </TabsList>
                  <div className="flex-shrink-0 px-2">
                    {!searchExpanded ? (
                      <button
                        type="button"
                        onClick={() => setSearchExpanded(true)}
                        className="h-8 w-8 rounded-full border border-border text-muted-foreground hover:text-[#1d9bf0] hover:border-[#1d9bf0]/40 transition-colors flex items-center justify-center"
                        aria-label="Search posts"
                      >
                        <Search className="h-4 w-4" />
                      </button>
                  ) : (
                    <div className="flex items-center gap-2 w-full">
                      <div className="relative flex-1">
                        <Search className="h-4 w-4 text-muted-foreground absolute left-3 top-1/2 -translate-y-1/2" />
                        <input
                          type="text"
                          value={searchQuery}
                          onChange={(e) => setSearchQuery(e.target.value)}
                          placeholder="Search posts or @username"
                          className="w-full h-9 rounded-full border border-border bg-background pl-9 pr-9 text-sm focus:outline-none focus:ring-2 focus:ring-[#1d9bf0]/40"
                        />
                        {searchQuery && (
                          <button
                            type="button"
                            onClick={() => setSearchQuery("")}
                            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                            aria-label="Clear search"
                          >
                            <X className="h-4 w-4" />
                          </button>
                        )}
                      </div>
                      <button
                        type="button"
                        onClick={() => {
                          setSearchExpanded(false)
                          setSearchQuery("")
                        }}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        Cancel
                      </button>
                    </div>
                  )}
                  </div>
                </div>
              </div>
            </div>

            <div ref={swipeRef} className="max-w-[598px] w-full mx-auto md:border-x md:border-border min-h-screen overflow-hidden">
              {isStale && (
                <div className="px-4 py-3 border-b border-amber-500/30 bg-amber-500/10 text-amber-700 dark:text-amber-300 text-sm flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                  <span>Briefing is {staleHours} hours old — data may be stale</span>
                </div>
              )}

              {availableTabs.map((tab) => (
                <TabsContent
                  key={tab.id}
                  value={tab.id}
                  className="mt-0 focus-visible:outline-none focus-visible:ring-0 animate-fade-in"
                >
                  {tab.posts.length === 0 ? (
                    <div className="px-4 py-10 text-center text-sm text-muted-foreground">
                      {normalizedSearch ? "No posts match your search." : tab.emptyMessage}
                    </div>
                  ) : (
                    <div>
                      {tab.posts.map((post, index) => {
                        const pid = postIdFromUrl(post.postUrl)
                        return (
                          <div
                            key={pid || `${post.authorUsername}-${index}`}
                            data-post-id={pid || undefined}
                            ref={(el) => {
                              if (el && pid && observerRef.current) {
                                observerRef.current.observe(el)
                              }
                            }}
                            className="px-4 py-3 border-b border-border cursor-pointer hover:bg-foreground/[0.03] transition-colors overflow-hidden"
                            onClick={() => {
                              if (post.postUrl) {
                                trackEvent("post_click", { postId: pid || post.authorUsername })
                                window.open(post.postUrl, "_blank", "noopener,noreferrer")
                              }
                            }}
                          >
                            <PostCard
                              {...post}
                              onMediaOpen={(items, idx) => {
                                trackEvent("media_open", { postId: pid || post.authorUsername })
                                setMediaViewer({ items, index: idx })
                              }}
                            />
                          </div>
                        )
                      })}
                    </div>
                  )}
                </TabsContent>
              ))}
            </div>
          </Tabs>
        </div>
      )}

      {!loading && (!briefing || availableTabs.length === 0) && (
        <div className="max-w-[598px] mx-auto md:border-x md:border-border px-4 text-center py-20">
          <p className="text-[15px] text-muted-foreground">No briefing available yet.</p>
          <p className="text-[13px] text-muted-foreground mt-2">Run the pipeline to generate your first briefing.</p>
        </div>
      )}

      {!loading && briefing && (
        <div className="max-w-[598px] mx-auto md:border-x md:border-border px-4 py-8 border-t border-t-border">
          <p className="text-center text-[12px] text-muted-foreground/60">
            Scanned {formatStat(briefing.stats.posts_scanned)} posts from {briefing.stats.accounts_tracked} accounts
          </p>
          <p className="text-center text-[11px] text-muted-foreground/40 mt-1">
            Last updated {formatLastUpdated(briefing.generated_at)}
          </p>
        </div>
      )}

      {mediaViewer && (
        <MediaViewer
          items={mediaViewer.items}
          initialIndex={mediaViewer.index}
          onClose={() => setMediaViewer(null)}
          proxyUrl={(url) => {
            if (!url) return undefined
            if (url.includes("video.twimg.com") || url.includes("pbs.twimg.com")) {
              return `/api/media?url=${encodeURIComponent(url)}`
            }
            return url
          }}
        />
      )}
    </div>
  )
}
