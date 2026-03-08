import { Play } from "lucide-react"
import { useRef, useState } from "react"

export interface MediaItem {
  type: string
  url?: string
  preview_image_url?: string
  video_url?: string
  alt_text?: string
}

/** Proxy Twitter media URLs through our API to avoid referer blocking */
export function proxyUrl(url: string | undefined | null): string | undefined {
  if (!url) return undefined
  if (url.includes("video.twimg.com") || url.includes("pbs.twimg.com")) {
    return `/api/media?url=${encodeURIComponent(url)}`
  }
  return url
}

export function MediaGrid({
  media,
  onImageClick,
  onMediaOpen,
}: {
  media: MediaItem[]
  onImageClick?: (url: string) => void
  onMediaOpen?: (items: MediaItem[], index: number) => void
}) {
  const count = media.length

  if (count === 0) return null

  if (count === 1) {
    return (
      <SingleMedia
        item={media[0]}
        onImageClick={onImageClick}
        onMediaOpen={onMediaOpen ? () => onMediaOpen(media, 0) : undefined}
      />
    )
  }

  if (count === 2) {
    return (
      <div className="mt-3 w-full max-w-full grid grid-cols-2 gap-0.5 rounded-2xl overflow-hidden border border-border">
        {media.map((item, i) => (
          <div key={i} className="relative aspect-square bg-accent overflow-hidden">
            <MediaContent
              item={item}
              fill
              onImageClick={onImageClick}
              onMediaOpen={onMediaOpen ? () => onMediaOpen(media, i) : undefined}
            />
          </div>
        ))}
      </div>
    )
  }

  if (count === 3) {
    return (
      <div
        className="mt-3 w-full max-w-full grid grid-cols-2 gap-0.5 rounded-2xl overflow-hidden border border-border"
        style={{ aspectRatio: "16/9" }}
      >
        <div className="relative row-span-2 bg-accent overflow-hidden">
          <MediaContent
            item={media[0]}
            fill
            onImageClick={onImageClick}
            onMediaOpen={onMediaOpen ? () => onMediaOpen(media, 0) : undefined}
          />
        </div>
        <div className="relative bg-accent overflow-hidden">
          <MediaContent
            item={media[1]}
            fill
            onImageClick={onImageClick}
            onMediaOpen={onMediaOpen ? () => onMediaOpen(media, 1) : undefined}
          />
        </div>
        <div className="relative bg-accent overflow-hidden">
          <MediaContent
            item={media[2]}
            fill
            onImageClick={onImageClick}
            onMediaOpen={onMediaOpen ? () => onMediaOpen(media, 2) : undefined}
          />
        </div>
      </div>
    )
  }

  return (
    <div
      className="mt-3 w-full max-w-full grid grid-cols-2 grid-rows-2 gap-0.5 rounded-2xl overflow-hidden border border-border"
      style={{ aspectRatio: "16/9" }}
    >
      {media.slice(0, 4).map((item, i) => (
        <div key={i} className="relative bg-accent overflow-hidden">
          <MediaContent
            item={item}
            fill
            onImageClick={onImageClick}
            onMediaOpen={onMediaOpen ? () => onMediaOpen(media, i) : undefined}
          />
        </div>
      ))}
    </div>
  )
}

export function SingleMedia({
  item,
  onImageClick,
  onMediaOpen,
}: {
  item: MediaItem
  onImageClick?: (url: string) => void
  onMediaOpen?: () => void
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
        <VideoPlayer item={item} onMediaOpen={onMediaOpen} />
      </div>
    )
  }

  if (item.type === "animated_gif") {
    return (
      <div className="mt-3 w-full max-w-full rounded-2xl overflow-hidden border border-border">
        <GifPlayer item={item} onMediaOpen={onMediaOpen} />
      </div>
    )
  }

  return null
}

function MediaContent({
  item,
  fill,
  onImageClick,
  onMediaOpen,
}: {
  item: MediaItem
  fill?: boolean
  onImageClick?: (url: string) => void
  onMediaOpen?: () => void
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
    return <VideoPlayer item={item} fill onMediaOpen={onMediaOpen} />
  }

  if (item.type === "animated_gif") {
    return <GifPlayer item={item} fill onMediaOpen={onMediaOpen} />
  }

  return null
}

function VideoPlayer({
  item,
  fill,
  onMediaOpen,
}: {
  item: MediaItem
  fill?: boolean
  onMediaOpen?: () => void
}) {
  const [playing, setPlaying] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)

  const posterUrl = proxyUrl(item.preview_image_url || item.url)
  const videoUrl = proxyUrl(item.video_url)

  if (!videoUrl) {
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
          if (onMediaOpen) {
            onMediaOpen()
          } else {
            setPlaying(true)
          }
        }}
      >
        {posterUrl && (
          <img
            src={posterUrl}
            alt="Video poster"
            className={fill ? "w-full h-full object-cover" : "w-full max-h-[510px] object-cover"}
          />
        )}
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
      className={fill ? "w-full h-full object-cover" : "w-full max-h-[510px] object-cover"}
      onClick={(e) => e.stopPropagation()}
    />
  )
}

function GifPlayer({
  item,
  fill,
  onMediaOpen,
}: {
  item: MediaItem
  fill?: boolean
  onMediaOpen?: () => void
}) {
  const videoUrl = proxyUrl(item.video_url)
  const posterUrl = proxyUrl(item.preview_image_url || item.url)

  return (
    <div
      className={`relative cursor-pointer ${fill ? "w-full h-full" : ""}`}
      onClick={(e) => {
        e.stopPropagation()
        onMediaOpen?.()
      }}
    >
      {videoUrl ? (
        <video
          src={videoUrl}
          poster={posterUrl}
          loop
          autoPlay
          muted
          playsInline
          className={fill ? "w-full h-full object-cover" : "w-full max-h-[510px] object-cover"}
        />
      ) : posterUrl ? (
        <img
          src={posterUrl}
          alt="GIF"
          className={fill ? "w-full h-full object-cover" : "w-full max-h-[510px] object-cover"}
        />
      ) : null}
      <div className="absolute bottom-2 left-2 bg-foreground/80 text-background text-xs font-bold px-1.5 py-0.5 rounded">
        GIF
      </div>
    </div>
  )
}
