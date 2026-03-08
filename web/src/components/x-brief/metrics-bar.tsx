import { Bookmark, Eye, Heart, MessageCircle, Repeat2, Share } from "lucide-react"

export interface PostMetrics {
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

export function MetricsBar({ metrics }: { metrics: PostMetrics }) {
  return (
    <div className="mt-1 flex items-center justify-between max-w-full">
      <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#1d9bf0] cursor-pointer">
        <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#1d9bf0]/10">
          <MessageCircle className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
        </div>
        {(metrics.replies ?? 0) > 0 && (
          <span className="text-[12px] sm:text-[13px] leading-4">{formatNumber(metrics.replies!)}</span>
        )}
      </div>

      <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#00ba7c] cursor-pointer">
        <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#00ba7c]/10">
          <Repeat2 className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
        </div>
        {(metrics.reposts ?? 0) > 0 && (
          <span className="text-[12px] sm:text-[13px] leading-4">{formatNumber(metrics.reposts!)}</span>
        )}
      </div>

      <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#f91880] cursor-pointer">
        <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#f91880]/10">
          <Heart className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
        </div>
        {(metrics.likes ?? 0) > 0 && (
          <span className="text-[12px] sm:text-[13px] leading-4">{formatNumber(metrics.likes!)}</span>
        )}
      </div>

      <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#1d9bf0] cursor-pointer">
        <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#1d9bf0]/10">
          <Eye className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
        </div>
        {(metrics.views ?? 0) > 0 && (
          <span className="text-[12px] sm:text-[13px] leading-4">{formatNumber(metrics.views!)}</span>
        )}
      </div>

      <div className="group/metric flex items-center gap-0.5 text-muted-foreground p-1.5 transition-colors hover:text-[#1d9bf0] cursor-pointer">
        <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#1d9bf0]/10">
          <Bookmark className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
        </div>
        {(metrics.bookmarks ?? 0) > 0 && (
          <span className="text-[12px] sm:text-[13px] leading-4">{formatNumber(metrics.bookmarks!)}</span>
        )}
      </div>

      <div className="group/metric hidden sm:flex items-center text-muted-foreground p-1.5 transition-colors hover:text-[#1d9bf0] cursor-pointer">
        <div className="rounded-full p-1 -m-1 transition-colors group-hover/metric:bg-[#1d9bf0]/10">
          <Share className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
        </div>
      </div>
    </div>
  )
}
