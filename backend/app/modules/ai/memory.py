"""Bounded reference memory; excludes names, notes, answers, secrets and stale quantities."""

import re
from datetime import date

SKU = re.compile(r"[A-Z0-9][A-Z0-9._/-]{0,63}")


def safe_sku(value):
    return value if isinstance(value, str) and SKU.fullmatch(value) else None


def sanitize_context(value) -> dict:
    if not isinstance(value, dict):
        return {}
    result = {}
    choices = (
        list(
            dict.fromkeys(sku for item in value.get("choices", [])[:20] if (sku := safe_sku(item)))
        )
        if isinstance(value.get("choices"), list)
        else []
    )
    if choices:
        result["choices"] = choices
    if sku := safe_sku(value.get("sku")):
        result["sku"] = sku
    for key in ["from_date", "to_date"]:
        try:
            if isinstance(value.get(key), str):
                result[key] = date.fromisoformat(value[key]).isoformat()
        except ValueError:
            pass
    return result


def build_context(results: list[dict]) -> dict:
    skus, selected, dates = [], [], {}
    for result in results:
        data = result["data"]
        if sku := safe_sku(data.get("sku")):
            if data.get("found") is not False:
                selected.append(sku)
        for row in data.get("items", []):
            if sku := safe_sku(row.get("sku")):
                skus.append(sku)
        rankings = data.get("ranking_by_unit", {})
        if len(rankings) == 1:
            for row in next(iter(rankings.values())):
                if sku := safe_sku(row.get("sku")):
                    skus.append(sku)
        for key in ["from_date", "to_date"]:
            alternate = "date_from" if key == "from_date" else "date_to"
            if key in data or alternate in data:
                dates[key] = data.get(key, data.get(alternate))
    choices = list(dict.fromkeys(selected + skus))[:20]
    unique = list(dict.fromkeys(selected))
    candidate = unique[0] if len(unique) == 1 else choices[0] if len(choices) == 1 else None
    return sanitize_context({"choices": choices, "sku": candidate, **dates})
