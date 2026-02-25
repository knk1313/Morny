from __future__ import annotations

WEATHER_CODE_MAP: dict[int, str] = {
    0: "晴れ",
    1: "晴れ時々曇り",
    2: "曇り",
    3: "曇り",
    45: "霧",
    48: "霧",
    51: "霧雨",
    53: "霧雨",
    55: "霧雨",
    56: "着氷性の霧雨",
    57: "着氷性の霧雨",
    61: "雨",
    63: "雨",
    65: "強い雨",
    66: "着氷性の雨",
    67: "着氷性の強い雨",
    71: "雪",
    73: "雪",
    75: "大雪",
    77: "雪粒",
    80: "にわか雨",
    81: "にわか雨",
    82: "激しいにわか雨",
    85: "にわか雪",
    86: "にわか雪",
    95: "雷雨",
    96: "雷雨（ひょう）",
    99: "激しい雷雨（ひょう）",
}


def weather_code_to_japanese(code: int | None) -> str:
    if code is None:
        return "不明"
    return WEATHER_CODE_MAP.get(code, "不明")
