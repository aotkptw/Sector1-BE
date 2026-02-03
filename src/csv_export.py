"""CSV export utilities for iRacing results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


DEFAULT_COLUMNS = [
    "driver_name",
    "car",
    "car_class",
    "position",
    "laps_complete",
    "incidents",
    "points",
]

DEFAULT_CALENDAR_COLUMNS = [
    "race_number",
    "race_name",
    "track",
    "start_time",
    "winner",
    "second_place",
    "third_place",
]

DEFAULT_LEAGUE_ALL_COLUMNS = [
    "dataset",
    "category",
    "position",
    "driver_name",
    "team_name",
    "club_name",
    "country",
    "points",
    "race_number",
    "race_name",
    "track",
    "start_time",
    "winner",
    "second_place",
    "third_place",
    "details",
]


def normalize_results(results_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    session_results = results_payload.get("session_results") or []
    if not session_results:
        return []

    # Prefer the race session if present, otherwise fall back to the first entry.
    race_session = next(
        (entry for entry in session_results if entry.get("simsession_name", "").lower() == "race"),
        session_results[0],
    )
    results = race_session.get("results") or []

    normalized: List[Dict[str, Any]] = []
    for entry in results:
        normalized.append(
            {
                "driver_name": entry.get("display_name")
                or entry.get("driver_name")
                or entry.get("name"),
                "car": entry.get("car_name") or entry.get("car"),
                "car_class": entry.get("car_class_name") or entry.get("class_name"),
                "position": entry.get("finish_position")
                if entry.get("finish_position") is not None
                else entry.get("position"),
                "laps_complete": entry.get("laps_complete")
                if entry.get("laps_complete") is not None
                else entry.get("laps"),
                "incidents": entry.get("incidents") or entry.get("incident_count"),
                "points": entry.get("points") or entry.get("championship_points"),
            }
        )

    return normalized


def write_csv(rows: Iterable[Dict[str, Any]], output_path: str, columns: List[str] | None = None) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    columns_to_use = columns or DEFAULT_COLUMNS

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns_to_use)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in columns_to_use})

    return path


def normalize_league_calendar(calendar_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    races = calendar_payload.get("races") or calendar_payload.get("race_schedule") or []
    if not races:
        return []

    normalized: List[Dict[str, Any]] = []
    for entry in races:
        podium = entry.get("podium") or entry.get("top_three") or []
        def podium_name(index: int) -> Any:
            if len(podium) > index:
                return podium[index].get("display_name") or podium[index].get("driver_name")
            return None

        normalized.append(
            {
                "race_number": entry.get("race_number")
                if entry.get("race_number") is not None
                else entry.get("round"),
                "race_name": entry.get("race_name") or entry.get("event_name"),
                "track": entry.get("track_name") or entry.get("track"),
                "start_time": entry.get("start_time") or entry.get("start_date"),
                "winner": podium_name(0),
                "second_place": podium_name(1),
                "third_place": podium_name(2),
            }
        )

    return normalized


def normalize_league_standings(
    rows: List[Dict[str, Any]], dataset: str, category: str
) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for entry in rows:
        normalized.append(
            {
                "dataset": dataset,
                "category": category,
                "position": entry.get("position")
                if entry.get("position") is not None
                else entry.get("rank")
                if entry.get("rank") is not None
                else entry.get("pos"),
                "driver_name": entry.get("display_name")
                or entry.get("driver_name")
                or entry.get("name"),
                "team_name": entry.get("team_name") or entry.get("team"),
                "club_name": entry.get("club_name") or entry.get("club"),
                "country": entry.get("country") or entry.get("country_code"),
                "points": entry.get("points")
                if entry.get("points") is not None
                else entry.get("championship_points"),
                "race_number": None,
                "race_name": None,
                "track": None,
                "start_time": None,
                "winner": None,
                "second_place": None,
                "third_place": None,
                "details": json.dumps(entry, default=str),
            }
        )
    return normalized


def normalize_league_team_standings(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for entry in rows:
        normalized.append(
            {
                "dataset": "team-standings",
                "category": "team",
                "position": entry.get("position")
                if entry.get("position") is not None
                else entry.get("rank")
                if entry.get("rank") is not None
                else entry.get("pos"),
                "driver_name": entry.get("display_name")
                or entry.get("driver_name")
                or entry.get("name"),
                "team_name": entry.get("team_name") or entry.get("team"),
                "club_name": entry.get("club_name") or entry.get("club"),
                "country": entry.get("country") or entry.get("country_code"),
                "points": entry.get("points")
                if entry.get("points") is not None
                else entry.get("championship_points"),
                "race_number": None,
                "race_name": None,
                "track": None,
                "start_time": None,
                "winner": None,
                "second_place": None,
                "third_place": None,
                "details": json.dumps(entry, default=str),
            }
        )
    return normalized


def normalize_league_points(points_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    points_rows = points_payload.get("points") or points_payload.get("point_system") or []
    normalized: List[Dict[str, Any]] = []
    for entry in points_rows:
        normalized.append(
            {
                "dataset": "points",
                "category": "point-system",
                "position": entry.get("position")
                if entry.get("position") is not None
                else entry.get("place")
                if entry.get("place") is not None
                else entry.get("rank"),
                "driver_name": None,
                "team_name": None,
                "club_name": None,
                "country": None,
                "points": entry.get("points") if entry.get("points") is not None else entry.get("value"),
                "race_number": None,
                "race_name": None,
                "track": None,
                "start_time": None,
                "winner": None,
                "second_place": None,
                "third_place": None,
                "details": json.dumps(entry, default=str),
            }
        )
    return normalized


def normalize_league_calendar_all(calendar_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    races = normalize_league_calendar(calendar_payload)
    normalized: List[Dict[str, Any]] = []
    for entry in races:
        normalized.append(
            {
                "dataset": "calendar",
                "category": "race",
                "position": None,
                "driver_name": None,
                "team_name": None,
                "club_name": None,
                "country": None,
                "points": None,
                "race_number": entry.get("race_number"),
                "race_name": entry.get("race_name"),
                "track": entry.get("track"),
                "start_time": entry.get("start_time"),
                "winner": entry.get("winner"),
                "second_place": entry.get("second_place"),
                "third_place": entry.get("third_place"),
                "details": json.dumps(entry, default=str),
            }
        )
    return normalized
