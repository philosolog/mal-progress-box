"""MAL Progress Box - GitHub Gist updater for MyAnimeList stats.

This script fetches anime/manga progress from MyAnimeList and updates a GitHub Gist
with the top 5 entries. Includes rate limiting to prevent updates more than once per hour.
"""

import os
import sys
import time
from pathlib import Path
from typing import TypedDict
import requests

class MALEntry(TypedDict):
	"""Type definition for a MyAnimeList entry."""

	status: int
	anime_title: str
	anime_num_episodes: int
	num_watched_episodes: int
	manga_num_chapters: int
	manga_num_volumes: int
	num_read_chapters: int
	num_read_volumes: int


# Environment variables
GIST_ID = os.environ["GIST_ID"]
GITHUB_TOKEN = os.environ["GH_TOKEN"]
MAL_USERNAME = os.environ["MAL_USERNAME"]
CONTENT_TYPE = os.environ["CONTENT_TYPE"]
CONTENT_STATUS = os.environ["CONTENT_STATUS"]

# Debug: Print environment variable info (lengths, not values for security)
print(f"Debug: MAL_USERNAME length = {len(MAL_USERNAME)}, value = '{MAL_USERNAME}'")
print(f"Debug: CONTENT_TYPE = '{CONTENT_TYPE}'")
print(f"Debug: CONTENT_STATUS = '{CONTENT_STATUS}'")
print(f"Debug: GIST_ID length = {len(GIST_ID)}")
print(f"Debug: GH_TOKEN length = {len(GITHUB_TOKEN)}")

# Rate limiting configuration
RATE_LIMIT_FILE = Path(".last_update_time")
RATE_LIMIT_HOURS = 1


def check_rate_limit() -> bool:
	"""Check if enough time has passed since the last update.

	Returns:
		True if update is allowed, False if rate limited.
	"""
	if not RATE_LIMIT_FILE.exists():
		return True

	try:
		last_update = float(RATE_LIMIT_FILE.read_text().strip())
		time_since_update = time.time() - last_update
		hours_since_update = time_since_update / 3600

		if hours_since_update < RATE_LIMIT_HOURS:
			print(
				f"Rate limited: Last update was {hours_since_update:.2f} hours ago. "
				f"Minimum interval is {RATE_LIMIT_HOURS} hour(s)."
			)
			return False
	except (ValueError, OSError) as e:
		print(f"Warning: Could not read rate limit file: {e}")

	return True


def update_rate_limit_timestamp() -> None:
	"""Update the timestamp of the last successful update."""
	try:
		RATE_LIMIT_FILE.write_text(str(time.time()))
	except OSError as e:
		print(f"Warning: Could not write rate limit file: {e}")


def update_gist(github_token: str, gist_id: str, message: str) -> None:
	"""Update the GitHub Gist with new content.

	Args:
		github_token: GitHub personal access token
		gist_id: ID of the gist to update
		message: Content to write to the gist
	"""
	content_status_normalized = ""

	if CONTENT_STATUS == "current":
		if CONTENT_TYPE == "anime":
			content_status_normalized = "I'm currently watching"
		elif CONTENT_TYPE == "manga":
			content_status_normalized = "I'm currently reading"
	elif CONTENT_STATUS in {"completed", "on-hold", "dropped"}:
		content_status_normalized = f"I have {CONTENT_STATUS.replace('-', ' ')}"
	else:
		print("Your CONTENT_STATUS repository secret has not been properly set.")
		return

	file_name = f"🍖 MAL {CONTENT_TYPE} {content_status_normalized}"
	resp = requests.patch(
		url=f"https://api.github.com/gists/{gist_id}",
		headers={"Authorization": f"token {github_token}", "Accept": "application/json"},
		json={"description": "", "files": {file_name: {"content": message}}},
		timeout=30,
	)

	try:
		resp.raise_for_status()
		print(f"Successfully updated gist: {file_name}")
		update_rate_limit_timestamp()
	except requests.exceptions.HTTPError as error_message:
		print(f"Error updating gist: {error_message}")
		sys.exit(1)


