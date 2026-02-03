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

    @staticmethod
    def _extract_link(value: Any) -> Optional[str]:
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            for key in ("link", "href", "url"):
                link_value = value.get(key)
                if isinstance(link_value, str) and link_value:
                    return link_value
        return None

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
        link = self._extract_link(payload)
        if not link:
            data_payload = payload.get("data")
            if isinstance(data_payload, dict):
                nested_link = self._extract_link(data_payload)
                if not nested_link:
                    nested_data = data_payload.get("data")
                    if isinstance(nested_data, dict):
                        nested_link = self._extract_link(nested_data)
                    elif isinstance(nested_data, list):
                        LOGGER.debug(
                            "Response from %s included nested data list; returning under 'data' key.",
                            endpoint,
                        )
                        return {"data": nested_data}
                if nested_link:
                    LOGGER.debug(
                        "Response from %s included a data link inside payload data; fetching.",
                        endpoint,
                    )
                    link = nested_link
                else:
                    LOGGER.debug("Response from %s included data inline; skipping link fetch.", endpoint)
                    return data_payload
            if link:
                LOGGER.debug("Fetching payload from %s", link)
                results_session = requests.Session()
                results_session.cookies.update(self._session.cookies)
                results_session.headers.update({"Accept": "application/json"})
                results_response = results_session.get(link, timeout=30)
                results_response.raise_for_status()
                return results_response.json()
            if data_payload in (None, [], ""):
                detail = payload.get("message") or payload.get("error") or payload.get(
                    "error_description"
                )
                LOGGER.warning(
                    "Response from %s did not include a data link or inline data%s; returning empty payload.",
                    endpoint,
                    f" ({detail})" if detail else "",
                )
                return {}
            if isinstance(data_payload, list):
                LOGGER.debug(
                    "Response from %s included data inline as a list; returning under 'data' key.",
                    endpoint,
                )
                return {"data": data_payload}
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

    def get_league_season_standings(self, league_id: str, season_id: str) -> Dict[str, Any]:
        """Fetch league season standings."""
        params: Dict[str, Any] = {"league_id": league_id, "season_id": season_id}
        return self._fetch_data("/data/league/season_standings", params)

    def get_league_season_team_standings(self, league_id: str, season_id: str) -> Dict[str, Any]:
        """Fetch league season team standings."""
        return self._fetch_data(
            "/data/league/season_standings",
            {"league_id": league_id, "season_id": season_id},
        )

    def get_league_season_points(self, league_id: str, season_id: str) -> Dict[str, Any]:
        """Fetch league season points system."""
        return self._fetch_data(
            "/data/league/get_points_systems",
            {"league_id": league_id, "season_id": season_id},
        )

    def get_league_season_race_schedule(self, league_id: str, season_id: str) -> Dict[str, Any]:
        """Fetch league season race calendar."""
        return self._fetch_data(
            "/data/league/season_sessions",
            {"league_id": league_id, "season_id": season_id},
        )

    def get_documentation(self, doc_path: str = "") -> Dict[str, Any]:
        """Fetch API documentation for the provided doc path."""
        normalized = doc_path.strip("/")
        endpoint = "/data/doc"
        if normalized:
            endpoint = f"{endpoint}/{normalized}"
        return self._fetch_data(endpoint, {})


def build_base_url() -> str:
    return "https://members-ng.iracing.com"


def build_api(access_token: str, base_url: Optional[str] = None) -> IRacingAPI:
    config = IRacingConfig(base_url=base_url or build_base_url(), access_token=access_token)
    return IRacingAPI(config)


def build_api_with_session(session: requests.Session, base_url: Optional[str] = None) -> IRacingAPI:
    config = IRacingConfig(base_url=base_url or build_base_url(), session=session)
    return IRacingAPI(config)
