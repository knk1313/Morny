from __future__ import annotations

import re

_COORD_RE = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*,\s*([+-]?\d+(?:\.\d+)?)\s*$")
_COORDISH_RE = re.compile(r"^[\s+\-\d.,]+$")
_HHMM_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def normalize_calendar_id(value: str) -> str | None:
    normalized = value.strip()
    if not normalized:
        return None
    if len(normalized) > 255:
        return None
    return normalized


def parse_calendar_ids(value: str) -> list[str] | None:
    text = value.strip()
    if not text:
        return None

    normalized_text = text.replace("，", ",").replace("\n", ",")
    raw_parts = [part.strip() for part in normalized_text.split(",")]
    ids = [part for part in raw_parts if part]
    if not ids:
        return None

    deduped: list[str] = []
    seen: set[str] = set()
    for calendar_id in ids:
        if len(calendar_id) > 255:
            return None
        if calendar_id in seen:
            continue
        seen.add(calendar_id)
        deduped.append(calendar_id)
    return deduped


def serialize_calendar_ids(calendar_ids: list[str]) -> str:
    return ", ".join(calendar_ids)


def parse_stored_calendar_ids(value: str | None) -> list[str]:
    if not value:
        return []
    parsed = parse_calendar_ids(value)
    return parsed or []


def looks_like_coordinate_input(value: str) -> bool:
    text = value.strip()
    return "," in text and bool(_COORDISH_RE.fullmatch(text))


def parse_lat_lon(value: str) -> tuple[float, float] | None:
    match = _COORD_RE.fullmatch(value)
    if not match:
        return None

    lat = float(match.group(1))
    lon = float(match.group(2))
    if not (-90 <= lat <= 90):
        raise ValueError("緯度は -90〜90 の範囲で入力してください。")
    if not (-180 <= lon <= 180):
        raise ValueError("経度は -180〜180 の範囲で入力してください。")
    return lat, lon


def is_valid_hhmm(value: str) -> bool:
    return bool(_HHMM_RE.fullmatch(value.strip()))
