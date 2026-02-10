"use client"

import { useEffect, useState } from "react"
import { BriefingSection } from "@/components/x-brief/briefing-section"
import { Separator } from "@/components/ui/separator"
import { Skeleton } from "@/components/ui/skeleton"

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
    <div className="space-y-6 animate-pulse">
      <div className="space-y-3">
        <Skeleton className="h-6 w-40" />
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-32 w-full rounded-xl" />
        ))}
      </div>
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
        month: "long",
        day: "numeric",
        year: "numeric",
      })
    : ""

  return (
    <div className="min-h-screen bg-[#F5F5F7] dark:bg-black">
      {/* Header */}
      <header className="sticky top-0 z-50 bg-white/80 dark:bg-black/80 backdrop-blur-xl border-b border-black/5 dark:border-white/10">
        <div className="max-w-2xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-[22px] font-bold tracking-tight text-[#1D1D1F] dark:text-[#F5F5F7]">
                𝕏 Brief
              </h1>
              {briefing && (
                <p className="text-[13px] text-[#86868B] dark:text-[#98989D] mt-0.5">
                  {generatedDate} · Past {briefing.period_hours}h
                </p>
              )}
            </div>
            <div className="flex items-center gap-1.5">
              <span className="inline-flex items-center rounded-full bg-emerald-50 dark:bg-emerald-500/10 px-2.5 py-1 text-[11px] font-medium text-emerald-600 dark:text-emerald-400">
                Live
              </span>
            </div>
          </div>
        </div>
      </header>

      {/* Stats bar */}
      {briefing && (
        <div className="bg-white dark:bg-[#1C1C1E] border-b border-black/5 dark:border-white/5">
          <div className="max-w-2xl mx-auto px-4 py-3">
            <div className="flex items-center justify-between text-[13px]">
              <div className="flex items-center gap-4">
                <span className="text-[#86868B] dark:text-[#98989D]">
                  <span className="font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">
                    {formatStat(briefing.stats.posts_scanned)}
                  </span>{" "}
                  posts scanned
                </span>
                <span className="text-[#86868B] dark:text-[#98989D]">
                  <span className="font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">
                    {briefing.stats.accounts_tracked}
                  </span>{" "}
                  accounts
                </span>
                <span className="text-[#86868B] dark:text-[#98989D]">
                  <span className="font-semibold text-[#1D1D1F] dark:text-[#F5F5F7]">
                    {briefing.stats.interests_detected}
                  </span>{" "}
                  topics
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Content */}
      <main className="max-w-2xl mx-auto px-4 py-6 space-y-8">
        {loading ? (
          <LoadingSkeleton />
        ) : briefing ? (
          <>
            {briefing.sections.map((section, index) => (
              <div key={section.title}>
                <BriefingSection
                  title={section.title}
                  emoji={section.emoji}
                  posts={section.posts}
                />
                {index < briefing.sections.length - 1 && (
                  <Separator className="mt-8 opacity-50" />
                )}
              </div>
            ))}

            {/* Footer */}
            <div className="text-center py-8">
              <p className="text-[13px] text-[#86868B] dark:text-[#98989D]">
                Generated{" "}
                {new Date(briefing.generated_at).toLocaleTimeString("en-US", {
                  hour: "numeric",
                  minute: "2-digit",
                })}{" "}
                · {briefing.stats.breakout_posts} breakout posts detected
              </p>
              <p className="text-[11px] text-[#86868B]/60 dark:text-[#98989D]/60 mt-1">
                Powered by 𝕏 Brief ⚡
              </p>
            </div>
          </>
        ) : (
          <div className="text-center py-20">
            <p className="text-[17px] text-[#86868B] dark:text-[#98989D]">
              No briefing available yet.
            </p>
            <p className="text-[13px] text-[#86868B]/60 dark:text-[#98989D]/60 mt-2">
              Run the pipeline to generate your first briefing.
            </p>
          </div>
        )}
      </main>
    </div>
  )
}
