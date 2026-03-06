import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

/**
 * SECURITY NOTE:
 * These functions include only minimal guards for open-source/dev usage.
 * Add full authentication + authorization checks before production deployment.
 */
async function requireAuthenticatedRequest(ctx: any) {
  const identity = await ctx.auth.getUserIdentity();
  if (!identity) {
    throw new Error("Unauthorized: authentication required.");
  }
}

function ensureNonEmptyId(value: unknown, fieldName: string) {
  if (!String(value ?? "").trim()) {
    throw new Error(`Invalid ${fieldName}: value is required.`);
  }
}

const postValidator = v.object({
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
});

const sectionValidator = v.object({
  name: v.string(),
  posts: v.array(postValidator),
});

export const createBriefing = mutation({
  args: {
    userId: v.id("users"),
    title: v.string(),
    sections: v.array(sectionValidator),
  },
  handler: async (ctx, args) => {
    await requireAuthenticatedRequest(ctx);
    ensureNonEmptyId(args.userId, "userId");

    const briefingId = await ctx.db.insert("briefings", {
      userId: args.userId,
      title: args.title,
      sections: args.sections,
      generatedAt: Date.now(),
    });

    return briefingId;
  },
});

export const getLatestBriefing = query({
  args: { userId: v.id("users") },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("briefings")
      .withIndex("by_user", (q) => q.eq("userId", args.userId))
      .order("desc")
      .first();
  },
});

export const listBriefings = query({
  args: {
    userId: v.id("users"),
    limit: v.optional(v.number()),
  },
  handler: async (ctx, args) => {
    const limit = args.limit ?? 10;
    return await ctx.db
      .query("briefings")
      .withIndex("by_user", (q) => q.eq("userId", args.userId))
      .order("desc")
      .take(limit);
  },
});

export const getBriefing = query({
  args: { id: v.id("briefings") },
  handler: async (ctx, args) => {
    return await ctx.db.get(args.id);
  },
});

export const deleteBriefing = mutation({
  args: { id: v.id("briefings") },
  handler: async (ctx, args) => {
    await requireAuthenticatedRequest(ctx);
    await ctx.db.delete(args.id);
  },
});
