import { v } from "convex/values";
import { mutation, query } from "./_generated/server";

export const getPreferences = query({
  args: { userId: v.id("users") },
  handler: async (ctx, args) => {
    return await ctx.db
      .query("userPreferences")
      .withIndex("by_user", (q) => q.eq("userId", args.userId))
      .first();
  },
});

export const updatePreferences = mutation({
  args: {
    userId: v.id("users"),
    interests: v.optional(v.array(v.string())),
    briefingFrequency: v.optional(
      v.union(v.literal("daily"), v.literal("twice_daily"), v.literal("four_times"))
    ),
    deliveryMethod: v.optional(
      v.union(v.literal("web"), v.literal("email"), v.literal("both"))
    ),
  },
  handler: async (ctx, args) => {
    const existing = await ctx.db
      .query("userPreferences")
      .withIndex("by_user", (q) => q.eq("userId", args.userId))
      .first();

    if (existing) {
      // Update existing preferences
      await ctx.db.patch(existing._id, {
        ...(args.interests !== undefined && { interests: args.interests }),
        ...(args.briefingFrequency !== undefined && { briefingFrequency: args.briefingFrequency }),
        ...(args.deliveryMethod !== undefined && { deliveryMethod: args.deliveryMethod }),
      });
      return existing._id;
    } else {
      // Create new preferences with defaults
      const preferencesId = await ctx.db.insert("userPreferences", {
        userId: args.userId,
        interests: args.interests ?? [],
        briefingFrequency: args.briefingFrequency ?? "daily",
        deliveryMethod: args.deliveryMethod ?? "web",
      });
      return preferencesId;
    }
  },
});

export const initializePreferences = mutation({
  args: {
    userId: v.id("users"),
    interests: v.array(v.string()),
    briefingFrequency: v.union(v.literal("daily"), v.literal("twice_daily"), v.literal("four_times")),
    deliveryMethod: v.union(v.literal("web"), v.literal("email"), v.literal("both")),
  },
  handler: async (ctx, args) => {
    // Check if preferences already exist
    const existing = await ctx.db
      .query("userPreferences")
      .withIndex("by_user", (q) => q.eq("userId", args.userId))
      .first();

    if (existing) {
      return existing._id;
    }

    const preferencesId = await ctx.db.insert("userPreferences", {
      userId: args.userId,
      interests: args.interests,
      briefingFrequency: args.briefingFrequency,
      deliveryMethod: args.deliveryMethod,
    });

    return preferencesId;
  },
});
