"use client"

import {
  Heart,
  Repeat2,
  Eye,
  ExternalLink,
  MessageCircle,
  Bookmark,
  Share,
} from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { useState, useMemo, Fragment, type ReactNode } from "react"

/** Proxy Twitter video/image URLs through our API to avoid referer blocking */
function proxyUrl(url: string | undefined | null): string | undefined {
  if (!url) return undefined
  if (
    url.includes("video.twimg.com") ||
    (url.includes("pbs.twimg.com") && url.includes("video"))
  ) {
    return `/api/media?url=${encodeURIComponent(url)}`
  }
  return url
}

// ---------------------------------------------------------------------------
// Text parsing — @mentions, #hashtags, URLs
// ---------------------------------------------------------------------------

interface TextSegment {
  type: "text" | "mention" | "hashtag" | "url"
  value: string
  href?: string
}

const SEGMENT_RE =
  /(@[A-Za-z0-9_]{1,15})|(#[A-Za-z0-9_\u00C0-\u024F]+)|(https?:\/\/[^\s<]+)/g

function parsePostText(raw: string): TextSegment[] {
  const segments: TextSegment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = SEGMENT_RE.exec(raw)) !== null) {
    // push preceding plain text
    if (match.index > lastIndex) {
      segments.push({ type: "text", value: raw.slice(lastIndex, match.index) })
    }

    if (match[1]) {
      // @mention
      const username = match[1].slice(1)
      segments.push({
        type: "mention",
        value: match[1],
        href: `https://x.com/${username}`,
      })
    } else if (match[2]) {
      // #hashtag
      const tag = match[2].slice(1)
      segments.push({
        type: "hashtag",
        value: match[2],
        href: `https://x.com/hashtag/${tag}`,
      })
    } else if (match[3]) {
      // URL
      const url = match[3].replace(/[.,;:!?)]+$/, "") // strip trailing punctuation
      const display = url
        .replace(/^https?:\/\//, "")
        .replace(/^www\./, "")
        .slice(0, 35)
      segments.push({
        type: "url",
        value: display.length < url.replace(/^https?:\/\//, "").length ? display + "…" : display,
        href: url,
      })
      // adjust lastIndex if we stripped chars
      const stripped = match[3].length - url.length
      if (stripped > 0) {
        SEGMENT_RE.lastIndex -= stripped
      }
    }

    lastIndex = SEGMENT_RE.lastIndex
  }

  // trailing plain text
  if (lastIndex < raw.length) {
    segments.push({ type: "text", value: raw.slice(lastIndex) })
  }

  return segments
}

function RichText({ text }: { text: string }) {
  const segments = useMemo(() => parsePostText(text), [text])
  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === "text") return <Fragment key={i}>{seg.value}</Fragment>
        return (
          <a
            key={i}
            href={seg.href}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#1d9bf0] hover:underline"
            onClick={(e) => e.stopPropagation()}
          >
            {seg.value}
          </a>
        )
      })}
    </>
  )
}

// ---------------------------------------------------------------------------
// X-style timestamp formatting
// ---------------------------------------------------------------------------

function formatTimestamp(createdAt?: string, fallback?: string): string {
  if (!createdAt) return fallback || ""
  const date = new Date(createdAt)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60_000)

  if (diffMin < 1) return "now"
  if (diffMin < 60) return `${diffMin}m`
  const diffH = Math.floor(diffMin / 60)
  if (diffH < 24) return `${diffH}h`

  // >24 h → "Feb 17" style
  return date.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

// ---------------------------------------------------------------------------
// Metrics formatting
// ---------------------------------------------------------------------------

interface PostMetrics {
  likes?: number
  reposts?: number
  views?: number
  replies?: number
}

function formatNumber(num: number): string {
  if (num >= 1_000_000) return `${(num / 1_000_000).toFixed(1)}M`
  if (num >= 1_000) return `${(num / 1_000).toFixed(1)}K`
  return num.toString()
}

