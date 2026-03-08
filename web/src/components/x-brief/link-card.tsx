import { ExternalLink } from "lucide-react"
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
        <div className="relative aspect-[1.91/1] bg-accent overflow-hidden">
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
