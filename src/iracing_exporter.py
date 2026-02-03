"""Entry point for exporting iRacing session results."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Dict

import requests

from iracing_api import build_api
from csv_export import normalize_results, write_csv

LOGGER = logging.getLogger(__name__)

TOKEN_URL = "https://members-ng.iracing.com/oauth2/token"


def load_env_credentials() -> Dict[str, str]:
    required = [
        "IRACING_CLIENT_ID",
        "IRACING_CLIENT_SECRET",
        "IRACING_USERNAME",
        "IRACING_PASSWORD",
    ]
    missing = [key for key in required if not os.getenv(key)]
    if missing:
        raise RuntimeError(f"Missing required environment variables: {', '.join(missing)}")
    return {key: os.environ[key] for key in required}


def request_access_token(credentials: Dict[str, str]) -> str:
    payload = {
        "grant_type": "password",
        "username": credentials["IRACING_USERNAME"],
        "password": credentials["IRACING_PASSWORD"],
        "audience": "data-server",
    }
    LOGGER.debug("Requesting OAuth token from %s", TOKEN_URL)
    response = requests.post(
        TOKEN_URL,
        data=payload,
        auth=(credentials["IRACING_CLIENT_ID"], credentials["IRACING_CLIENT_SECRET"]),
        timeout=30,
    )
    response.raise_for_status()
    token_payload = response.json()
    access_token = token_payload.get("access_token")
    if not access_token:
        raise RuntimeError("OAuth token response did not include an access_token.")
    return access_token


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
        access_token = request_access_token(credentials)
        api = build_api(access_token)
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
