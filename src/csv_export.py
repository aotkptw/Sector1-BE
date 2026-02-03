"""CSV export utilities for iRacing results."""

from __future__ import annotations

import csv
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
