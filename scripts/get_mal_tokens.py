"""Minimal terminal helper for obtaining MAL OAuth tokens."""

from __future__ import annotations

import argparse
import base64
import json
import secrets
import string
import sys
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTH_URL = "https://myanimelist.net/v1/oauth2/authorize"
TOKEN_URL = "https://myanimelist.net/v1/oauth2/token"


def generate_code_verifier(length: int = 64) -> str:
	"""Generate a MAL-compatible PKCE verifier."""
	alphabet = string.ascii_letters + string.digits + "-._~"
	return "".join(secrets.choice(alphabet) for _ in range(length))


def build_auth_url(
	client_id: str,
	code_verifier: str,
	state: str,
	redirect_uri: str | None = None,
) -> str:
	"""Build the MAL authorization URL."""
	params = {
		"response_type": "code",
		"client_id": client_id,
		"code_challenge": code_verifier,
		"code_challenge_method": "plain",
		"state": state,
	}
	if redirect_uri:
		params["redirect_uri"] = redirect_uri
	return f"{AUTH_URL}?{urlencode(params)}"


def parse_callback(value: str, expected_state: str) -> str:
	"""Accept either the raw code or the full callback URL."""
	value = value.strip()
	if not value:
		raise ValueError("No authorization code provided.")
	if "://" not in value:
		return value

	query = parse_qs(urlparse(value).query)
	code = query.get("code", [None])[0]
	state = query.get("state", [None])[0]
	if not code:
		raise ValueError("The pasted URL did not include a code parameter.")
	if state and state != expected_state:
		raise ValueError("The pasted callback URL had an unexpected state value.")
	return code


def token_request_payload(
	code: str,
	code_verifier: str,
	redirect_uri: str | None = None,
) -> dict[str, str]:
	"""Build the shared form body for the token request."""
	data = {
		"grant_type": "authorization_code",
		"code": code,
		"code_verifier": code_verifier,
	}
	if redirect_uri:
		data["redirect_uri"] = redirect_uri
	return data


def request_tokens(
	data: dict[str, str],
	client_id: str,
	client_secret: str | None,
	auth_scheme: str,
) -> dict[str, str]:
	"""Exchange a token request using one of MAL's documented client auth schemes."""
	body_headers = {
		"Accept": "application/json",
		"Content-Type": "application/x-www-form-urlencoded",
	}

	def send_with_body() -> requests.Response:
		body = {"client_id": client_id, **data}
		if client_secret:
			body["client_secret"] = client_secret
		return requests.post(TOKEN_URL, data=body, headers=body_headers, timeout=30)

	def send_with_basic() -> requests.Response:
		if not client_secret:
			raise ValueError("HTTP Basic client auth requires a client secret.")
		credentials = base64.b64encode(f"{client_id}:{client_secret}".encode("utf-8")).decode("ascii")
		return requests.post(
			TOKEN_URL,
			data=data,
			headers={
				**body_headers,
				"Authorization": f"Basic {credentials}",
			},
			timeout=30,
		)

	# MAL docs describe both client-auth approaches. Try the request-body form first,
	# then fall back to HTTP Basic when auto mode is selected.
	if auth_scheme == "body":
		resp = send_with_body()
	elif auth_scheme == "basic":
		resp = send_with_basic()
	else:
		resp = send_with_body()
		if resp.status_code == 401 and client_secret:
			resp = send_with_basic()

	resp.raise_for_status()
	payload = resp.json()
	return {
		"access_token": payload.get("access_token", ""),
		"refresh_token": payload.get("refresh_token", ""),
	}


def main() -> int:
	parser = argparse.ArgumentParser(description="Get MAL OAuth tokens from the terminal.")
	parser.add_argument("--client-id", required=True, help="MyAnimeList client ID")
	parser.add_argument("--client-secret", help="MyAnimeList client secret")
	parser.add_argument(
		"--auth-scheme",
		choices=("auto", "body", "basic"),
		default="auto",
		help="Token endpoint client-auth scheme from the MAL docs",
	)
	parser.add_argument(
		"--redirect-uri",
		help="Exact redirect URI configured in your MAL app; omit if the app has only one registered URI",
	)
	args = parser.parse_args()

	code_verifier = generate_code_verifier()
	state = secrets.token_urlsafe(24)
	auth_url = build_auth_url(args.client_id, code_verifier, state, args.redirect_uri)

	print("Open this URL in your browser, log in, and approve the app:\n")
	print(auth_url)
	print()
	print("After approval, copy either the `code` value or the full redirected URL and paste it here.")

	try:
		code = parse_callback(input("> "), state)
		tokens = request_tokens(
			data=token_request_payload(code, code_verifier, args.redirect_uri),
			client_id=args.client_id,
			client_secret=args.client_secret,
			auth_scheme=args.auth_scheme,
		)
	except requests.HTTPError as exc:
		status = exc.response.status_code if exc.response is not None else "?"
		body = exc.response.text if exc.response is not None else str(exc)
		print(f"Token exchange failed: {status} {body}", file=sys.stderr)
		return 1
	except Exception as exc:
		print(f"OAuth flow failed: {exc}", file=sys.stderr)
		return 1

	print("\nTokens received:\n")
	print(json.dumps(tokens, indent=2))
	print()
	print("GitHub Actions secrets:")
	print(f"MAL_CLIENT_ID={args.client_id}")
	if args.client_secret:
		print("MAL_CLIENT_SECRET=<your existing client secret>")
	print(f"MAL_REFRESH_TOKEN={tokens['refresh_token']}")
	print(f"MAL_ACCESS_TOKEN={tokens['access_token']}")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