// ---------------------------------------------------------------------------
// Media types
// ---------------------------------------------------------------------------

interface MediaItem {
  type: string // "photo", "video", "animated_gif"
  url?: string
  preview_image_url?: string
  video_url?: string
  alt_text?: string
}

// ---------------------------------------------------------------------------
// QuotedPost (nested tweet card)
// ---------------------------------------------------------------------------

interface QuotedPostData {
  authorName: string
  authorUsername: string
  authorAvatarUrl?: string
  verified?: string | null
  text: string
  media?: MediaItem[]
  metrics?: PostMetrics
  postUrl?: string
  timestamp?: string
  createdAt?: string
}

function QuotedPost({ post }: { post: QuotedPostData }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = post.text.length > 180
  const displayText = !expanded && isLong ? post.text.slice(0, 180) + "…" : post.text

  return (
    <div
      className="mt-3 border border-gray-200 dark:border-gray-800 rounded-2xl overflow-hidden cursor-pointer hover:bg-gray-50/50 dark:hover:bg-gray-900/30 transition-colors"
      onClick={(e) => {
        e.stopPropagation()
        if (post.postUrl) window.open(post.postUrl, "_blank", "noopener,noreferrer")
      }}
    >
      <div className="px-3 py-2.5">
        {/* Author row */}
        <div className="flex items-center gap-1.5">
          <Avatar className="h-5 w-5">
            {post.authorAvatarUrl && (
              <AvatarImage src={post.authorAvatarUrl} alt={post.authorName} />
            )}
            <AvatarFallback className="bg-gray-200 dark:bg-gray-800 text-[10px] font-medium">
              {post.authorName?.[0]?.toUpperCase() || "?"}
            </AvatarFallback>
          </Avatar>
          <span className="font-bold text-[13px] text-gray-900 dark:text-white leading-4">
            {post.authorName}
          </span>
          {post.verified && <VerificationBadge type={post.verified} size={14} />}
          <span className="text-[13px] text-gray-500 dark:text-gray-500 leading-4">
            @{post.authorUsername}
          </span>
          {(post.createdAt || post.timestamp) && (
            <>
              <span className="text-gray-500 dark:text-gray-500 text-[13px]">·</span>
              <span className="text-[13px] text-gray-500 dark:text-gray-500 leading-4">
                {formatTimestamp(post.createdAt, post.timestamp)}
              </span>
            </>
          )}
        </div>

        {/* Text */}
        <p className="mt-1 text-[15px] leading-5 text-gray-900 dark:text-white whitespace-pre-wrap break-words">
          <RichText text={displayText} />
          {isLong && !expanded && (
            <button
              className="text-[#1d9bf0] hover:underline ml-1 text-[15px]"
              onClick={(e) => {
                e.stopPropagation()
                setExpanded(true)
              }}
            >
              Show more
            </button>
          )}
        </p>
      </div>

      {/* Quoted media (single image preview) */}
      {post.media && post.media.length > 0 && post.media[0].type === "photo" && post.media[0].url && (
        <img
          src={post.media[0].url}
          alt={post.media[0].alt_text || "Image"}
          className="w-full max-h-[200px] object-cover border-t border-gray-200 dark:border-gray-800"
        />
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Verification badge
// ---------------------------------------------------------------------------

function VerificationBadge({ type, size = 18 }: { type: string; size?: number }) {
  return (
    <svg
      viewBox="0 0 22 22"
      style={{ height: size, width: size }}
      className="flex-shrink-0"
      aria-label="Verified account"
    >
      <path
        d="M20.396 11c-.018-.646-.215-1.275-.57-1.816-.354-.54-.852-.972-1.438-1.246.223-.607.27-1.264.14-1.897-.131-.634-.437-1.218-.882-1.687-.47-.445-1.053-.75-1.687-.882-.633-.13-1.29-.083-1.897.14-.273-.587-.704-1.086-1.245-1.44S11.647 1.62 11 1.604c-.646.017-1.273.213-1.813.568s-.969.855-1.24 1.44c-.608-.223-1.267-.272-1.902-.14-.635.13-1.22.436-1.69.882-.445.47-.749 1.055-.878 1.69-.13.633-.08 1.29.144 1.896-.587.274-1.087.705-1.443 1.245-.356.54-.555 1.17-.574 1.817.02.647.218 1.276.574 1.817.356.54.856.972 1.443 1.245-.224.606-.274 1.263-.144 1.896.13.636.433 1.221.878 1.69.47.446 1.055.752 1.69.883.635.13 1.294.083 1.902-.143.271.586.702 1.084 1.24 1.438.54.354 1.167.551 1.813.568.647-.016 1.276-.213 1.817-.567s.972-.854 1.245-1.44c.604.225 1.261.272 1.893.143.636-.131 1.222-.434 1.69-.88.445-.47.749-1.055.88-1.69.13-.634.085-1.293-.138-1.9.586-.273 1.084-.704 1.438-1.244.354-.54.551-1.17.569-1.816zM9.662 14.85l-3.429-3.428 1.293-1.302 2.072 2.072 4.4-4.794 1.347 1.246z"
        fill={
          type === "business"
            ? "#E8A12E"
            : type === "government"
            ? "#829AAB"
            : "#1D9BF0"
        }
      />
    </svg>
  )
}

// ---------------------------------------------------------------------------
// PostCard (main component)
// ---------------------------------------------------------------------------

interface PostCardProps {
  authorName: string
  authorUsername: string
  authorAvatarUrl?: string
  verified?: string | null
  text: string
  media?: MediaItem[]
  metrics?: PostMetrics
  postUrl?: string
  timestamp?: string
  createdAt?: string
  category?: string
  quotedPost?: QuotedPostData
}

const TRUNCATE_LENGTH = 280

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
  createdAt,
  quotedPost,
}: PostCardProps) {
  const [expandedMedia, setExpandedMedia] = useState<number | null>(null)
  const [textExpanded, setTextExpanded] = useState(false)

  const isLongText = text.length > TRUNCATE_LENGTH
  const displayText =
    !textExpanded && isLongText ? text.slice(0, TRUNCATE_LENGTH) + "…" : text

  const initials = authorName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)

  const displayTime = formatTimestamp(createdAt, timestamp)

  return (
    <article className="flex gap-3 group min-h-[44px]">
      {/* Avatar */}
      <div className="flex-shrink-0">
        <Avatar className="h-10 w-10">
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
        {/* Author info — single line like X */}
        <div className="flex items-center gap-1 min-w-0">
          <span className="font-bold text-[15px] leading-5 text-gray-900 dark:text-white truncate">
            {authorName}
          </span>

          {verified && <VerificationBadge type={verified} />}

          <span className="text-[15px] leading-5 text-gray-500 dark:text-gray-500 truncate flex-shrink-[2]">
            @{authorUsername}
          </span>

          {displayTime && (
            <>
              <span className="text-gray-500 dark:text-gray-500 flex-shrink-0">·</span>
              <span className="text-[15px] leading-5 text-gray-500 dark:text-gray-500 flex-shrink-0">
                {displayTime}
              </span>
            </>
          )}
        </div>

        {/* Post text with rich parsing */}
        <div className="mt-0.5">
          <p className="text-[15px] leading-5 text-gray-900 dark:text-white whitespace-pre-wrap break-words">
            <RichText text={displayText} />
            {isLongText && !textExpanded && (
              <button
                className="text-[#1d9bf0] hover:underline ml-1 text-[15px]"
                onClick={(e) => {
                  e.stopPropagation()
                  setTextExpanded(true)
                }}
              >
                Show more
              </button>
            )}
          </p>
        </div>

        {/* Quoted post */}
        {quotedPost && <QuotedPost post={quotedPost} />}

        {/* Media attachments */}
        {media && media.length > 0 && (
          <div
            className={`mt-3 ${
              media.length === 1 ? "" : "grid grid-cols-2 gap-0.5"
            } rounded-2xl overflow-hidden border border-gray-200 dark:border-gray-800`}
          >
            {media.map((item, index) => (
              <div
                key={index}
                className={`relative bg-gray-100 dark:bg-gray-900 ${
                  media.length === 1
                    ? "aspect-video max-h-[500px]"
                    : "aspect-square"
                }`}
              >
                {item.type === "photo" && item.url && (
                  <img
                    src={item.url}
                    alt={item.alt_text || "Image"}
                    className="w-full h-full object-cover"
                    onClick={(e) => {
                      e.stopPropagation()
                      setExpandedMedia(expandedMedia === index ? null : index)
                    }}
                  />
                )}

                {item.type === "video" && item.video_url && (
                  <video
                    src={proxyUrl(item.video_url)}
                    poster={proxyUrl(item.preview_image_url)}
                    controls
                    autoPlay
                    muted
                    playsInline
                    className="w-full h-full object-cover rounded-inherit"
                    preload="auto"
                    onClick={(e) => e.stopPropagation()}
                  />
                )}

                {item.type === "animated_gif" && (
                  <div className="relative w-full h-full">
                    {item.video_url ? (
                      <video
                        src={proxyUrl(item.video_url)}
                        poster={proxyUrl(item.preview_image_url)}
                        loop
                        autoPlay
                        muted
                        playsInline
                        className="w-full h-full object-cover rounded-inherit"
                        onClick={(e) => e.stopPropagation()}
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

        {/* Engagement metrics — X layout: replies · reposts · likes · views · bookmark · share · external */}
        {metrics && (
          <div className="mt-1 flex items-center justify-between max-w-[425px] -ml-2">
            {/* Replies */}
            <div className="flex items-center gap-1 text-gray-500 dark:text-gray-500 p-2 min-w-[40px]">
              <MessageCircle className="h-[18px] w-[18px]" />
              {(metrics.replies ?? 0) > 0 && (
                <span className="text-[13px] leading-4">
                  {formatNumber(metrics.replies!)}
                </span>
              )}
            </div>

            {/* Reposts */}
            <div className="flex items-center gap-1 text-gray-500 dark:text-gray-500 p-2 min-w-[40px]">
              <Repeat2 className="h-[18px] w-[18px]" />
              {(metrics.reposts ?? 0) > 0 && (
                <span className="text-[13px] leading-4">
                  {formatNumber(metrics.reposts!)}
                </span>
              )}
            </div>

            {/* Likes */}
            <div className="flex items-center gap-1 text-gray-500 dark:text-gray-500 p-2 min-w-[40px]">
              <Heart className="h-[18px] w-[18px]" />
              {(metrics.likes ?? 0) > 0 && (
                <span className="text-[13px] leading-4">
                  {formatNumber(metrics.likes!)}
                </span>
              )}
            </div>

            {/* Views */}
            <div className="flex items-center gap-1 text-gray-500 dark:text-gray-500 p-2 min-w-[40px]">
              <Eye className="h-[18px] w-[18px]" />
              {(metrics.views ?? 0) > 0 && (
                <span className="text-[13px] leading-4">
                  {formatNumber(metrics.views!)}
                </span>
              )}
            </div>

            {/* Bookmark (decorative) */}
            <div className="flex items-center text-gray-500 dark:text-gray-500 p-2">
              <Bookmark className="h-[18px] w-[18px]" />
            </div>

            {/* Share (decorative) */}
            <div className="flex items-center text-gray-500 dark:text-gray-500 p-2">
              <Share className="h-[18px] w-[18px]" />
            </div>

            {/* External link */}
            {postUrl && (
              <a
                href={postUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center text-gray-500 dark:text-gray-500 hover:text-[#1d9bf0] transition-colors p-2"
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
