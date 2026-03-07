#!/usr/bin/env python3
"""Fetch all accounts your X account follows."""

import httpx
import json
import asyncio
import os
from pathlib import Path

BEARER_TOKEN = os.environ.get("X_BRIEF_BEARER_TOKEN", "")
if not BEARER_TOKEN:
    print("Error: X_BRIEF_BEARER_TOKEN environment variable is required.")
    raise SystemExit(1)

BASE_URL = "https://api.twitter.com/2"
X_USERNAME = os.environ.get("X_BRIEF_USERNAME", "")
if not X_USERNAME:
    print("Error: X_BRIEF_USERNAME environment variable is required.")
    raise SystemExit(1)


async def get_user_id(username: str) -> str:
    """Get user ID from username."""
    url = f"{BASE_URL}/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        return data["data"]["id"]


async def get_all_following(user_id: str) -> list:
    """Fetch all accounts a user follows with pagination."""
    url = f"{BASE_URL}/users/{user_id}/following"
    headers = {"Authorization": f"Bearer {BEARER_TOKEN}"}
    params = {
        "max_results": 1000,
        "user.fields": "id,name,username,description,public_metrics,profile_image_url,verified_type",
    }

    all_users = []
    pagination_token = None

    async with httpx.AsyncClient() as client:
        while True:
            if pagination_token:
                params["pagination_token"] = pagination_token

            print(f"Fetching page... (total so far: {len(all_users)})")
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if "data" in data:
                all_users.extend(data["data"])

            # Check for next page
            if "meta" in data and "next_token" in data["meta"]:
                pagination_token = data["meta"]["next_token"]
            else:
                break

    return all_users


async def main():
    print(f"Fetching user ID for @{X_USERNAME}...")
    user_id = await get_user_id(X_USERNAME)
    print(f"User ID: {user_id}")

    print("\nFetching all following accounts...")
    following = await get_all_following(user_id)
    print(f"\n✅ Fetched {len(following)} accounts total")

    usernames = [user["username"] for user in following]

    # Update local config if target path is provided.
    output_config_path = os.environ.get("X_BRIEF_CONFIG_PATH", "")
    if output_config_path:
        config_path = Path(output_config_path)
        with open(config_path) as f:
            config = json.load(f)

        config["tracked_accounts"] = usernames

        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\n✅ Updated {config_path} with {len(usernames)} accounts")

    # Write full following payload if output path is provided.
    output_following_path = os.environ.get("X_BRIEF_FOLLOWING_OUTPUT", "")
    if output_following_path:
        following_path = Path(output_following_path)
        with open(following_path, "w") as f:
            json.dump(following, f, indent=2)
        print(f"✅ Updated {following_path} with full account details")

    print("\n📋 Sample of accounts (first 10):")
    for user in following[:10]:
        verified = " ✓" if user.get("verified_type") else ""
        print(f"  - @{user['username']}{verified} ({user['name']})")


if __name__ == "__main__":
    asyncio.run(main())
