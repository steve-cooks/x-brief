"use client"

import { PostCard } from "./post-card"

interface BriefingPost {
  authorName: string
  authorUsername: string
  authorAvatarUrl?: string
  text: string
  metrics?: {
    likes?: number
    reposts?: number
    views?: number
  }
  postUrl?: string
  timestamp?: string
  category?: string
}

interface BriefingSectionProps {
  title: string
  emoji: string
  posts: BriefingPost[]
  maxPosts?: number
}

export function BriefingSection({
  title,
  emoji,
  posts,
  maxPosts = 10,
}: BriefingSectionProps) {
  const displayPosts = posts.slice(0, maxPosts)

  if (displayPosts.length === 0) return null

  return (
    <section className="space-y-3">
      <div className="flex items-center gap-2.5 px-1">
        <span className="text-xl">{emoji}</span>
        <h2 className="text-[17px] font-semibold tracking-tight text-[#1D1D1F] dark:text-[#F5F5F7]">
          {title}
        </h2>
        <span className="text-[13px] text-[#86868B] dark:text-[#98989D]">
          {displayPosts.length} {displayPosts.length === 1 ? "post" : "posts"}
        </span>
      </div>

      <div className="space-y-2">
        {displayPosts.map((post, index) => (
          <PostCard key={`${post.authorUsername}-${index}`} {...post} />
        ))}
      </div>
    </section>
  )
}
