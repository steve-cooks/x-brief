"use client"

import { Heart, Repeat2, Eye, ExternalLink, Play } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { useState } from "react"

interface PostMetrics {
  likes?: number
  reposts?: number
  views?: number
  replies?: number
}

interface MediaItem {
  type: string // "photo", "video", "animated_gif"
  url?: string
  preview_image_url?: string
  video_url?: string
  alt_text?: string
}

interface PostCardProps {
  authorName: string
  authorUsername: string
  authorAvatarUrl?: string
  verified?: string | null // "blue", "business", "government"
  text: string
  media?: MediaItem[]
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
  media,
  metrics,
  postUrl,
  timestamp,
}: PostCardProps) {
  const [expandedMedia, setExpandedMedia] = useState<number | null>(null)
  
  const initials = authorName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)

  return (
    <article className="flex gap-3 group min-h-[44px]">
      {/* Avatar */}
      <div className="flex-shrink-0">
        <Avatar className="h-10 w-10 hover:opacity-90 transition-opacity cursor-pointer">
          {authorAvatarUrl && (
            <AvatarImage src={authorAvatarUrl} alt={authorName} />
          )}
          <AvatarFallback className="bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300 text-sm font-medium">
            {initials}
          </AvatarFallback>
        </Avatar>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Author info */}
        <div className="flex items-center gap-1 flex-wrap">
          <span className="font-bold text-[15px] text-gray-900 dark:text-white hover:underline cursor-pointer">
            {authorName}
          </span>

          {/* Verification badge */}
          {verified && (
            <svg
              viewBox="0 0 22 22"
              className="h-[18px] w-[18px] flex-shrink-0"
              aria-label="Verified account"
            >
              <path
                d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.855-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.69-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.636.433 1.221.878 1.69.47.446 1.055.752 1.69.883.635.13 1.294.083 1.902-.143.271.586.702 1.084 1.24 1.438.54.354 1.167.551 1.813.568.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.225 1.261.272 1.893.143.636-.131 1.222-.434 1.69-.88.445-.47.749-1.055.88-1.69.13-.634.085-1.293-.138-1.9.586-.273 1.084-.704 1.438-1.244.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z"
                fill={
                  verified === "business"
                    ? "#E8A12E"
                    : verified === "government"
                    ? "#829AAB"
                    : "#1D9BF0"
                }
              />
            </svg>
          )}

          <span className="text-[15px] text-gray-500 dark:text-gray-400">
            @{authorUsername}
          </span>

          {timestamp && (
            <>
              <span className="text-gray-500 dark:text-gray-400">·</span>
              <span className="text-[15px] text-gray-500 dark:text-gray-400">
                {timestamp}
              </span>
            </>
          )}
        </div>

        {/* Post text */}
        <div className="mt-0.5">
          <p className="text-[15px] leading-5 text-gray-900 dark:text-white whitespace-pre-wrap break-words">
            {text}
          </p>
        </div>

        {/* Media attachments */}
        {media && media.length > 0 && (
          <div className={`mt-3 ${media.length === 1 ? "" : "grid grid-cols-2 gap-0.5"} rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800`}>
            {media.map((item, index) => (
              <div
                key={index}
                className={`relative bg-gray-100 dark:bg-gray-900 ${
                  media.length === 1 ? "aspect-video max-h-[500px]" : "aspect-square"
                }`}
              >
                {/* Photo */}
                {item.type === "photo" && item.url && (
                  <img
                    src={item.url}
                    alt={item.alt_text || "Image"}
                    className="w-full h-full object-cover cursor-pointer hover:opacity-95 transition-opacity"
                    onClick={() => setExpandedMedia(expandedMedia === index ? null : index)}
                  />
                )}

                {/* Video — auto-play muted like X, with controls */}
                {item.type === "video" && item.video_url && (
                  <video
                    src={item.video_url}
                    poster={item.preview_image_url}
                    controls
                    autoPlay
                    muted
                    playsInline
                    // @ts-expect-error referrerPolicy is valid on video elements
                    referrerPolicy="no-referrer"
                    crossOrigin="anonymous"
                    className="w-full h-full object-cover rounded-inherit"
                    preload="auto"
                  />
                )}

                {/* Animated GIF */}
                {item.type === "animated_gif" && (
                  <div className="relative w-full h-full">
                    {item.video_url ? (
                      <video
                        src={item.video_url}
                        poster={item.preview_image_url}
                        loop
                        autoPlay
                        muted
                        playsInline
                        // @ts-expect-error referrerPolicy is valid on video elements
                        referrerPolicy="no-referrer"
                        crossOrigin="anonymous"
                        className="w-full h-full object-cover rounded-inherit"
                      />
                    ) : item.preview_image_url ? (
                      <img
                        src={item.preview_image_url}
                        alt="GIF"
                        className="w-full h-full object-cover"
                      />
                    ) : null}
                    <div className="absolute bottom-2 left-2 bg-gray-900/80 text-white text-xs font-semibold px-2 py-1 rounded">
                      GIF
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Engagement metrics */}
        {metrics && (
          <div className="mt-3 flex items-center gap-6">
            {/* Likes */}
            {metrics.likes !== undefined && metrics.likes > 0 && (
              <button
                className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 hover:text-pink-600 dark:hover:text-pink-500 group/like transition-colors -ml-2 p-2 rounded-full hover:bg-pink-50 dark:hover:bg-pink-950/30"
                onClick={(e) => e.stopPropagation()}
              >
                <Heart className="h-[18px] w-[18px] group-hover/like:fill-pink-600 dark:group-hover/like:fill-pink-500 transition-all" />
                <span className="text-[13px] font-normal">
                  {formatNumber(metrics.likes)}
                </span>
              </button>
            )}

            {/* Reposts */}
            {metrics.reposts !== undefined && metrics.reposts > 0 && (
              <button
                className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 hover:text-green-600 dark:hover:text-green-500 group/repost transition-colors p-2 rounded-full hover:bg-green-50 dark:hover:bg-green-950/30"
                onClick={(e) => e.stopPropagation()}
              >
                <Repeat2 className="h-[18px] w-[18px] transition-all" />
                <span className="text-[13px] font-normal">
                  {formatNumber(metrics.reposts)}
                </span>
              </button>
            )}

            {/* Views */}
            {metrics.views !== undefined && metrics.views > 0 && (
              <div className="flex items-center gap-1.5 text-gray-500 dark:text-gray-400 p-2">
                <Eye className="h-[18px] w-[18px]" />
                <span className="text-[13px] font-normal">
                  {formatNumber(metrics.views)}
                </span>
              </div>
            )}

            {/* External link */}
            {postUrl && (
              <a
                href={postUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto flex items-center gap-1 text-gray-500 dark:text-gray-400 hover:text-blue-600 dark:hover:text-blue-500 transition-colors p-2 rounded-full hover:bg-blue-50 dark:hover:bg-blue-950/30"
                onClick={(e) => e.stopPropagation()}
              >
                <ExternalLink className="h-[18px] w-[18px]" />
              </a>
            )}
          </div>
        )}
      </div>
    </article>
  )
}
