"use client"

import { ExternalLink, BookOpen, X as XIcon } from "lucide-react"
import { useEffect, useCallback } from "react"
import { proxyUrl } from "@/components/x-brief/media-grid"

export interface LinkCardData {
  title: string
  description?: string
  thumbnail?: string | null
  domain?: string
  url?: string
}

export function EnrichedLinkCard({ card }: { card: LinkCardData }) {
  const domain = card.domain || ""

  return (
    <a
      href={card.url}
      target="_blank"
      rel="noopener noreferrer"
      className="mt-3 block border border-border rounded-2xl overflow-hidden transition-colors hover:bg-foreground/[0.03] bg-background max-w-full"
      onClick={(e) => e.stopPropagation()}
    >
      {card.thumbnail && (
        <div className="relative aspect-[1.91/1] bg-accent rounded-t-2xl overflow-hidden border-b border-border">
          <img
            src={proxyUrl(card.thumbnail)}
            alt={card.title}
            className="w-full h-full object-cover"
          />
        </div>
      )}
      <div className="px-3 py-2.5">
        <div className="text-[13px] text-muted-foreground truncate">{domain}</div>
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

export function SimpleLinkCard({ url }: { url: string }) {
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
      <span className="text-[13px] text-muted-foreground truncate">{domain}</span>
      <ExternalLink className="h-3.5 w-3.5 flex-shrink-0 text-muted-foreground" />
    </a>
  )
}

// ─── Article Card ──────────────────────────────────────────────────────────────

export interface ArticleCardProps {
  card?: LinkCardData | null
  /** Fallback article URL if card has no url */
  articleUrl?: string | null
  /** Author of the post (shown as article author fallback) */
  authorName?: string
  authorUsername?: string
  /** Called when user taps the card — opens in-app reader */
  onOpen: () => void
}

/**
 * X-style article card: hero image, bold title, description, author row.
 * Clicking opens the article in the in-app reader (not a new tab).
 */
export function ArticleCard({
  card,
  articleUrl,
  authorName,
  authorUsername,
  onOpen,
}: ArticleCardProps) {
  const title = card?.title || ""
  const description = card?.description || ""
  const thumbnail = card?.thumbnail
  const domain = card?.domain || (articleUrl ? (() => {
    try { return new URL(articleUrl).hostname.replace(/^www\./, "") } catch { return "x.com" }
  })() : "x.com")

  return (
    <button
      type="button"
      className="mt-3 w-full text-left border border-border rounded-2xl overflow-hidden transition-colors hover:bg-foreground/[0.03] bg-background focus:outline-none focus-visible:ring-2 focus-visible:ring-[#1d9bf0]"
      onClick={(e) => {
        e.stopPropagation()
        onOpen()
      }}
    >
      {/* Hero image */}
      {thumbnail && (
        <div className="relative w-full aspect-[16/9] bg-accent rounded-t-2xl overflow-hidden border-b border-border">
          <img
            src={proxyUrl(thumbnail)}
            alt={title || "Article cover"}
            className="w-full h-full object-cover"
          />
        </div>
      )}

      {/* Card body */}
      <div className="px-3.5 py-3">
        {/* Article badge + domain row */}
        <div className="flex items-center gap-2 mb-1.5">
          <span className="inline-flex items-center gap-1 rounded-full bg-[#1d9bf0]/10 border border-[#1d9bf0]/30 px-2 py-0.5 text-[11px] font-semibold text-[#1d9bf0]">
            <BookOpen className="h-2.5 w-2.5" />
            Article
          </span>
          <span className="text-[12px] text-muted-foreground truncate">{domain}</span>
        </div>

        {/* Title */}
        {title && (
          <div className="text-[16px] font-bold text-foreground leading-[1.3] line-clamp-3">
            {title}
          </div>
        )}

        {/* Description / subtitle */}
        {description && (
          <div className="mt-1 text-[13px] text-muted-foreground leading-[1.4] line-clamp-2">
            {description}
          </div>
        )}

        {/* Author row */}
        {(authorName || authorUsername) && (
          <div className="mt-2 text-[12px] text-muted-foreground">
            {authorName && <span className="font-medium text-foreground/70">{authorName}</span>}
            {authorUsername && (
              <span className="ml-1 opacity-60">@{authorUsername}</span>
            )}
          </div>
        )}
      </div>
    </button>
  )
}

// ─── Article Reader Modal ──────────────────────────────────────────────────────

export interface ArticleReaderProps {
  url: string
  title?: string
  onClose: () => void
}

/**
 * Full-screen in-app article reader with iframe.
 * Falls back to "Open in browser" link if the iframe is blocked.
 */
export function ArticleReaderModal({ url, title, onClose }: ArticleReaderProps) {
  // Lock body scroll while modal is open
  useEffect(() => {
    const orig = document.body.style.overflow
    document.body.style.overflow = "hidden"
    return () => { document.body.style.overflow = orig }
  }, [])

  // Escape key to close
  const handleKey = useCallback(
    (e: KeyboardEvent) => { if (e.key === "Escape") onClose() },
    [onClose]
  )
  useEffect(() => {
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [handleKey])

  return (
    <div
      className="fixed inset-0 z-[200] flex flex-col bg-background animate-in fade-in duration-150"
      role="dialog"
      aria-modal="true"
      aria-label={title || "Article Reader"}
    >
      {/* Header bar */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border bg-background/95 backdrop-blur-sm flex-shrink-0">
        <button
          onClick={onClose}
          className="flex items-center justify-center h-8 w-8 rounded-full text-muted-foreground hover:bg-foreground/[0.08] transition-colors flex-shrink-0"
          aria-label="Close article reader"
        >
          <XIcon className="h-5 w-5" />
        </button>

        <div className="flex-1 min-w-0">
          {title && (
            <p className="text-[13px] font-medium text-foreground truncate">{title}</p>
          )}
          <p className="text-[11px] text-muted-foreground truncate">{url}</p>
        </div>

        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center h-8 w-8 rounded-full text-muted-foreground hover:bg-foreground/[0.08] transition-colors flex-shrink-0"
          aria-label="Open in browser"
          title="Open in browser"
          onClick={(e) => e.stopPropagation()}
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>

      {/* iframe */}
      <div className="flex-1 relative overflow-hidden">
        <iframe
          src={url}
          title={title || "Article"}
          className="w-full h-full border-0"
          sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
          loading="lazy"
        />
      </div>
    </div>
  )
}
