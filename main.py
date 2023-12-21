import os
import sys
import time
import requests

gist_id = os.environ["GIST_ID"]
gh_token = os.environ["GH_TOKEN"]
mal_username = os.environ["MAL_USERNAME"]

def update_gist(gh_token, gist_id, message): # TODO: Ensure the preparation of the Gist.
	data = {
		"description" : "",
		"files" : {"🍖 MyAnimeList progress" : {"content" : message}}
	}
	request = requests.patch(
		url=f"https://api.github.com/gists/{gist_id}",
		headers={
			"Authorization": f"token {gh_token}",
			"Accept": "application/json"
		},
		json=data
	)

	try :
		request.raise_for_status()
	except requests.exceptions.HTTPError as e :
		print(e)
		return "Data retrival error."
def request_chunk(username, offset):
	url = ("https://myanimelist.net/animelist/{username}/load.json?status=7&offset={offset}").format(username=username, offset=offset)
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
	# TODO: Add in-line auto-padding and shortening for longer undefined entries.
	animelist = request_animelist(mal_username)
	currently_watching = []
	progress = []
	undefined_progress = []
	lines = []
	message = ""

	for i in range(10):
		if animelist[i]["status"] == 1:
			if animelist[i]["anime_num_episodes"] != 0:
				progress.append([round(animelist[i]["num_watched_episodes"]/animelist[i]["anime_num_episodes"]*100), animelist[i]["anime_title"]])
			else:
				undefined_progress.append([str(animelist[i]["num_watched_episodes"]) + "/?", animelist[i]["anime_title"], animelist[i]["num_watched_episodes"]])

	progress.sort(reverse=True)
	undefined_progress.sort(key = lambda x: x[2], reverse=True)
	currently_watching = progress + undefined_progress

	for i, v in enumerate(currently_watching):
		title = (v[1][:37] + "...") if len(v[1]) > 40 else v[1]

		if type(v[0]) == str:
			lines.append("🍳 " + str(v[0]) + ": " + title)
		else:
			status_emoji = ""

			if v[0] >= 80:
				status_emoji = "🍗 "
			elif v[0] >= 60:
				status_emoji = "🐔 "
			elif v[0] >= 40:
				status_emoji = "🐥 "
			elif v[0] >= 20:
				status_emoji = "🐣 "
			elif v[0] >= 0:
				status_emoji = "🥚 "

			lines.append(status_emoji + str(v[0]) + "%" + ": " + title)

	for i, v in enumerate(lines):
		if i < len(lines) - 1:
			message += v + "\n"
		else:
			message += v

	update_gist(gh_token, gist_id, message)

if __name__ == "__main__":
	main()