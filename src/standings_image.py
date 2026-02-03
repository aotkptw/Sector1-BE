"""PNG rendering utilities for league standings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Mapping, Sequence


def _ensure_pillow() -> None:
    try:
        import PIL  # noqa: F401
    except ModuleNotFoundError as exc:  # pragma: no cover - runtime dependency
        raise RuntimeError(
            "PNG rendering requires Pillow. Install it with `pip install Pillow`."
        ) from exc


def _coerce_mapping(entry: Any) -> Mapping[str, Any]:
    if isinstance(entry, Mapping):
        return entry
    return {"value": entry}


def _pick_value(entry: Mapping[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in entry and entry[key] is not None:
            return entry[key]
    return None


def _normalize_rows(
    rows: Iterable[Mapping[str, Any]],
    name_keys: Sequence[str],
) -> List[Mapping[str, Any]]:
    normalized = []
    for entry in rows:
        entry_data = _coerce_mapping(entry)
        normalized.append(
            {
                "position": _pick_value(entry_data, ("position", "rank", "pos", "place")),
                "name": _pick_value(entry_data, name_keys),
                "points": _pick_value(entry_data, ("points", "championship_points", "value")),
            }
        )
    _shift_positions_if_zero_based(normalized)
    return normalized


def _shift_positions_if_zero_based(rows: List[Mapping[str, Any]]) -> None:
    positions = [
        entry.get("position")
        for entry in rows
        if isinstance(entry.get("position"), (int, float))
        and not isinstance(entry.get("position"), bool)
    ]
    if positions and min(positions) == 0:
        for entry in rows:
            position = entry.get("position")
            if isinstance(position, (int, float)) and not isinstance(position, bool):
                entry["position"] = position + 1


def render_standings_png(
    rows: Iterable[Mapping[str, Any]],
    output_path: str,
    title: str,
    name_keys: Sequence[str],
) -> Path:
    _ensure_pillow()
    from PIL import Image, ImageDraw, ImageFont

    normalized = _normalize_rows(rows, name_keys)
    if not normalized:
        raise RuntimeError("No standings rows available to render.")

    row_height = 36
    header_height = 60
    padding = 24
    table_width = 900
    height = header_height + row_height * (len(normalized) + 1) + padding

    image = Image.new("RGB", (table_width, height), color=(18, 18, 22))
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()

    draw.text((padding, 16), title, fill=(240, 240, 240), font=font)

    header_y = header_height - 10
    draw.line((padding, header_y, table_width - padding, header_y), fill=(80, 80, 90), width=2)

    columns = [
        ("Pos", 60),
        ("Name", 520),
        ("Pts", 120),
    ]
    col_x = padding
    for label, width in columns:
        draw.text((col_x, header_height + 4), label, fill=(200, 200, 210), font=font)
        col_x += width

    start_y = header_height + row_height
    for index, entry in enumerate(normalized, start=1):
        y = start_y + (index - 1) * row_height
        fill = (245, 245, 245) if index % 2 else (220, 220, 220)
        position = entry["position"] if entry["position"] is not None else index
        name = entry["name"] or "—"
        points = entry["points"] if entry["points"] is not None else "—"

        draw.text((padding, y), str(position), fill=fill, font=font)
        draw.text((padding + 60, y), str(name), fill=fill, font=font)
        draw.text((padding + 60 + 520, y), str(points), fill=fill, font=font)

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path
