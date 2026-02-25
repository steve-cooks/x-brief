"use client"

import {
  Heart,
  Repeat2,
  Eye,
  ExternalLink,
  MessageCircle,
  Bookmark,
  Share,
  Play,
} from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { useState, useRef, useMemo, Fragment, type ReactNode } from "react"

/** Proxy Twitter media URLs through our API to avoid referer blocking */
function proxyUrl(url: string | undefined | null): string | undefined {
  if (!url) return undefined
  if (
    url.includes("video.twimg.com") ||
    url.includes("pbs.twimg.com")
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
    if (match.index > lastIndex) {
      segments.push({ type: "text", value: raw.slice(lastIndex, match.index) })
    }

    if (match[1]) {
      const username = match[1].slice(1)
      segments.push({
        type: "mention",
        value: match[1],
        href: `https://x.com/${username}`,
      })
    } else if (match[2]) {
      const tag = match[2].slice(1)
      segments.push({
        type: "hashtag",
        value: match[2],
        href: `https://x.com/hashtag/${tag}`,
      })
    } else if (match[3]) {
      const url = match[3].replace(/[.,;:!?)]+$/, "")
      const display = url
        .replace(/^https?:\/\//, "")
        .replace(/^www\./, "")
        .slice(0, 35)
      segments.push({
        type: "url",
        value:
          display.length < url.replace(/^https?:\/\//, "").length
            ? display + "…"
            : display,
        href: url,
      })
      const stripped = match[3].length - url.length
      if (stripped > 0) {
        SEGMENT_RE.lastIndex -= stripped
      }
    }

    lastIndex = SEGMENT_RE.lastIndex
  }

  if (lastIndex < raw.length) {
    segments.push({ type: "text", value: raw.slice(lastIndex) })
  }

  return segments
}

function RichText({
  text,
  hideUrls = false,
}: {
  text: string
  hideUrls?: boolean
}) {
  const segments = useMemo(() => parsePostText(text), [text])
  return (
    <>
      {segments.map((seg, i) => {
        if (seg.type === "text")
          return <Fragment key={i}>{seg.value}</Fragment>
        if (seg.type === "url" && hideUrls) return null
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
  bookmarks?: number
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
// LinkCard data (from enrichment)
// ---------------------------------------------------------------------------

interface LinkCardData {
  title: string
  description?: string
  thumbnail?: string | null
  domain?: string
  url?: string
}

// ---------------------------------------------------------------------------
// LinkCard — X-style link preview (enriched version with thumbnail)
// ---------------------------------------------------------------------------

function EnrichedLinkCard({ card }: { card: LinkCardData }) {
  const domain = card.domain || ""

  return (
    <a
      href={card.url}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-3 block border border-border rounded-2xl overflow-hidden transition-colors hover:bg-foreground/[0.03] bg-background max-w-full"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Large thumbnail on top */}
      {card.thumbnail && (
        <div className="relative aspect-[1.91/1] bg-accent overflow-hidden">
          <img
            src={proxyUrl(card.thumbnail)}
            alt={card.title}
            className="w-full h-full object-cover"
          />
        </div>
      )}
      {/* Title + domain below */}
      <div className="px-3 py-2.5">
        <div className="text-[13px] text-muted-foreground truncate">
          {domain}
        </div>
        <div className="text-[15px] text-foreground leading-5 line-clamp-2 mt-0.5">
          {card.title}
        </div>
        {card.description && !card.thumbnail && (
          <div className="text-[13px] text-muted-foreground line-clamp-2 mt-0.5">
            {card.description}
          </div>
        )}
      </div>
    </a>
  )
}

/** Fallback: simple URL-only link card (no enrichment data) */
function SimpleLinkCard({ url }: { url: string }) {
  const domain = (() => {
    try {
      const u = new URL(url)
      return u.hostname.replace(/^www\./, "")
    } catch {
      return url.replace(/^https?:\/\//, "").replace(/^www\./, "").split("/")[0]
    }
  })()

  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-3 flex items-center gap-2 border border-border rounded-2xl px-3 py-2.5 transition-colors hover:bg-foreground/[0.03] bg-background max-w-full overflow-hidden"
      onClick={(e) => e.stopPropagation()}
    >
      <span className="text-[13px] text-muted-foreground truncate">
        {domain}
      </span>
      <ExternalLink className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
    </a>
  )
}

// ---------------------------------------------------------------------------
// Media Grid — handles 1-4 images in X's layout
// ---------------------------------------------------------------------------

function MediaGrid({
  media,
  onImageClick,
}: {
  media: MediaItem[]
  onImageClick?: (url: string) => void
}) {
  const count = media.length

  if (count === 0) return null

  if (count === 1) {
    return (
      <SingleMedia item={media[0]} onImageClick={onImageClick} />
    )
  }

  if (count === 2) {
    return (
      <div className="mt-3 w-full max-w-full grid grid-cols-2 gap-0.5 rounded-2xl overflow-hidden border border-border">
        {media.map((item, i) => (
          <div key={i} className="relative aspect-square bg-accent overflow-hidden">
            <MediaContent item={item} fill onImageClick={onImageClick} />
          </div>
        ))}
      </div>
    )
  }

  if (count === 3) {
    return (
      <div className="mt-3 w-full max-w-full grid grid-cols-2 gap-0.5 rounded-2xl overflow-hidden border border-border" style={{ aspectRatio: "16/9" }}>
        <div className="relative row-span-2 bg-accent overflow-hidden">
          <MediaContent item={media[0]} fill onImageClick={onImageClick} />
        </div>
        <div className="relative bg-accent overflow-hidden">
          <MediaContent item={media[1]} fill onImageClick={onImageClick} />
        </div>
        <div className="relative bg-accent overflow-hidden">
          <MediaContent item={media[2]} fill onImageClick={onImageClick} />
        </div>
      </div>
    )
  }

  // 4+
  return (
    <div className="mt-3 w-full max-w-full grid grid-cols-2 grid-rows-2 gap-0.5 rounded-2xl overflow-hidden border border-border" style={{ aspectRatio: "16/9" }}>
      {media.slice(0, 4).map((item, i) => (
        <div key={i} className="relative bg-accent overflow-hidden">
          <MediaContent item={item} fill onImageClick={onImageClick} />
        </div>
      ))}
    </div>
  )
}

/** Single media item (full width) */
function SingleMedia({
  item,
  onImageClick,
}: {
  item: MediaItem
  onImageClick?: (url: string) => void
}) {
  if (item.type === "photo" && item.url) {
    return (
      <div className="mt-3 w-full max-w-full rounded-2xl overflow-hidden border border-border">
        <img
          src={proxyUrl(item.url)}
          alt={item.alt_text || "Image"}
          className="w-full max-h-[510px] object-cover cursor-pointer"
          onClick={(e) => {
            e.stopPropagation()
            onImageClick?.(item.url!)
          }}
        />
      </div>
    )
  }

  if (item.type === "video") {
    return (
      <div className="mt-3 w-full max-w-full rounded-2xl overflow-hidden border border-border">
        <VideoPlayer item={item} />
      </div>
    )
  }

  if (item.type === "animated_gif") {
    return (
      <div className="mt-3 w-full max-w-full rounded-2xl overflow-hidden border border-border">
        <GifPlayer item={item} />
      </div>
    )
  }

  return null
}

/** Renders a media item inside a grid cell */
function MediaContent({
  item,
  fill,
  onImageClick,
}: {
  item: MediaItem
  fill?: boolean
  onImageClick?: (url: string) => void
}) {
  if (item.type === "photo" && item.url) {
    return (
      <img
        src={proxyUrl(item.url)}
        alt={item.alt_text || "Image"}
        className="w-full h-full object-cover cursor-pointer"
        onClick={(e) => {
          e.stopPropagation()
          onImageClick?.(item.url!)
        }}
      />
    )
  }

  if (item.type === "video") {
    return <VideoPlayer item={item} fill />
  }

  if (item.type === "animated_gif") {
    return <GifPlayer item={item} fill />
  }

  return null
}

/** Video player with poster + play button overlay */
function VideoPlayer({ item, fill }: { item: MediaItem; fill?: boolean }) {
  const [playing, setPlaying] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  const posterUrl = proxyUrl(item.preview_image_url || item.url)
  const videoUrl = proxyUrl(item.video_url)

  if (!videoUrl) {
    // No video URL — show poster only
    return posterUrl ? (
      <img
        src={posterUrl}
        alt="Video"
        className={fill ? "w-full h-full object-cover" : "w-full max-h-[510px] object-cover"}
      />
    ) : null
  }

  if (!playing) {
    return (
      <div
        className={`relative cursor-pointer ${fill ? "w-full h-full" : ""}`}
        onClick={(e) => {
          e.stopPropagation()
          setPlaying(true)
        }}
      >
        {posterUrl && (
          <img
            src={posterUrl}
            alt="Video poster"
            className={
              fill
                ? "w-full h-full object-cover"
                : "w-full max-h-[510px] object-cover"
            }
          />
        )}
        {/* Play button overlay */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="flex items-center justify-center w-[60px] h-[60px] rounded-full bg-[#1d9bf0] shadow-lg">
            <Play className="h-7 w-7 text-white fill-white ml-1" />
          </div>
        </div>
      </div>
    )
  }

  return (
    <video
      ref={videoRef}
      src={videoUrl}
      poster={posterUrl}
      controls
      autoPlay
      playsInline
      className={
        fill
          ? "w-full h-full object-cover"
          : "w-full max-h-[510px] object-cover"
      }
      onClick={(e) => e.stopPropagation()}
    />
  )
}

/** GIF player — auto-loops, muted, no controls, with "GIF" badge */
function GifPlayer({ item, fill }: { item: MediaItem; fill?: boolean }) {
  const videoUrl = proxyUrl(item.video_url)
  const posterUrl = proxyUrl(item.preview_image_url || item.url)

  return (
    <div className={`relative ${fill ? "w-full h-full" : ""}`}>
      {videoUrl ? (
        <video
          src={videoUrl}
          poster={posterUrl}
          loop
          autoPlay
          muted
          playsInline
          className={
            fill
              ? "w-full h-full object-cover"
              : "w-full max-h-[510px] object-cover"
          }
          onClick={(e) => e.stopPropagation()}
        />
      ) : posterUrl ? (
        <img
          src={posterUrl}
          alt="GIF"
          className={
            fill
              ? "w-full h-full object-cover"
              : "w-full max-h-[510px] object-cover"
          }
        />
      ) : null}
      {/* GIF badge */}
      <div className="absolute bottom-2 left-2 bg-foreground/80 text-background text-xs font-bold px-1.5 py-0.5 rounded">
        GIF
      </div>
    </div>
  )
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
  linkCard?: LinkCardData | null
}

function QuotedPost({ post }: { post: QuotedPostData }) {
  const [expanded, setExpanded] = useState(false)
  const isLong = post.text.length > 180
  const displayText =
    !expanded && isLong ? post.text.slice(0, 180) + "…" : post.text

  return (
    <div
      className="mt-3 border border-border rounded-2xl overflow-hidden cursor-pointer hover:bg-foreground/[0.03] transition-colors max-w-full"
      onClick={(e) => {
        e.stopPropagation()
        if (post.postUrl)
          window.open(post.postUrl, "_blank", "noopener,noreferrer")
      }}
    >
      <div className="px-3 py-2.5">
        {/* Author row */}
        <div className="flex items-center gap-1.5">
          <Avatar className="h-5 w-5">
            {post.authorAvatarUrl && (
              <AvatarImage
                src={proxyUrl(post.authorAvatarUrl)}
                alt={post.authorName}
              />
            )}
            <AvatarFallback className="bg-accent text-[10px] font-medium">
              {post.authorName?.[0]?.toUpperCase() || "?"}
            </AvatarFallback>
          </Avatar>
          <span className="font-bold text-[13px] text-foreground leading-4 truncate">
            {post.authorName}
          </span>
          {post.verified && (
            <VerificationBadge type={post.verified} size={14} />
          )}
          <span className="text-[13px] text-muted-foreground leading-4 truncate">
            @{post.authorUsername}
          </span>
          {(post.createdAt || post.timestamp) && (
            <>
              <span className="text-muted-foreground text-[13px]">·</span>
              <span className="text-[13px] text-muted-foreground leading-4">
                {formatTimestamp(post.createdAt, post.timestamp)}
              </span>
            </>
          )}
        </div>

        {/* Text */}
        <p className="mt-1 text-[15px] leading-5 text-foreground whitespace-pre-wrap break-words">
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

      {/* Quoted media (single image preview only) */}
      {post.media &&
        post.media.length > 0 &&
        post.media[0].type === "photo" &&
        post.media[0].url && (
          <img
            src={proxyUrl(post.media[0].url)}
            alt={post.media[0].alt_text || "Image"}
            className="w-full max-h-[200px] object-cover border-t border-border"
          />
        )}

      {/* Quoted link card (for articles/links) */}
      {post.linkCard && post.linkCard.url && (
        <div className="mx-3 mb-2.5 border border-border rounded-xl overflow-hidden">
          {post.linkCard.thumbnail && (
            <img
              src={proxyUrl(post.linkCard.thumbnail)}
              alt=""
              className="w-full max-h-[150px] object-cover"
            />
          )}
          <div className="px-3 py-2">
            <span className="text-[13px] text-muted-foreground">
              {post.linkCard.domain}
            </span>
            {post.linkCard.title && (
              <p className="text-[15px] text-foreground leading-5 line-clamp-2">
                {post.linkCard.title}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

// ---------------------------------------------------------------------------
// Verification badge
// ---------------------------------------------------------------------------

function VerificationBadge({
  type,
  size = 18,
}: {
  type: string
  size?: number
}) {
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
  linkCard?: LinkCardData
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
  linkCard,
}: PostCardProps) {
  const [textExpanded, setTextExpanded] = useState(false)

  const isLongText = text.length > TRUNCATE_LENGTH
  const displayText =
    !textExpanded && isLongText
      ? text.slice(0, TRUNCATE_LENGTH) + "…"
      : text

  const initials = authorName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)

  const displayTime = formatTimestamp(createdAt, timestamp)

  // Determine if we should hide URLs in text (when we have an enriched link card or media)
  const hasLinkCard = !!linkCard
  const hasMedia = media && media.length > 0

  // Extract first URL for fallback link card (only if no enriched linkCard and no media)
  const textSegments = useMemo(() => parsePostText(displayText), [displayText])
  const firstUrl = useMemo(() => {
    if (hasLinkCard || hasMedia) return null
    for (const seg of textSegments) {
      if (seg.type === "url" && seg.href) return seg.href
    }
    return null
  }, [textSegments, hasLinkCard, hasMedia])

  const handleImageClick = (url: string) => {
    window.open(url, "_blank", "noopener,noreferrer")
  }

  return (
    <article className="flex gap-3 group min-h-[44px] min-w-0">
      {/* Avatar */}
      <div className="flex-shrink-0">
        <Avatar className="h-10 w-10">
          {authorAvatarUrl && (
            <AvatarImage
              src={proxyUrl(authorAvatarUrl)}
              alt={authorName}
            />
          )}
          <AvatarFallback className="bg-accent text-muted-foreground text-sm font-medium">
            {initials}
          </AvatarFallback>
        </Avatar>
      </div>

      {/* Content */}
      <div className="w-0 flex-1 overflow-hidden">
        {/* Author info — single line like X */}
        <div className="flex items-center gap-1 min-w-0">
          <span className="font-bold text-[15px] leading-5 text-foreground truncate">
            {authorName}
          </span>

          {verified && <VerificationBadge type={verified} />}

          <span className="text-[15px] leading-5 text-muted-foreground truncate flex-shrink-[2]">
            @{authorUsername}
          </span>

          {displayTime && (
            <>
              <span className="text-muted-foreground flex-shrink-0">·</span>
              <span className="text-[15px] leading-5 text-muted-foreground flex-shrink-0">
                {displayTime}
              </span>
            </>
          )}
        </div>

        {/* Post text with rich parsing */}
        <div className="mt-0.5 max-w-full">
          <p className="text-[15px] leading-[20px] text-foreground whitespace-pre-wrap break-words">
            <RichText text={displayText} hideUrls={hasLinkCard} />
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

        {/* Media attachments */}
        {hasMedia && (
          <MediaGrid media={media!} onImageClick={handleImageClick} />
        )}

        {/* Enriched link card (from syndication API) */}
        {hasLinkCard && <EnrichedLinkCard card={linkCard!} />}

        {/* Fallback simple link card (URL-only, no enrichment data) */}
        {firstUrl && !hasLinkCard && <SimpleLinkCard url={firstUrl} />}

        {/* Quoted post */}
        {quotedPost && <QuotedPost post={quotedPost} />}

        {/* Engagement metrics — X layout */}
        {metrics && (
          <div className="mt-1 flex items-center justify-between max-w-full">
            {/* Replies — blue on hover */}
            <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#1d9bf0] cursor-pointer">
              <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#1d9bf0]/10">
                <MessageCircle className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
              </div>
              {(metrics.replies ?? 0) > 0 && (
                <span className="text-[12px] sm:text-[13px] leading-4">
                  {formatNumber(metrics.replies!)}
                </span>
              )}
            </div>

            {/* Reposts — green on hover */}
            <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#00ba7c] cursor-pointer">
              <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#00ba7c]/10">
                <Repeat2 className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
              </div>
              {(metrics.reposts ?? 0) > 0 && (
                <span className="text-[12px] sm:text-[13px] leading-4">
                  {formatNumber(metrics.reposts!)}
                </span>
              )}
            </div>

            {/* Likes — pink on hover */}
            <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#f91880] cursor-pointer">
              <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#f91880]/10">
                <Heart className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
              </div>
              {(metrics.likes ?? 0) > 0 && (
                <span className="text-[12px] sm:text-[13px] leading-4">
                  {formatNumber(metrics.likes!)}
                </span>
              )}
            </div>

            {/* Views — blue on hover */}
            <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#1d9bf0] cursor-pointer">
              <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#1d9bf0]/10">
                <Eye className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
              </div>
              {(metrics.views ?? 0) > 0 && (
                <span className="text-[12px] sm:text-[13px] leading-4">
                  {formatNumber(metrics.views!)}
                </span>
              )}
            </div>

            {/* Bookmark — blue on hover */}
            <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#1d9bf0] cursor-pointer">
              <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#1d9bf0]/10">
                <Bookmark className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
              </div>
              {(metrics.bookmarks ?? 0) > 0 && (
                <span className="text-[12px] sm:text-[13px] leading-4">
                  {formatNumber(metrics.bookmarks!)}
                </span>
              )}
            </div>

            {/* Share — blue on hover, hidden on small mobile */}
            <div className="group/metric hidden sm:flex items-center text-muted-foreground p-1.5 transition-colors hover:text-[#1d9bf0] cursor-pointer">
              <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#1d9bf0]/10">
                <Share className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
              </div>
            </div>
          </div>
        )}
      </div>
    </article>
  )
}