def request_list_mal_api(
	username: str,
	content_type: str,
	mal_client_id: str | None,
	access_token: str | None = None,
) -> list[MALEntry]:
	"""Request anime/manga entries from MAL's official API v2.

	Uses MAL API v2 with either:
	- client_auth (X-MAL-CLIENT-ID header) for public lists
	- OAuth Bearer token for private lists (when access_token is provided)

	API docs: https://myanimelist.net/apiconfig/references/api/v2

	Args:
		username: MyAnimeList username
		content_type: Type of content ('anime' or 'manga')
		mal_client_id: MAL API Client ID (optional if using OAuth)
		access_token: OAuth access token for private list access

	Returns:
		List of MAL entries from the API
	"""
	auth_mode = "OAuth" if access_token else "Client ID"
	print(f"Fetching {content_type} list for user: {username} (using MAL API - {auth_mode})")
	if mal_client_id:
		print(f"Debug: MAL_CLIENT_ID length = {len(mal_client_id)}")

	# MAL API v2 endpoint
	base_url = f"https://api.myanimelist.net/v2/users/{username}/{content_type}list"

	# Use OAuth Bearer token if available, otherwise use Client ID
	if access_token:
		headers = {
			"Authorization": f"Bearer {access_token}",
			"Accept": "application/json",
		}
	elif mal_client_id:
		headers = {
			"X-MAL-CLIENT-ID": mal_client_id,
			"Accept": "application/json",
		}
	else:
		print("Error: No authentication method available.", file=sys.stderr)
		sys.exit(1)

	# Fields to request from the API
	if content_type == "anime":
		fields = "list_status,num_episodes"
	else:
		fields = "list_status,num_chapters,num_volumes"

	all_entries: list[MALEntry] = []
	offset = 0
	limit = 100  # Max is 1000, but smaller batches are more reliable

	while True:
		params: dict[str, str | int] = {
			"fields": fields,
			"limit": limit,
			"offset": offset,
		}

		resp = requests.get(base_url, headers=headers, params=params, timeout=30)

		if resp.status_code == 401:
			print(f"Error: 401 Unauthorized - {resp.text}", file=sys.stderr)
			if access_token:
				print("Your MAL_ACCESS_TOKEN is invalid or expired.", file=sys.stderr)
				print("OAuth tokens expire after a certain period. You may need to refresh it.", file=sys.stderr)
			else:
				print("Your MAL_CLIENT_ID is invalid.", file=sys.stderr)
			sys.exit(1)

		if resp.status_code == 403:
			print(f"Error: 403 Forbidden - {resp.text}", file=sys.stderr)
			print(f"User '{username}' may have a private list. Use OAuth for private list access.", file=sys.stderr)
			sys.exit(1)

		if resp.status_code == 404:
			print(f"Error: User '{username}' not found on MyAnimeList.", file=sys.stderr)
			sys.exit(1)

		if not resp.ok:
			print(f"MAL API error: {resp.status_code} {resp.text}", file=sys.stderr)
			sys.exit(1)

		data = resp.json()
		items = data.get("data", [])

		if not items:
			break

		# Convert MAL API v2 format to our MALEntry format
		for item in items:
			node = item.get("node", {})
			list_status = item.get("list_status", {})

			# Map API status to our status integer
			status_str = list_status.get("status", "")
			status_int = 1 if status_str in ["watching", "reading"] else 2

			if content_type == "anime":
				normalized: MALEntry = {
					"status": status_int,
					"anime_title": node.get("title", ""),
					"anime_num_episodes": node.get("num_episodes", 0) or 0,
					"num_watched_episodes": list_status.get("num_episodes_watched", 0),
					"manga_num_chapters": 0,
					"manga_num_volumes": 0,
					"num_read_chapters": 0,
					"num_read_volumes": 0,
				}
			else:
				normalized = {
					"status": status_int,
					"anime_title": node.get("title", ""),
					"anime_num_episodes": 0,
					"num_watched_episodes": 0,
					"manga_num_chapters": node.get("num_chapters", 0) or 0,
					"manga_num_volumes": node.get("num_volumes", 0) or 0,
					"num_read_chapters": list_status.get("num_chapters_read", 0),
					"num_read_volumes": list_status.get("num_volumes_read", 0),
				}

			all_entries.append(normalized)

		# Check for next page
		paging = data.get("paging", {})
		if "next" not in paging:
			break

		offset += limit
		time.sleep(0.5)  # Be nice to the API

	print(f"Found {len(all_entries)} {content_type} entries from MAL API.")
	return all_entries



