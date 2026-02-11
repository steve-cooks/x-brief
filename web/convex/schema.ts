import { defineSchema, defineTable } from "convex/server";
import { v } from "convex/values";

export default defineSchema({
  // Users who subscribe to X Brief
  users: defineTable({
    email: v.string(),
    name: v.optional(v.string()),
    plan: v.union(v.literal("free"), v.literal("pro")),
    stripeCustomerId: v.optional(v.string()),
    createdAt: v.number(),
  }).index("by_email", ["email"]),

  // Generated briefings
  briefings: defineTable({
    userId: v.id("users"),
    title: v.string(),
    sections: v.array(v.object({
      name: v.string(),
      posts: v.array(v.object({
        author: v.string(),
        authorHandle: v.string(),
        authorAvatar: v.optional(v.string()),
        text: v.string(),
        url: v.string(),
        likes: v.number(),
        retweets: v.number(),
        views: v.number(),
        mediaUrls: v.optional(v.array(v.string())),
        isVerified: v.optional(v.boolean()),
      })),
    })),
    generatedAt: v.number(),
  }).index("by_user", ["userId"]),

  // User's followed accounts / interests
  userFollows: defineTable({
    userId: v.id("users"),
    handle: v.string(),
    name: v.string(),
    category: v.optional(v.string()),
  }).index("by_user", ["userId"]),

  // User preferences
  userPreferences: defineTable({
    userId: v.id("users"),
    interests: v.array(v.string()),
    briefingFrequency: v.union(v.literal("daily"), v.literal("twice_daily"), v.literal("four_times")),
    deliveryMethod: v.union(v.literal("web"), v.literal("email"), v.literal("both")),
  }).index("by_user", ["userId"]),
});
