"use client"

import { Heart, Repeat2, Eye, ExternalLink } from "lucide-react"
import { Card, CardContent } from "@/components/ui/card"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"

interface PostMetrics {
  likes?: number
  reposts?: number
  views?: number
  replies?: number
}

interface PostCardProps {
  authorName: string
  authorUsername: string
  authorAvatarUrl?: string
  verified?: string | null  // "blue", "business", "government"
  text: string
  metrics?: PostMetrics
  postUrl?: string
  timestamp?: string
  category?: string
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`
  return num.toString()
}

export function PostCard({
  authorName,
  authorUsername,
  authorAvatarUrl,
  verified,
  text,
  metrics,
  postUrl,
  timestamp,
  category,
}: PostCardProps) {
  const initials = authorName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)

  return (
    <Card className="group relative overflow-hidden border-0 bg-white/80 backdrop-blur-sm shadow-[0_1px_3px_rgba(0,0,0,0.08)] hover:shadow-[0_4px_12px_rgba(0,0,0,0.10)] transition-all duration-300 dark:bg-[#1C1C1E]/80 dark:shadow-[0_1px_3px_rgba(0,0,0,0.3)]">
      <CardContent className="p-4 sm:p-5">
        {/* Author row */}
        <div className="flex items-start gap-3">
          <Avatar className="h-10 w-10 shrink-0 ring-1 ring-black/5 dark:ring-white/10">
            {authorAvatarUrl && <AvatarImage src={authorAvatarUrl} alt={authorName} />}
            <AvatarFallback className="text-xs font-medium bg-gradient-to-br from-blue-500 to-blue-600 text-white">
              {initials}
            </AvatarFallback>
          </Avatar>

          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-[15px] text-[#1D1D1F] dark:text-[#F5F5F7] truncate">
                {authorName}
              </span>
              {verified && (
                <svg viewBox="0 0 22 22" className="h-4 w-4 shrink-0" aria-label="Verified account">
                  <path
                    d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.855-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.69-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.636.433 1.221.878 1.69.47.446 1.055.752 1.69.883.635.13 1.294.083 1.902-.143.271.586.702 1.084 1.24 1.438.54.354 1.167.551 1.813.568.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.225 1.261.272 1.893.143.636-.131 1.222-.434 1.69-.88.445-.47.749-1.055.88-1.69.13-.634.085-1.293-.138-1.9.586-.273 1.084-.704 1.438-1.244.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z"
                    fill={verified === "business" ? "#E8A12E" : verified === "government" ? "#829AAB" : "#1D9BF0"}
                  />
                </svg>
              )}
              <span className="text-[13px] text-[#86868B] dark:text-[#98989D] shrink-0">
                @{authorUsername}
              </span>
              {timestamp && (
                <>
                  <span className="text-[#86868B] dark:text-[#98989D]">·</span>
                  <span className="text-[13px] text-[#86868B] dark:text-[#98989D] shrink-0">
                    {timestamp}
                  </span>
                </>
              )}
            </div>

            {/* Post text */}
            <p className="mt-1.5 text-[15px] leading-[1.5] text-[#1D1D1F] dark:text-[#E5E5E7] whitespace-pre-wrap break-words">
              {text}
            </p>

            {/* Metrics row */}
            {metrics && (
              <div className="mt-3 flex items-center gap-4 text-[13px] text-[#86868B] dark:text-[#98989D]">
                {metrics.likes !== undefined && metrics.likes > 0 && (
                  <span className="flex items-center gap-1 hover:text-rose-500 transition-colors">
                    <Heart className="h-3.5 w-3.5" />
                    {formatNumber(metrics.likes)}
                  </span>
                )}
                {metrics.reposts !== undefined && metrics.reposts > 0 && (
                  <span className="flex items-center gap-1 hover:text-emerald-500 transition-colors">
                    <Repeat2 className="h-3.5 w-3.5" />
                    {formatNumber(metrics.reposts)}
                  </span>
                )}
                {metrics.views !== undefined && metrics.views > 0 && (
                  <span className="flex items-center gap-1">
                    <Eye className="h-3.5 w-3.5" />
                    {formatNumber(metrics.views)}
                  </span>
                )}
                {postUrl && (
                  <a
                    href={postUrl}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="ml-auto flex items-center gap-1 text-[#007AFF] hover:text-[#0056B3] transition-colors"
                  >
                    <ExternalLink className="h-3.5 w-3.5" />
                    <span className="hidden sm:inline">View</span>
                  </a>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Category badge */}
        {category && (
          <div className="absolute top-3 right-3">
            <span className="inline-flex items-center rounded-full bg-[#F5F5F7] dark:bg-[#2C2C2E] px-2.5 py-0.5 text-[11px] font-medium text-[#86868B] dark:text-[#98989D]">
              {category}
            </span>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
