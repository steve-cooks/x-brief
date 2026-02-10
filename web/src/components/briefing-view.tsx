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
      metrics?: { likes?: number; reposts?: number; views?: number }
      postUrl?: string
      timestamp?: string
      category?: string
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

export function BriefingView() {
  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch("/api/briefing")
      .then((r) => r.json())
      .then((data) => {
        setBriefing(data)
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [])

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
      <header className="sticky top-0 z-50 bg-white/95 dark:bg-black/95 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between px-4 py-3">
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                𝕏 Brief
              </h1>
            </div>
            {briefing && (
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center rounded-full bg-green-100 dark:bg-green-900/30 px-2.5 py-0.5 text-xs font-medium text-green-700 dark:text-green-400">
                  Live
                </span>
              </div>
            )}
          </div>
        </div>
      </header>

      {/* Loading state */}
      {loading && <LoadingSkeleton />}

      {/* Main content with tabs */}
      {!loading && briefing && briefing.sections.length > 0 && (
        <Tabs defaultValue={briefing.sections[0].title} className="w-full">
          {/* Tab navigation - X style */}
          <div className="sticky top-[57px] z-40 bg-white/95 dark:bg-black/95 backdrop-blur-md border-b border-gray-200 dark:border-gray-800">
            <div className="max-w-2xl mx-auto">
              <TabsList className="w-full h-auto p-0 bg-transparent rounded-none border-0 flex justify-start overflow-x-auto scrollbar-hide">
                {briefing.sections.map((section) => (
                  <TabsTrigger
                    key={section.title}
                    value={section.title}
                    className="relative flex-shrink-0 px-4 py-4 rounded-none border-0 bg-transparent text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-900 data-[state=active]:text-gray-900 data-[state=active]:bg-transparent dark:data-[state=active]:text-white data-[state=active]:shadow-none data-[state=active]:font-semibold after:absolute after:bottom-0 after:left-0 after:right-0 after:h-1 after:bg-blue-500 after:rounded-full after:opacity-0 data-[state=active]:after:opacity-100 after:transition-opacity"
                  >
                    <span className="flex items-center gap-2 text-[15px]">
                      <span>{section.emoji}</span>
                      <span className="hidden sm:inline">{section.title}</span>
                      <span className="sm:hidden">{section.title.split(' ')[0]}</span>
                    </span>
                  </TabsTrigger>
                ))}
              </TabsList>
            </div>
          </div>

          {/* Tab content */}
          <div className="max-w-2xl mx-auto">
            {briefing.sections.map((section) => (
              <TabsContent
                key={section.title}
                value={section.title}
                className="mt-0 focus-visible:outline-none focus-visible:ring-0"
              >
                {/* Section stats */}
                <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-900">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {section.posts.length} {section.posts.length === 1 ? "post" : "posts"}
                    {" · "}
                    {generatedDate}
                  </p>
                </div>

                {/* Posts feed */}
                <div className="divide-y divide-gray-100 dark:divide-gray-900">
                  {section.posts.map((post, index) => (
                    <div key={`${post.authorUsername}-${index}`} className="px-4 py-3">
                      <PostCard {...post} />
                    </div>
                  ))}
                </div>

                {/* Empty state */}
                {section.posts.length === 0 && (
                  <div className="text-center py-20">
                    <p className="text-base text-gray-600 dark:text-gray-400">
                      No posts in this section yet.
                    </p>
                  </div>
                )}
              </TabsContent>
            ))}
          </div>
        </Tabs>
      )}

      {/* Empty state - no briefing */}
      {!loading && !briefing && (
        <div className="max-w-2xl mx-auto px-4 text-center py-20">
          <p className="text-lg text-gray-600 dark:text-gray-400">
            No briefing available yet.
          </p>
          <p className="text-sm text-gray-500 dark:text-gray-500 mt-2">
            Run the pipeline to generate your first briefing.
          </p>
        </div>
      )}

      {/* Footer stats */}
      {!loading && briefing && (
        <div className="max-w-2xl mx-auto px-4 py-8 border-t border-gray-100 dark:border-gray-900">
          <div className="flex items-center justify-center gap-6 text-sm text-gray-600 dark:text-gray-400">
            <span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {formatStat(briefing.stats.posts_scanned)}
              </span>{" "}
              posts scanned
            </span>
            <span className="text-gray-300 dark:text-gray-700">·</span>
            <span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {briefing.stats.accounts_tracked}
              </span>{" "}
              accounts
            </span>
            <span className="text-gray-300 dark:text-gray-700">·</span>
            <span>
              <span className="font-semibold text-gray-900 dark:text-white">
                {briefing.stats.breakout_posts}
              </span>{" "}
              breakout
            </span>
          </div>
          <p className="text-center text-xs text-gray-500 dark:text-gray-500 mt-4">
            Generated at{" "}
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
