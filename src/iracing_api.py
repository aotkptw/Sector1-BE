"""iRacing data server client helpers."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional

import requests

LOGGER = logging.getLogger(__name__)


@dataclass
class IRacingConfig:
    base_url: str
    access_token: Optional[str] = None
    session: Optional[requests.Session] = None


class IRacingAPI:
    """Client for iRacing data server endpoints."""

    def __init__(self, config: IRacingConfig) -> None:
        self._config = config
        self._session = self._config.session or requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        if self._config.access_token:
            self._session.headers.update({"Authorization": f"Bearer {self._config.access_token}"})
        elif not self._config.session:
            raise ValueError("IRacingAPI requires an access token or an authenticated session.")

    def _fetch_data(self, endpoint: str, params: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._config.base_url}{endpoint}"
        LOGGER.debug("Requesting data from %s", url)
        response = self._session.get(url, params=params, timeout=30)
        response.raise_for_status()
        payload = response.json()
        link = payload.get("link")
        if not link:
            data_payload = payload.get("data")
            if data_payload is not None:
                if isinstance(data_payload, dict):
                    LOGGER.debug(
                        "Response from %s included data inline; skipping link fetch.", endpoint
                    )
                    return data_payload
                LOGGER.debug(
                    "Response from %s included inline data payload; returning raw response.",
                    endpoint,
                )
                return payload
            if any(key in payload for key in ("standings", "team_standings", "points", "point_system")):
                LOGGER.debug(
                    "Response from %s included expected data keys inline; skipping link fetch.",
                    endpoint,
                )
                return payload
            raise ValueError(f"Response from {endpoint} did not include a data link.")
        LOGGER.debug("Fetching payload from %s", link)
        results_session = requests.Session()
        results_session.cookies.update(self._session.cookies)
        results_session.headers.update({"Accept": "application/json"})
        results_response = results_session.get(link, timeout=30)
        results_response.raise_for_status()
        return results_response.json()

    def get_session_results(self, session_id: str) -> Dict[str, Any]:
        """Fetch session results for the provided subsession/session id."""
        return self._fetch_data("/data/results/get", {"subsession_id": session_id})

    def get_league(self, league_id: str) -> Dict[str, Any]:
        """Fetch league metadata."""
        return self._fetch_data("/data/league/get", {"league_id": league_id})

    def get_league_seasons(self, league_id: str) -> Dict[str, Any]:
        """Fetch available seasons for a league."""
        return self._fetch_data("/data/league/seasons", {"league_id": league_id})

    def get_league_season_standings(
        self, league_id: str, season_id: str, standings_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Fetch league season standings; standings_type can specify overall/pro/am/nation."""
        params: Dict[str, Any] = {"league_id": league_id, "season_id": season_id}
        if standings_type:
            params["standings_type"] = standings_type
        return self._fetch_data("/data/league/season/standings", params)

    def get_league_season_team_standings(self, league_id: str, season_id: str) -> Dict[str, Any]:
        """Fetch league season team standings."""
        return self._fetch_data(
            "/data/league/season/team_standings",
            {"league_id": league_id, "season_id": season_id},
        )

    def get_league_season_points(self, league_id: str, season_id: str) -> Dict[str, Any]:
        """Fetch league season points system."""
        return self._fetch_data(
            "/data/league/season/points",
            {"league_id": league_id, "season_id": season_id},
        )

    def get_league_season_race_schedule(self, league_id: str, season_id: str) -> Dict[str, Any]:
        """Fetch league season race calendar."""
        return self._fetch_data(
            "/data/league/season/race_schedule",
            {"league_id": league_id, "season_id": season_id},
        )


def build_base_url() -> str:
    return "https://members-ng.iracing.com"


def build_api(access_token: str, base_url: Optional[str] = None) -> IRacingAPI:
    config = IRacingConfig(base_url=base_url or build_base_url(), access_token=access_token)
    return IRacingAPI(config)


def build_api_with_session(session: requests.Session, base_url: Optional[str] = None) -> IRacingAPI:
    config = IRacingConfig(base_url=base_url or build_base_url(), session=session)
    return IRacingAPI(config)
