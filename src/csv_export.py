"""CSV export utilities for iRacing results."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


DEFAULT_COLUMNS = [
    "start_time",
    "track",
    "series",
    "season_year",
    "season_quarter",
    "rookie_season",
    "race_week",
    "strength_of_field",
    "special_event_type",
    "fin_pos",
    "car_id",
    "car",
    "car_class_id",
    "car_class",
    "team_id",
    "cust_id",
    "name",
    "start_pos",
    "car_number",
    "out_id",
    "out",
    "interval",
    "laps_led",
    "qualify_time",
    "average_lap_time",
    "fastest_lap_time",
    "fast_lap_number",
    "laps_complete",
    "incidents",
    "points",
    "club_points",
    "division",
    "club_id",
    "club",
    "old_irating",
    "new_irating",
    "old_license_level",
    "old_license_sub_level",
    "new_license_level",
    "new_license_sub_level",
    "series_name",
    "max_fuel_fill_percent",
    "weight_penalty_kg",
    "agg_points",
    "ai",
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

    session_info = _build_session_info(results_payload, race_session)

    normalized: List[Dict[str, Any]] = []
    for entry in results:
        driver_name = (
            entry.get("display_name")
            or entry.get("driver_name")
            or entry.get("name")
            or _name_from_driver_entry(entry.get("driver"))
        )
        normalized.append(
            {
                **session_info,
                "fin_pos": entry.get("finish_position")
                if entry.get("finish_position") is not None
                else entry.get("position"),
                "car_id": entry.get("car_id")
                if entry.get("car_id") is not None
                else entry.get("car"),
                "car": entry.get("car_name") or entry.get("car"),
                "car_class_id": entry.get("car_class_id")
                if entry.get("car_class_id") is not None
                else entry.get("class_id"),
                "car_class": entry.get("car_class_name") or entry.get("class_name"),
                "team_id": entry.get("team_id")
                if entry.get("team_id") is not None
                else entry.get("cust_id"),
                "cust_id": entry.get("cust_id")
                if entry.get("cust_id") is not None
                else _id_from_driver_entry(entry.get("driver")),
                "name": driver_name,
                "driver_name": driver_name,
                "start_pos": entry.get("starting_position")
                if entry.get("starting_position") is not None
                else entry.get("start_position"),
                "car_number": entry.get("car_number")
                if entry.get("car_number") is not None
                else entry.get("car_num"),
                "out_id": entry.get("reason_out_id")
                if entry.get("reason_out_id") is not None
                else entry.get("out_id"),
                "out": entry.get("reason_out")
                or entry.get("reason_out_str")
                or entry.get("out"),
                "interval": entry.get("interval")
                if entry.get("interval") is not None
                else entry.get("interval_to_leader"),
                "laps_led": entry.get("laps_led"),
                "qualify_time": entry.get("qualifying_time")
                if entry.get("qualifying_time") is not None
                else entry.get("qualify_time"),
                "average_lap_time": entry.get("average_lap")
                if entry.get("average_lap") is not None
                else entry.get("average_lap_time"),
                "fastest_lap_time": entry.get("best_lap_time")
                if entry.get("best_lap_time") is not None
                else entry.get("fastest_lap_time"),
                "fast_lap_number": entry.get("best_lap_num")
                if entry.get("best_lap_num") is not None
                else entry.get("fast_lap_number"),
                "laps_complete": entry.get("laps_complete")
                if entry.get("laps_complete") is not None
                else entry.get("laps"),
                "incidents": entry.get("incidents") or entry.get("incident_count"),
                "points": entry.get("points") or entry.get("championship_points"),
                "club_points": entry.get("club_points"),
                "division": entry.get("division"),
                "club_id": entry.get("club_id"),
                "club": entry.get("club_name") or entry.get("club"),
                "old_irating": entry.get("oldi_rating")
                if entry.get("oldi_rating") is not None
                else entry.get("old_irating"),
                "new_irating": entry.get("newi_rating")
                if entry.get("newi_rating") is not None
                else entry.get("new_irating"),
                "old_license_level": entry.get("old_license_level"),
                "old_license_sub_level": entry.get("old_sub_level")
                if entry.get("old_sub_level") is not None
                else entry.get("old_license_sub_level"),
                "new_license_level": entry.get("new_license_level"),
                "new_license_sub_level": entry.get("new_sub_level")
                if entry.get("new_sub_level") is not None
                else entry.get("new_license_sub_level"),
                "series_name": entry.get("series_name") or session_info.get("series"),
                "max_fuel_fill_percent": entry.get("max_fuel_fill_percent")
                if entry.get("max_fuel_fill_percent") is not None
                else entry.get("max_fuel_pct"),
                "weight_penalty_kg": entry.get("weight_penalty_kg")
                if entry.get("weight_penalty_kg") is not None
                else entry.get("weight_penalty"),
                "agg_points": entry.get("agg_points")
                if entry.get("agg_points") is not None
                else entry.get("points"),
                "ai": entry.get("ai") if entry.get("ai") is not None else entry.get("ai_flag"),
            }
        )

    _shift_positions_if_zero_based(normalized, "fin_pos")
    _shift_positions_if_zero_based(normalized, "start_pos")
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


def _shift_positions_if_zero_based(rows: List[Dict[str, Any]], key: str = "position") -> None:
    positions = [row.get(key) for row in rows if _is_numeric_position(row.get(key))]
    if positions and min(positions) == 0:
        for row in rows:
            position = row.get(key)
            if _is_numeric_position(position):
                row[key] = position + 1


def _build_session_info(results_payload: Dict[str, Any], race_session: Dict[str, Any]) -> Dict[str, Any]:
    season_year = _first_present(
        race_session,
        ["season_year", "series_season_year"],
    )
    season_quarter = _first_present(
        race_session,
        ["season_quarter", "series_season_quarter"],
    )
    return {
        "start_time": _first_present(
            results_payload,
            ["start_time", "session_start_time", "start_time_utc"],
            fallback=_first_present(race_session, ["start_time", "session_start_time"]),
        ),
        "track": _first_present(
            results_payload,
            ["track", "track_name"],
            fallback=_first_present(race_session, ["track", "track_name"]),
        ),
        "series": _first_present(
            results_payload,
            ["series_name", "series"],
            fallback=_first_present(race_session, ["series_name", "series"]),
        ),
        "season_year": season_year,
        "season_quarter": season_quarter,
        "rookie_season": _first_present(
            race_session,
            ["rookie_season", "is_rookie_season"],
        ),
        "race_week": _first_present(race_session, ["race_week_num", "race_week"]),
        "strength_of_field": _first_present(
            race_session,
            ["strength_of_field", "sof"],
        ),
        "special_event_type": _first_present(
            race_session,
            ["special_event_type", "special_event_type_name"],
        ),
    }


def _first_present(
    entry: Dict[str, Any], keys: List[str], fallback: Any = None
) -> Any:
    for key in keys:
        if entry.get(key) is not None:
            return entry.get(key)
    return fallback


def _name_from_driver_entry(driver_entry: Any) -> Any:
    if isinstance(driver_entry, dict):
        return (
            driver_entry.get("display_name")
            or driver_entry.get("driver_name")
            or driver_entry.get("name")
        )
    return None


def _id_from_driver_entry(driver_entry: Any) -> Any:
    if isinstance(driver_entry, dict):
        return driver_entry.get("cust_id") if driver_entry.get("cust_id") is not None else driver_entry.get("id")
    return None


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
