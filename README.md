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