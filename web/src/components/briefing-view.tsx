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
          <div className="flex items-center justify-between px-4 h-[57px]">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white tracking-tight">
                𝕏 Brief
              </h1>
              {briefing && (
                <div className="hidden sm:flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                  <span className="w-1 h-1 rounded-full bg-gray-400 dark:bg-gray-600"></span>
                  <span>{generatedDate}</span>
                </div>
              )}
            </div>
            {briefing && (
              <div className="flex items-center gap-2">
                <span className="relative flex h-2 w-2">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </span>
                <span className="text-sm font-medium text-green-600 dark:text-green-500">
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
            <div className="max-w-2xl mx-auto overflow-x-auto scrollbar-hide">
              <TabsList className="w-full h-auto p-0 bg-transparent rounded-none border-0 inline-flex justify-start min-w-full">
                {briefing.sections.map((section) => (
                  <TabsTrigger
                    key={section.title}
                    value={section.title}
                    className="relative flex-shrink-0 px-4 py-4 rounded-none border-0 bg-transparent text-gray-600 dark:text-gray-400 hover:bg-gray-50/50 dark:hover:bg-gray-900/50 data-[state=active]:text-gray-900 data-[state=active]:bg-transparent dark:data-[state=active]:text-white data-[state=active]:shadow-none data-[state=active]:font-semibold transition-colors after:absolute after:bottom-0 after:left-0 after:right-0 after:h-[3px] after:bg-blue-500 after:rounded-full after:opacity-0 data-[state=active]:after:opacity-100 after:transition-all after:duration-200"
                  >
                    <span className="flex items-center gap-2 text-[15px] whitespace-nowrap">
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
                className="mt-0 focus-visible:outline-none focus-visible:ring-0 animate-fade-in"
              >
                {/* Section stats */}
                <div className="px-4 py-3 bg-white dark:bg-black border-b border-gray-100 dark:border-gray-900">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="font-semibold text-gray-900 dark:text-white">
                      {section.posts.length}
                    </span>
                    <span className="text-gray-600 dark:text-gray-400">
                      {section.posts.length === 1 ? "post" : "posts"}
                    </span>
                    <span className="text-gray-400 dark:text-gray-600">·</span>
                    <span className="text-gray-600 dark:text-gray-400 sm:hidden">
                      Past {briefing.period_hours}h
                    </span>
                    <span className="text-gray-600 dark:text-gray-400 hidden sm:inline">
                      {generatedDate}
                    </span>
                  </div>
                </div>

                {/* Posts feed */}
                <div className="divide-y divide-gray-100 dark:divide-gray-900">
                  {section.posts.map((post, index) => (
                    <div
                      key={`${post.authorUsername}-${index}`}
                      className="px-4 py-3 hover:bg-gray-50/50 dark:hover:bg-gray-900/30 transition-colors cursor-pointer"
                    >
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
          <div className="flex flex-col sm:flex-row items-center justify-center gap-4 sm:gap-6 text-sm">
            <div className="flex items-center gap-6">
              <div className="text-center sm:text-left">
                <div className="font-semibold text-gray-900 dark:text-white text-lg">
                  {formatStat(briefing.stats.posts_scanned)}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  posts scanned
                </div>
              </div>
              <div className="w-px h-10 bg-gray-200 dark:bg-gray-800"></div>
              <div className="text-center sm:text-left">
                <div className="font-semibold text-gray-900 dark:text-white text-lg">
                  {briefing.stats.accounts_tracked}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  accounts
                </div>
              </div>
              <div className="w-px h-10 bg-gray-200 dark:bg-gray-800"></div>
              <div className="text-center sm:text-left">
                <div className="font-semibold text-gray-900 dark:text-white text-lg">
                  {briefing.stats.breakout_posts}
                </div>
                <div className="text-xs text-gray-600 dark:text-gray-400">
                  breakout
                </div>
              </div>
            </div>
          </div>
          <p className="text-center text-xs text-gray-500 dark:text-gray-500 mt-6">
            Generated at{" "}
            {new Date(briefing.generated_at).toLocaleTimeString("en-US", {
              hour: "numeric",
              minute: "2-digit",
            })}{" "}
            · Powered by 𝕏 Brief
          </p>
        </div>
      )}
    </div>
  )
}
