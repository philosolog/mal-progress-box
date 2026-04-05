# MAL Progress Box 🍖

**A GitHub Gist updater for tracking a user's MyAnimeList stats.** It automatically updates a GitHub Gist with your top 5 anime or manga progress entries.

## Features

- Updates a Gist hourly via GitHub Actions
- Uses emoji to represent progress levels
	- 🥚 0-19% complete
	- 🐣 20-39% complete
	- 🐥 40-59% complete
	- 🐔 60-79% complete
	- 🍗 80-100% complete
	- 🍳 Unknown total (shows episode/chapter count)
- Built with [mypy](https://mypy-lang.org/) typechecking and [ruff](https://docs.astral.sh/ruff/) for linting & formatting

## Setup

### Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) package manager
- A GitHub account with a personal access token
- A MyAnimeList account

### Installation

1. **Create a GitHub Gist**

   - Go to https://gist.github.com/
   - Create a new public gist
   - Note the gist ID from the URL (e.g., `https://gist.github.com/username/{GIST_ID}`)

2. **Create a GitHub Personal Access Token**

   - Go to Settings → Developer settings → Personal access tokens → Fine-grained tokens
   - Generate a new token with **Gists: Read and write** permission
   - Copy the token

3. **Configure Repository Secrets**

   In your GitHub repository, go to Settings → Secrets and variables → Actions, and add:

   - `GIST_ID`: Your gist ID
   - `GH_TOKEN`: Your GitHub personal access token
   - `MAL_USERNAME`: Your MyAnimeList username
   - `CONTENT_TYPE`: Either `anime` or `manga`
   - `CONTENT_STATUS`: One of `current`, `completed`, `on-hold`, or `dropped`

### Private MAL Lists

For private MyAnimeList data, do a one-time OAuth grant in the terminal and store a refresh token. The helper now follows the MAL docs more closely:

- PKCE with `code_challenge_method=plain`
- `state` on the authorization request
- optional `redirect_uri` if your MAL app has only one registered redirect
- token endpoint support for both documented client-auth schemes

```bash
python scripts/get_mal_tokens.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET
```

If your MAL app has exactly one redirect URI registered, you can omit `--redirect-uri`. If it has multiple, pass the exact registered value:

```bash
python scripts/get_mal_tokens.py --client-id YOUR_CLIENT_ID --client-secret YOUR_CLIENT_SECRET --redirect-uri https://localhost/
```

Add these GitHub Actions secrets:

- `MAL_CLIENT_ID`
- `MAL_CLIENT_SECRET`
- `MAL_REFRESH_TOKEN`
- `MAL_CLIENT_AUTH_METHOD` (optional: `auto`, `body`, or `basic`)

The helper prints a login URL. After you approve the app, paste back either the `code` value or the full redirected URL. If `MAL_CLIENT_ID` and `MAL_REFRESH_TOKEN` are present, the script refreshes an access token automatically before requesting your MAL list.
