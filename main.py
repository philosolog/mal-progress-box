import os
import sys
import time
import requests

gist_id = os.environ["GIST_ID"]
github_token = os.environ["GH_TOKEN"]
mal_username = os.environ["MAL_USERNAME"]
content_type = os.environ["CONTENT_TYPE"]

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
				"🍖 Mycontent progress": {
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
def request_chunk(username, offset, type):
	url = f"https://mycontent.net/{type}list/{username}/load.json?status=7&offset={offset}"
	resp = requests.get(url)

	if resp.status_code == 400:
		print("List query error for {}.".format(username), file=sys.stderr)
		print(resp.status_code, resp.text, file=sys.stderr)
		sys.exit(1)

	return resp.json()
def request_list(username):
	all_entries = []
	offset = 0

	while True:
		entries = request_chunk(username, offset, content_type)
		all_entries.extend(entries)

		if len(entries) < 300:
			break

		time.sleep(3)

		offset += 300
	return all_entries
def main():
	content = request_list(mal_username)
	progress_data = []
	undefined_progress_data = []
	longest_progress_string_length = 0
	gist_code = []

	for i in range(10):
		if content[i]["status"] == 1:
			if content_type == "anime":
				if content[i]["anime_num_episodes"] != 0:
					progress_data.append([round(content[i]["num_watched_episodes"]/content[i]["anime_num_episodes"]*100), content[i]["anime_title"]])
				else:
					undefined_progress_data.append([str(content[i]["num_watched_episodes"]) + " ep.", content[i]["anime_title"], content[i]["num_watched_episodes"]])
			elif content_type == "manga":
				if content[i]["anime_num_episodes"] != 0:
					type_ratio = []

					if content[i]["num_read_chapters"]/content[i]["manga_num_chapters"] > content[i]["num_read_chapters"]/content[i]["manga_num_volumes"]:
						type_ratio = content[i]["num_read_chapters"]/content[i]["manga_num_chapters"]
					else:
						type_ratio = content[i]["num_read_chapters"]/content[i]["manga_num_volumes"]

					progress_data.append([round(type_ratio*100), content[i]["anime_title"]])
				else:
					# TODO: Properly handle ch. versus vol. for later sorting.
					num_read_type = []

					if content[i]["num_read_chapters"] > content[i]["num_read_volumes"]:
						num_read_type = ["num_read_chapters", "ch."]
					else:
						num_read_type = ["num_read_volumes", "vol."]

					undefined_progress_data.append([str(content[i][num_read_type[0]]) + num_read_type[1], content[i]["manga_title"], content[i][num_read_type[0]]])
			else:
				print("Your CONTENT_TYPE repository secret is not properly set.", file=sys.stderr)

	progress_data.sort(reverse=True)
	undefined_progress_data.sort(key = lambda x: x[2], reverse=True)
	displayable_data = progress_data + undefined_progress_data

	# Uses data to fill only the first 5 lines of Gist code.
	for v in displayable_data[:5]:
		test_length = (len(v[0])) if type(v[0]) == str else len(str(v[0]) + "%")

		longest_progress_string_length = max(longest_progress_string_length, test_length)
	for i, v in enumerate(displayable_data[:5]):
		progress_emoji = ""

		if type(v[0]) == str:
			progress_emoji = "🍳 "
		else:
			if v[0] >= 80:
				progress_emoji = "🍗 "
			elif v[0] >= 60:
				progress_emoji = "🐔 "
			elif v[0] >= 40:
				progress_emoji = "🐥 "
			elif v[0] >= 20:
				progress_emoji = "🐣 "
			elif v[0] >= 0:
				progress_emoji = "🥚 "
			
			v[0] = str(v[0]) + "%"

		line = progress_emoji + v[0].rjust(longest_progress_string_length, " ") + ": " + v[1]
		truncated_line = (line[:50] + "...") if len(line) > 54 else line

		gist_code.append(truncated_line)

	update_gist(github_token, gist_id, '\n'.join(gist_code))

if __name__ == "__main__":
	main()