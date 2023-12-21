import os
import sys
import time
import requests

gist_id = os.environ["GIST_ID"]
github_token = os.environ["GH_TOKEN"]
mal_username = os.environ["MAL_USERNAME"]

def update_gist(github_token: str, gist_id: str, message: str) -> None: # TODO: Ensure the preparation of the Gist.
	request = requests.patch(
		url = f"https://api.github.com/gists/{gist_id}",
		headers = {
			"Authorization": f"token {github_token}",
			"Accept": "application/json"
		},
		json = {
			"description": "",
			"files": {
				"🍖 MyAnimeList progress": {
					"content": message
				}
			}
		}
	)

	try :
		request.raise_for_status()
	except requests.exceptions.HTTPError as errorMessage:
		print(errorMessage)

		return "Data retrival error."
def request_chunk(username, offset):
	url = f"https://myanimelist.net/animelist/{username}/load.json?status=7&offset={offset}"
	resp = requests.get(url)

	if resp.status_code == 400:
		print("List query error for {}.".format(username), file=sys.stderr)
		print(resp.status_code, resp.text, file=sys.stderr)
		sys.exit(1)

	return resp.json()
def request_animelist(username):
	all_entries = []
	offset = 0

	while True:
		entries = request_chunk(username, offset)
		all_entries.extend(entries)

		if len(entries) < 300:
			break

		time.sleep(3)

		offset += 300
	return all_entries
def main():
	animelist = request_animelist(mal_username)
	progress_data = []
	undefined_progress_data = []
	longest_progress_string_length = 0
	gist_code = []

	for i in range(10):
		if animelist[i]["status"] == 1:
			if animelist[i]["anime_num_episodes"] != 0:
				progress_data.append([str(round(animelist[i]["num_watched_episodes"]/animelist[i]["anime_num_episodes"]*100)) + "%", animelist[i]["anime_title"]])
			else:
				undefined_progress_data.append([str(animelist[i]["num_watched_episodes"]) + "/?", animelist[i]["anime_title"], animelist[i]["num_watched_episodes"]])

	progress_data.sort(reverse=True)
	undefined_progress_data.sort(key = lambda x: x[2], reverse=True)
	displayable_data = progress_data + undefined_progress_data

	for v in displayable_data[:5]: # Uses data to fill only the first 5 lines of Gist code.
		longest_progress_string_length = max(longest_progress_string_length, len(v[0]))
	for i, v in enumerate(displayable_data[:5]):
		progress_emoji = ""

		if v[0].find("/?") != -1:
			progress_emoji = "🍳 "
		elif v[0] >= 80:
			progress_emoji = "🍗 "
		elif v[0] >= 60:
			progress_emoji = "🐔 "
		elif v[0] >= 40:
			progress_emoji = "🐥 "
		elif v[0] >= 20:
			progress_emoji = "🐣 "
		elif v[0] >= 0:
			progress_emoji = "🥚 "

		line = progress_emoji + str(v[0]).rjust(longest_progress_string_length, " ") + ": " + v[1]
		truncated_line = (line[:47] + "...") if len(line) > 50 else line

		gist_code.append(truncated_line)

	update_gist(github_token, gist_id, '\n'.join(gist_code))

if __name__ == "__main__":
	main()