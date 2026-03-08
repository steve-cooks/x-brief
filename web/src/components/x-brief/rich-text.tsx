import { Fragment, useMemo } from "react"

export interface TextSegment {
  type: "text" | "mention" | "hashtag" | "url"
  value: string
  href?: string
}

const SEGMENT_RE =
  /(@[A-Za-z0-9_]{1,15})|(#[A-Za-z0-9_\u00C0-\u024F]+)|(https?:\/\/[^\s<]+)/g

export function parsePostText(raw: string): TextSegment[] {
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

export function RichText({
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
        if (seg.type === "text") {
          return <Fragment key={i}>{seg.value}</Fragment>
        }
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
