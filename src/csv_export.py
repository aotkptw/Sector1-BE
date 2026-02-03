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

    _shift_positions_if_zero_based(normalized)
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


def _coerce_mapping(entry: Any) -> Dict[str, Any]:
    if isinstance(entry, dict):
        return entry
    return {"value": entry}


def _is_numeric_position(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _shift_positions_if_zero_based(rows: List[Dict[str, Any]]) -> None:
    positions = [row.get("position") for row in rows if _is_numeric_position(row.get("position"))]
    if positions and min(positions) == 0:
        for row in rows:
            position = row.get("position")
            if _is_numeric_position(position):
                row["position"] = position + 1


def normalize_league_calendar(calendar_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(calendar_payload, list):
        races = calendar_payload
    else:
        races = (
            calendar_payload.get("races")
            or calendar_payload.get("race_schedule")
            or calendar_payload.get("sessions")
            or calendar_payload.get("data")
            or []
        )
    if not races:
        return []

    normalized: List[Dict[str, Any]] = []
    for entry in races:
        entry_data = _coerce_mapping(entry)
        podium = entry_data.get("podium") or entry_data.get("top_three") or []

        def podium_name(index: int) -> Any:
            if len(podium) > index:
                podium_entry = _coerce_mapping(podium[index])
                return (
                    podium_entry.get("display_name")
                    or podium_entry.get("driver_name")
                    or podium_entry.get("name")
                    or podium_entry.get("value")
                )
            return None

        normalized.append(
            {
                "race_number": entry_data.get("race_number")
                if entry_data.get("race_number") is not None
                else entry_data.get("round"),
                "race_name": entry_data.get("race_name") or entry_data.get("event_name"),
                "track": entry_data.get("track_name") or entry_data.get("track"),
                "start_time": entry_data.get("start_time") or entry_data.get("start_date"),
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
        entry_data = _coerce_mapping(entry)
        normalized.append(
            {
                "dataset": dataset,
                "category": category,
                "position": entry_data.get("position")
                if entry_data.get("position") is not None
                else entry_data.get("rank")
                if entry_data.get("rank") is not None
                else entry_data.get("pos"),
                "driver_name": entry_data.get("display_name")
                or entry_data.get("driver_name")
                or entry_data.get("name")
                or entry_data.get("value"),
                "team_name": entry_data.get("team_name") or entry_data.get("team"),
                "club_name": entry_data.get("club_name") or entry_data.get("club"),
                "country": entry_data.get("country") or entry_data.get("country_code"),
                "points": entry_data.get("points")
                if entry_data.get("points") is not None
                else entry_data.get("championship_points"),
                "race_number": None,
                "race_name": None,
                "track": None,
                "start_time": None,
                "winner": None,
                "second_place": None,
                "third_place": None,
                "details": json.dumps(entry_data, default=str),
            }
        )
    _shift_positions_if_zero_based(normalized)
    return normalized


def normalize_league_team_standings(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for entry in rows:
        entry_data = _coerce_mapping(entry)
        normalized.append(
            {
                "dataset": "team-standings",
                "category": "team",
                "position": entry_data.get("position")
                if entry_data.get("position") is not None
                else entry_data.get("rank")
                if entry_data.get("rank") is not None
                else entry_data.get("pos"),
                "driver_name": entry_data.get("display_name")
                or entry_data.get("driver_name")
                or entry_data.get("name")
                or entry_data.get("value"),
                "team_name": entry_data.get("team_name") or entry_data.get("team"),
                "club_name": entry_data.get("club_name") or entry_data.get("club"),
                "country": entry_data.get("country") or entry_data.get("country_code"),
                "points": entry_data.get("points")
                if entry_data.get("points") is not None
                else entry_data.get("championship_points"),
                "race_number": None,
                "race_name": None,
                "track": None,
                "start_time": None,
                "winner": None,
                "second_place": None,
                "third_place": None,
                "details": json.dumps(entry_data, default=str),
            }
        )
    _shift_positions_if_zero_based(normalized)
    return normalized


def normalize_league_points(points_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if isinstance(points_payload, list):
        points_rows = points_payload
    else:
        points_rows = (
            points_payload.get("points")
            or points_payload.get("point_system")
            or points_payload.get("data")
            or []
        )
    normalized: List[Dict[str, Any]] = []
    for entry in points_rows:
        entry_data = _coerce_mapping(entry)
        normalized.append(
            {
                "dataset": "points",
                "category": "point-system",
                "position": entry_data.get("position")
                if entry_data.get("position") is not None
                else entry_data.get("place")
                if entry_data.get("place") is not None
                else entry_data.get("rank"),
                "driver_name": None,
                "team_name": None,
                "club_name": None,
                "country": None,
                "points": entry_data.get("points")
                if entry_data.get("points") is not None
                else entry_data.get("value"),
                "race_number": None,
                "race_name": None,
                "track": None,
                "start_time": None,
                "winner": None,
                "second_place": None,
                "third_place": None,
                "details": json.dumps(entry_data, default=str),
            }
        )
    _shift_positions_if_zero_based(normalized)
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
