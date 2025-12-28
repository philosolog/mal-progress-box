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


def request_chunk(username: str, offset: int, content_type: str) -> list[MALEntry]:
	"""Request a chunk of entries from MyAnimeList.

	Args:
		username: MyAnimeList username
		offset: Offset for pagination
		content_type: Type of content ('anime' or 'manga')

	Returns:
		List of MAL entries
	"""
	url = (
		f"https://myanimelist.net/{content_type}list/{username}/load.json?status=7&offset={offset}"
	)
	resp = requests.get(url, timeout=30)

	if resp.status_code == 400:
		print(
			f"List query error for {username}.\nCheck your repository keys.",
			file=sys.stderr,
		)
		print(resp.status_code, resp.text, file=sys.stderr)
		sys.exit(1)

	return resp.json()


def request_list(username: str, content_type: str) -> list[MALEntry]:
	"""Request all entries from a MyAnimeList user's list.

	Args:
		username: MyAnimeList username
		content_type: Type of content ('anime' or 'manga')

	Returns:
		Complete list of MAL entries
	"""
	all_entries: list[MALEntry] = []
	offset = 0

	while True:
		entries = request_chunk(username, offset, content_type)
		all_entries.extend(entries)

		if len(entries) < 300:
			break

		time.sleep(3)
		offset += 300

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

	content = request_list(MAL_USERNAME, CONTENT_TYPE)
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
