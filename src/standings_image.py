"""PNG rendering utilities for league standings."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Iterable, List, Mapping, Sequence, Tuple


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


def _load_font(size: int) -> "ImageFont.ImageFont":
    from PIL import ImageFont

    try:
        return ImageFont.truetype("DejaVuSans.ttf", size=size)
    except OSError:
        return ImageFont.load_default()


def _format_value(value: Any) -> str:
    if value is None or value == "":
        return "—"
    return str(value)


def _normalize_columns(columns: Sequence[str]) -> List[Tuple[str, str]]:
    normalized: List[Tuple[str, str]] = []
    for key in columns:
        label = key.replace("_", " ").title()
        normalized.append((key, label))
    return normalized


def _text_width(draw: "ImageDraw.ImageDraw", text: str, font: "ImageFont.ImageFont") -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def render_standings_png(
    rows: Iterable[Mapping[str, Any]],
    output_path: str,
    title: str,
    columns: Sequence[str],
) -> Path:
    _ensure_pillow()
    from PIL import Image, ImageDraw

    normalized = [_coerce_mapping(entry) for entry in rows]
    if not normalized:
        raise RuntimeError("No standings rows available to render.")

    column_defs = _normalize_columns(columns)

    body_font = _load_font(16)
    header_font = _load_font(17)
    title_font = _load_font(22)

    padding_x = 24
    padding_y = 20
    row_padding_y = 8
    header_padding_y = 10
    title_height = 48

    row_height = body_font.size + row_padding_y * 2
    header_height = header_font.size + header_padding_y * 2

    image = Image.new("RGB", (1, 1), color=(18, 18, 22))
    draw = ImageDraw.Draw(image)

    column_widths: List[int] = []
    for key, label in column_defs:
        width = _text_width(draw, label, header_font)
        for entry in normalized:
            value = _format_value(entry.get(key))
            width = max(width, _text_width(draw, value, body_font))
        column_widths.append(width + 24)

    table_width = padding_x * 2 + sum(column_widths)
    height = padding_y + title_height + header_height + row_height * len(normalized) + padding_y

    image = Image.new("RGB", (table_width, height), color=(18, 18, 22))
    draw = ImageDraw.Draw(image)

    draw.rectangle((0, 0, table_width, title_height + padding_y), fill=(26, 26, 32))
    draw.text(
        (padding_x, padding_y // 2),
        title,
        fill=(245, 245, 248),
        font=title_font,
    )

    header_y = padding_y + title_height
    draw.rectangle(
        (padding_x, header_y, table_width - padding_x, header_y + header_height),
        fill=(38, 40, 50),
    )

    col_x = padding_x
    for (key, label), width in zip(column_defs, column_widths):
        draw.text(
            (col_x + 12, header_y + header_padding_y),
            label,
            fill=(222, 225, 235),
            font=header_font,
        )
        col_x += width

    start_y = header_y + header_height
    for index, entry in enumerate(normalized):
        y = start_y + index * row_height
        fill = (30, 32, 38) if index % 2 else (24, 26, 32)
        draw.rectangle((padding_x, y, table_width - padding_x, y + row_height), fill=fill)

        col_x = padding_x
        for (key, _), width in zip(column_defs, column_widths):
            value = _format_value(entry.get(key))
            draw.text(
                (col_x + 12, y + row_padding_y),
                value,
                fill=(236, 238, 244),
                font=body_font,
            )
            col_x += width

    draw.rectangle(
        (padding_x, header_y, table_width - padding_x, height - padding_y),
        outline=(70, 72, 82),
        width=2,
    )

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path, format="PNG")
    return path
