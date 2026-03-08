import { Bookmark, Eye, Heart, MessageCircle, Repeat2 } from "lucide-react"

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
  const items = [
    {
      key: "replies",
      value: metrics.replies ?? 0,
      Icon: MessageCircle,
      className: "hover:text-[#1d9bf0]",
      iconBgClass: "group-hover/metric:bg-[#1d9bf0]/10",
    },
    {
      key: "reposts",
      value: metrics.reposts ?? 0,
      Icon: Repeat2,
      className: "hover:text-[#00ba7c]",
      iconBgClass: "group-hover/metric:bg-[#00ba7c]/10",
    },
    {
      key: "likes",
      value: metrics.likes ?? 0,
      Icon: Heart,
      className: "hover:text-[#f91880]",
      iconBgClass: "group-hover/metric:bg-[#f91880]/10",
    },
    {
      key: "bookmarks",
      value: metrics.bookmarks ?? 0,
      Icon: Bookmark,
      className: "hover:text-[#1d9bf0]",
      iconBgClass: "group-hover/metric:bg-[#1d9bf0]/10",
    },
    {
      key: "views",
      value: metrics.views ?? 0,
      Icon: Eye,
      className: "hover:text-[#1d9bf0]",
      iconBgClass: "group-hover/metric:bg-[#1d9bf0]/10",
    },
  ]

  return (
    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 max-w-full">
      {items.map(({ key, value, Icon, className, iconBgClass }) => (
        <div
          key={key}
          className={`group/metric flex items-center gap-0.5 text-muted-foreground p-1 transition-colors cursor-pointer ${className}`}
        >
          <div className={`rounded-full p-1 -m-1 transition-colors ${iconBgClass}`}>
            <Icon className="h-4 w-4 sm:h-[18.75px] sm:w-[18.75px]" />
          </div>
          <span className="text-[12px] sm:text-[13px] leading-4">{formatNumber(value)}</span>
        </div>
      ))}
    </div>
  )
}
