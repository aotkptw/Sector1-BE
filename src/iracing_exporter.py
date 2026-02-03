"""Entry point for exporting iRacing session results."""

from __future__ import annotations

import argparse
import base64
import hashlib
import logging
import os
import sys
from typing import Dict, Optional

import requests

from iracing_api import build_api, build_api_with_session
from csv_export import normalize_results, write_csv

LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://oauth.iracing.com/oauth2/token"
LEGACY_AUTH_URL = "https://members-ng.iracing.com/auth"


def load_env_credentials() -> Dict[str, Optional[str]]:
    required = ["IRACING_CLIENT_ID", "IRACING_CLIENT_SECRET", "IRACING_USERNAME"]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return {
        "IRACING_CLIENT_ID": os.environ["IRACING_CLIENT_ID"],
        "IRACING_CLIENT_SECRET": os.environ["IRACING_CLIENT_SECRET"],
        "IRACING_USERNAME": os.environ["IRACING_USERNAME"],
        "IRACING_PASSWORD": os.getenv("IRACING_PASSWORD"),
        "IRACING_REFRESH_TOKEN": os.getenv("IRACING_REFRESH_TOKEN"),
    }


def mask_secret(secret: str, identifier: str) -> str:
    normalized_id = identifier.strip().lower()
    digest = hashlib.sha256(f"{secret}{normalized_id}".encode("utf-8")).digest()
    return base64.b64encode(digest).decode("utf-8")


def request_refresh_token(credentials: Dict[str, Optional[str]]) -> str:
    refresh_token = credentials.get("IRACING_REFRESH_TOKEN")
    if not refresh_token:
        raise RuntimeError("Missing IRACING_REFRESH_TOKEN for refresh grant.")
    payload = {
        "grant_type": "refresh_token",
        "client_id": credentials["IRACING_CLIENT_ID"],
        "client_secret": mask_secret(
            credentials["IRACING_CLIENT_SECRET"], credentials["IRACING_CLIENT_ID"]
        ),
        "refresh_token": refresh_token,
    }
    LOGGER.debug("Requesting OAuth refresh token from %s", TOKEN_URL)
    response = requests.post(TOKEN_URL, data=payload, timeout=30)
    if response.status_code >= 400:
        LOGGER.error(
            "OAuth refresh token request failed with HTTP %s: %s",
            response.status_code,
            response.text,
        )
    response.raise_for_status()
    token_payload = response.json()
    access_token = token_payload.get("access_token")
    if not access_token:
        raise RuntimeError("OAuth refresh token response did not include an access_token.")
    new_refresh_token = token_payload.get("refresh_token")
    if new_refresh_token:
        LOGGER.info("Received new refresh token; update IRACING_REFRESH_TOKEN for reuse.")
    return access_token


def request_access_token(credentials: Dict[str, Optional[str]]) -> str:
    if not credentials.get("IRACING_PASSWORD"):
        raise RuntimeError("Missing IRACING_PASSWORD for password-limited grant.")
    payload = {
        "grant_type": "password_limited",
        "username": credentials["IRACING_USERNAME"],
        "password": mask_secret(credentials["IRACING_PASSWORD"], credentials["IRACING_USERNAME"]),
        "client_id": credentials["IRACING_CLIENT_ID"],
        "client_secret": mask_secret(
            credentials["IRACING_CLIENT_SECRET"], credentials["IRACING_CLIENT_ID"]
        ),
        "scope": "iracing.auth",
    }
    LOGGER.debug("Requesting OAuth token from %s", TOKEN_URL)
    response = requests.post(
        TOKEN_URL,
        data=payload,
        timeout=30,
    )
    if response.status_code >= 400:
        LOGGER.error(
            "OAuth token request failed with HTTP %s: %s",
            response.status_code,
            response.text,
        )
    response.raise_for_status()
    token_payload = response.json()
    access_token = token_payload.get("access_token")
    if not access_token:
        raise RuntimeError("OAuth token response did not include an access_token.")
    refresh_token = token_payload.get("refresh_token")
    if refresh_token:
        LOGGER.info("Received refresh token; set IRACING_REFRESH_TOKEN to reuse it.")
    return access_token


def authenticate_legacy(credentials: Dict[str, str]) -> requests.Session:
    payload = {
        "email": credentials["IRACING_USERNAME"],
        "password": credentials["IRACING_PASSWORD"],
    }
    LOGGER.debug("Attempting legacy authentication against %s", LEGACY_AUTH_URL)
    session = requests.Session()
    response = session.post(LEGACY_AUTH_URL, json=payload, timeout=30)
    response.raise_for_status()
    return session


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export iRacing session results to CSV.")
    parser.add_argument("--session-id", required=True, help="Subsession/session identifier.")
    parser.add_argument("--output", required=True, help="Output CSV path.")
    parser.add_argument("--format", default="csv", choices=["csv"], help="Export format.")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging.")
    parser.add_argument("--dry-run", action="store_true", help="Validate arguments without API calls.")
    return parser.parse_args()


def configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def main() -> int:
    args = parse_args()
    configure_logging(args.verbose)

    try:
        if args.dry_run:
            LOGGER.info("Dry run enabled; skipping OAuth and API calls.")
            return 0
        credentials = load_env_credentials()
        try:
            if credentials.get("IRACING_REFRESH_TOKEN"):
                access_token = request_refresh_token(credentials)
            else:
                access_token = request_access_token(credentials)
            api = build_api(access_token)
        except requests.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            if status_code != 405:
                raise
            LOGGER.warning(
                "OAuth token request returned HTTP 405. Falling back to legacy auth endpoint."
            )
            session = authenticate_legacy(credentials)
            api = build_api_with_session(session)
        results_payload = api.get_session_results(args.session_id)
        rows = normalize_results(results_payload)
        if not rows:
            LOGGER.warning("No results found for session %s", args.session_id)
        if args.format != "csv":
            raise RuntimeError(f"Unsupported format: {args.format}")
        output_path = write_csv(rows, args.output)
        LOGGER.info("Wrote %s rows to %s", len(rows), output_path)
        return 0
    except Exception as exc:  # pylint: disable=broad-except
        LOGGER.error("Export failed: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