def format_progress_line(progress: str | int, title: str, longest_length: int) -> str:
	"""Format a single progress line with emoji and padding.

	Args:
		progress: Progress value (percentage or string like "Ep. 5")
		title: Title of the anime/manga
		longest_length: Length of the longest progress string for alignment

	Returns:
		Formatted line string
	"""
	progress_emoji = ""

	if isinstance(progress, str):
		progress_emoji = "🍳 "
		progress_str = progress
	else:
		if progress >= 80:
			progress_emoji = "🍗 "
		elif progress >= 60:
			progress_emoji = "🐔 "
		elif progress >= 40:
			progress_emoji = "🐥 "
		elif progress >= 20:
			progress_emoji = "🐣 "
		else:
			progress_emoji = "🥚 "
		progress_str = f"{progress}%"

	line = f"{progress_emoji}{progress_str.rjust(longest_length)}: {title}"
	return (line[:50] + "...") if len(line) > 54 else line


def main() -> None:
	"""Main function to fetch MAL data and update the gist."""
	# Check rate limit before proceeding
	if not check_rate_limit():
		print("Skipping update due to rate limit.")
		sys.exit(0)

	# Get MAL API credentials
	mal_client_id = os.environ.get("MAL_CLIENT_ID")
	access_token = os.environ.get("MAL_ACCESS_TOKEN")

	# Require at least one authentication method
	if not mal_client_id and not access_token:
		print("Error: Either MAL_CLIENT_ID or MAL_ACCESS_TOKEN is required.", file=sys.stderr)
		print("- MAL_CLIENT_ID: For public list access (get from https://myanimelist.net/apiconfig)", file=sys.stderr)
		print("- MAL_ACCESS_TOKEN: For private list access (OAuth token)", file=sys.stderr)
		sys.exit(1)

	if access_token:
		print("Using OAuth access token (private list access supported).")
	else:
		print("Using Client ID only (public lists only).")

	content = request_list_mal_api(MAL_USERNAME, CONTENT_TYPE, mal_client_id, access_token)
	progress_data: list[tuple[int, str]] = []
	undefined_progress_data: list[tuple[str, str, int]] = []

	for entry in content:
		if entry["status"] != 1:  # Only process "currently watching/reading" items
			continue

		if CONTENT_TYPE == "anime":
			if entry["anime_num_episodes"] != 0:
				percentage = round(
					entry["num_watched_episodes"] / entry["anime_num_episodes"] * 100
				)
				progress_data.append((percentage, entry["anime_title"]))
			else:
				undefined_progress_data.append(
					(
						f"Ep. {entry['num_watched_episodes']}",
						entry["anime_title"],
						entry["num_watched_episodes"],
					)
				)
		elif CONTENT_TYPE == "manga":
			if entry["manga_num_chapters"] != 0 or entry["manga_num_volumes"] != 0:
				# Use the higher ratio between chapters and volumes
				chapter_ratio = (
					entry["num_read_chapters"] / entry["manga_num_chapters"]
					if entry["manga_num_chapters"] != 0
					else 0
				)
				volume_ratio = (
					entry["num_read_volumes"] / entry["manga_num_volumes"]
					if entry["manga_num_volumes"] != 0
					else 0
				)
				type_ratio = max(chapter_ratio, volume_ratio)
				percentage = round(type_ratio * 100)
				progress_data.append((percentage, entry["anime_title"]))
			else:
				# Use whichever is higher: chapters or volumes
				if entry["num_read_chapters"] > entry["num_read_volumes"]:
					undefined_progress_data.append(
						(
							f"Ch. {entry['num_read_chapters']}",
							entry["anime_title"],
							entry["num_read_chapters"],
						)
					)
				else:
					undefined_progress_data.append(
						(
							f"Vol. {entry['num_read_volumes']}",
							entry["anime_title"],
							entry["num_read_volumes"],
						)
					)
		else:
			print(
				"Your CONTENT_TYPE repository secret has not been properly set.",
				file=sys.stderr,
			)
			sys.exit(1)

	# Sort by progress (highest first)
	progress_data.sort(reverse=True)
	undefined_progress_data.sort(key=lambda x: x[2], reverse=True)

	# Combine and take top 5
	combined_data: list[tuple[int | str, str]] = [
		*progress_data,
		*[(item[0], item[1]) for item in undefined_progress_data],
	]
	displayable_data = combined_data[:5]

	if not displayable_data:
		print("No items to display.")
		sys.exit(0)

	# Calculate longest progress string for alignment
	longest_progress_length = max(
		len(str(item[0]) + "%") if isinstance(item[0], int) else len(item[0])
		for item in displayable_data
	)

	# Format lines
	gist_lines = [
		format_progress_line(progress, title, longest_progress_length)
		for progress, title in displayable_data
	]

	update_gist(GITHUB_TOKEN, GIST_ID, "\n".join(gist_lines))


if __name__ == "__main__":
	main()
