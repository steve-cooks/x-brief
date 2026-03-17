"use client"

import { ChevronDown, ChevronUp } from "lucide-react"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { useMemo, useState } from "react"
import { RichText, parsePostText } from "@/components/x-brief/rich-text"
import { MediaGrid, type MediaItem, proxyUrl } from "@/components/x-brief/media-grid"
import { ArticleCard, ArticleReaderModal, EnrichedLinkCard, type LinkCardData, SimpleLinkCard } from "@/components/x-brief/link-card"
import { MetricsBar, type PostMetrics } from "@/components/x-brief/metrics-bar"

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
  const displayText = !expanded && isLong ? post.text.slice(0, 180) + "…" : post.text

  return (
    <div
      className="mt-3 border border-border rounded-2xl overflow-hidden cursor-pointer hover:bg-foreground/[0.03] transition-colors max-w-full"
      onClick={(e) => {
        e.stopPropagation()
        if (post.postUrl) window.open(post.postUrl, "_blank", "noopener,noreferrer")
      }}
    >
      <div className="px-3 py-2.5">
        <div className="flex items-center gap-1.5">
          <Avatar className="h-5 w-5">
            {post.authorAvatarUrl && <AvatarImage src={proxyUrl(post.authorAvatarUrl)} alt={post.authorName} />}
            <AvatarFallback className="bg-accent text-[10px] font-medium">
              {post.authorName?.[0]?.toUpperCase() || "?"}
            </AvatarFallback>
          </Avatar>
          <span className="font-bold text-[13px] text-foreground leading-4 truncate">{post.authorName}</span>
          {post.verified && <VerificationBadge type={post.verified} size={14} />}
          <span className="text-[13px] text-muted-foreground leading-4 truncate">@{post.authorUsername}</span>
          {(post.createdAt || post.timestamp) && (
            <>
              <span className="text-muted-foreground text-[13px]">·</span>
              <span className="text-[13px] text-muted-foreground leading-4">
                {formatTimestamp(post.createdAt, post.timestamp)}
              </span>
            </>
          )}
        </div>

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

      {post.media && post.media.length > 0 && post.media[0].type === "photo" && post.media[0].url && (
        <img
          src={proxyUrl(post.media[0].url)}
          alt={post.media[0].alt_text || "Image"}
          className="w-full max-h-[200px] object-cover border-t border-border"
        />
      )}

      {post.linkCard && post.linkCard.url && (
        <div className="mx-3 mb-2.5 border border-border rounded-xl overflow-hidden">
          {post.linkCard.thumbnail && <img src={proxyUrl(post.linkCard.thumbnail)} alt="" className="w-full max-h-[150px] object-cover" />}
          <div className="px-3 py-2">
            <span className="text-[13px] text-muted-foreground">{post.linkCard.domain}</span>
            {post.linkCard.title && (
              <p className="text-[15px] text-foreground leading-5 line-clamp-2">{post.linkCard.title}</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

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
        fill={type === "business" ? "#E8A12E" : type === "government" ? "#829AAB" : "#1D9BF0"}
      />
    </svg>
  )
}

interface CommunityNoteData {
  text: string
  url?: string | null
}

function CommunityNote({ note }: { note: CommunityNoteData }) {
  return (
    <div className="mt-3 rounded-2xl border border-amber-200/60 bg-amber-50/80 dark:border-amber-700/40 dark:bg-amber-950/30 px-3 py-2.5">
      <div className="flex items-center gap-1.5 mb-1.5">
        {/* Community Notes info icon */}
        <svg viewBox="0 0 20 20" className="h-4 w-4 flex-shrink-0 text-amber-600 dark:text-amber-400" fill="currentColor" aria-hidden="true">
          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a.75.75 0 000 1.5h.253a.25.25 0 01.244.304l-.459 2.066A1.75 1.75 0 0010.747 15H11a.75.75 0 000-1.5h-.253a.25.25 0 01-.244-.304l.459-2.066A1.75 1.75 0 009.253 9H9z" clipRule="evenodd" />
        </svg>
        <span className="text-[12px] font-semibold text-amber-700 dark:text-amber-400 leading-4">
          Readers added context
        </span>
      </div>
      <p className="text-[13px] leading-[18px] text-amber-900 dark:text-amber-200 whitespace-pre-wrap break-words">
        {note.text}
      </p>
      {note.url && (
        <a
          href={note.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1.5 inline-block text-[12px] text-amber-700 dark:text-amber-400 hover:underline"
          onClick={(e) => e.stopPropagation()}
        >
          Learn more ↗
        </a>
      )}
    </div>
  )
}

interface PostCardProps {
  authorName: string
  authorUsername: string
  authorAvatarUrl?: string
  verified?: string | null
  text: string
  media?: MediaItem[]
  metrics?: PostMetrics
  postUrl?: string
  source?: "for_you" | "following" | null
  is_article?: boolean
  article_url?: string | null
  thread_posts?: Array<{ id?: string | null; text: string; url?: string | null }>
  timestamp?: string
  createdAt?: string
  category?: string
  quotedPost?: QuotedPostData
  linkCard?: LinkCardData
  communityNote?: CommunityNoteData | null
  onMediaOpen?: (items: MediaItem[], index: number) => void
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
  is_article,
  article_url,
  thread_posts,
  timestamp,
  createdAt,
  quotedPost,
  linkCard,
  communityNote,
  onMediaOpen,
}: PostCardProps) {
  const [textExpanded, setTextExpanded] = useState(false)
  const [threadExpanded, setThreadExpanded] = useState(false)
  const [articleReaderOpen, setArticleReaderOpen] = useState(false)

  const isLongText = text.length > TRUNCATE_LENGTH
  const displayText = !textExpanded && isLongText ? text.slice(0, TRUNCATE_LENGTH) + "…" : text

  const initials = authorName
    .split(" ")
    .map((n) => n[0])
    .join("")
    .toUpperCase()
    .slice(0, 2)

  const displayTime = formatTimestamp(createdAt, timestamp)

  const hasLinkCard = !!linkCard
  const hasMedia = media && media.length > 0

  const textSegments = useMemo(() => parsePostText(displayText), [displayText])
  const firstUrl = useMemo(() => {
    if (hasLinkCard || hasMedia) return null
    for (const seg of textSegments) {
      if (seg.type === "url" && seg.href) return seg.href
    }
    return null
  }, [textSegments, hasLinkCard, hasMedia])

  const handleImageClick = (url: string) => {
    if (onMediaOpen && media && media.length > 0) {
      const index = media.findIndex((m) => m.url === url)
      onMediaOpen(media, index >= 0 ? index : 0)
    } else {
      window.open(url, "_blank", "noopener,noreferrer")
    }
  }

  return (
    <article className="flex gap-3 group min-h-[44px] min-w-0 max-w-full overflow-hidden">
      <div className="flex-shrink-0">
        <Avatar className="h-10 w-10">
          {authorAvatarUrl && <AvatarImage src={proxyUrl(authorAvatarUrl)} alt={authorName} />}
          <AvatarFallback className="bg-accent text-muted-foreground text-sm font-medium">{initials}</AvatarFallback>
        </Avatar>
      </div>

      <div className="w-0 flex-1 overflow-hidden">
        <div className="flex items-center gap-1 min-w-0">
          <span className="font-bold text-[15px] leading-5 text-foreground truncate">{authorName}</span>
          {verified && <VerificationBadge type={verified} />}
          <span className="text-[15px] leading-5 text-muted-foreground truncate flex-shrink-[2]">@{authorUsername}</span>
          {displayTime && (
            <>
              <span className="text-muted-foreground flex-shrink-0">·</span>
              <span className="text-[15px] leading-5 text-muted-foreground flex-shrink-0">{displayTime}</span>
            </>
          )}
        </div>

        {(is_article || (thread_posts && thread_posts.length > 0)) && (
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {is_article && (
              <span className="inline-flex items-center rounded-full border border-[#1d9bf0]/40 bg-[#1d9bf0]/10 px-2 py-0.5 text-[11px] font-medium text-[#1d9bf0]">
                Article
              </span>
            )}
            {thread_posts && thread_posts.length > 0 && (
              <button
                type="button"
                className="inline-flex items-center gap-1 rounded-full border border-border bg-accent px-2 py-0.5 text-[11px] font-medium text-foreground hover:bg-foreground/[0.06]"
                onClick={(e) => {
                  e.stopPropagation()
                  setThreadExpanded((prev) => !prev)
                }}
              >
                <span>Thread · {thread_posts.length + 1} posts</span>
                {threadExpanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              </button>
            )}
          </div>
        )}

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

        {hasMedia && <MediaGrid media={media!} onImageClick={handleImageClick} onMediaOpen={onMediaOpen} />}

        {/* Article posts get a rich card that opens the in-app reader */}
        {is_article ? (
          <>
            <ArticleCard
              card={linkCard ?? null}
              articleUrl={article_url}
              authorName={authorName}
              authorUsername={authorUsername}
              postText={text}
              onOpen={() => setArticleReaderOpen(true)}
            />
            {articleReaderOpen && (
              <ArticleReaderModal
                url={linkCard?.url || article_url || postUrl || ""}
                title={linkCard?.title}
                onClose={() => setArticleReaderOpen(false)}
              />
            )}
          </>
        ) : (
          <>
            {hasLinkCard && <EnrichedLinkCard card={linkCard!} />}
            {firstUrl && !hasLinkCard && <SimpleLinkCard url={firstUrl} />}
          </>
        )}

        {quotedPost && <QuotedPost post={quotedPost} />}
        {communityNote && communityNote.text && <CommunityNote note={communityNote} />}
        {threadExpanded && thread_posts && thread_posts.length > 0 && (
          <div className="mt-2 space-y-1 border-l-2 border-border pl-3">
            {thread_posts.map((threadPost, index) => (
              <div
                key={threadPost.id || `${threadPost.url || "thread"}-${index}`}
                className="rounded-md px-2 py-1 text-[13px] leading-4 text-muted-foreground bg-muted/30"
              >
                <RichText text={threadPost.text} />
                {threadPost.url && (
                  <button
                    type="button"
                    className="ml-1 text-[#1d9bf0] hover:underline"
                    onClick={(e) => {
                      e.stopPropagation()
                      window.open(threadPost.url || undefined, "_blank", "noopener,noreferrer")
                    }}
                  >
                    ↗
                  </button>
                )}
              </div>
            ))}
          </div>
        )}
        {metrics && <MetricsBar metrics={metrics} />}
      </div>
    </article>
  )
}
