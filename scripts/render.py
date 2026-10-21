#!/usr/bin/env python3
"""Regenerate README price tables + data/prices.json from NovAI's public feed.

Run locally or in GitHub Actions. Stdlib only.
"""
from __future__ import annotations

import json
import pathlib
import urllib.request

FEED = "https://aiapi-pro.com/china-ai-leaderboard.json"
ROOT = pathlib.Path(__file__).resolve().parent.parent
README = ROOT / "README.md"
DATA = ROOT / "data" / "prices.json"

START = "<!-- PRICES:START -->"
END = "<!-- PRICES:END -->"

CATEGORY_ORDER = ["Chat / LLM", "Image", "Video", "Audio / Speech", "Embedding", "3D"]


def fetch() -> dict:
    req = urllib.request.Request(FEED, headers={"User-Agent": "novai-prices-bot/1.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def fmt_price(v) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    if f == 0:
        return "free"
    if f < 0.01:
        return f"${f:.5f}"
    if f < 1:
        return f"${f:.4f}"
    if f < 10:
        return f"${f:.3f}"
    return f"${f:.2f}"


def render_block(feed: dict) -> str:
    lines = [START, ""]
    lines.append(f"_Auto-generated from the live feed at <{FEED}> — do not edit by hand._")
    lines.append("")
    lines.append(f"**Generated:** {feed.get('generated_at', '')}  ")
    lines.append(f"**Platform fee:** {feed.get('platform_markup_pct', 0)}% (multiplier {feed.get('multiplier', 1.0)})  ")
    free = feed.get("free_models") or []
    if free:
        lines.append(f"**Free models:** {', '.join(free)}  ")
    credit = feed.get("free_signup_credit_usd")
    if credit:
        lines.append(f"**Signup credit:** ${credit}  ")
    lines.append("")

    cats = feed.get("categories") or []
    by_cat = {c.get("category"): c.get("models") or [] for c in cats}
    order = [c for c in CATEGORY_ORDER if c in by_cat] + [c for c in by_cat if c not in CATEGORY_ORDER]

    for cat in order:
        models = by_cat[cat]
        if not models:
            continue
        # group by unit so mixed billing units are never compared
        units: dict[str, list] = {}
        for m in models:
            units.setdefault(str(m.get("unit") or ""), []).append(m)
        for unit, items in units.items():
            items = sorted(items, key=lambda m: float(m.get("price_usd") or 0))
            shown = items[:12]
            lines.append(f"### {cat} — {unit} ({len(items)} models)")
            lines.append("")
            lines.append("| Model | Provider | Price | Unit |")
            lines.append("|---|---|---|---|")
            for m in shown:
                lines.append(
                    f"| [{m.get('name')}]({m.get('url')}) | {m.get('provider')} | {fmt_price(m.get('price_usd'))} | {m.get('unit')} |"
                )
            if len(items) > len(shown):
                lines.append(f"| … | | | _+{len(items) - len(shown)} more in the JSON feed_ |")
            lines.append("")

    lines.append(END)
    return "\n".join(lines)


def main() -> int:
    feed = fetch()
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(feed, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    block = render_block(feed)
    text = README.read_text(encoding="utf-8")
    if START in text and END in text:
        head = text.split(START)[0]
        tail = text.split(END)[1]
        text = head + block + tail
    else:
        text = text.rstrip() + "\n\n" + block + "\n"
    README.write_text(text, encoding="utf-8")

    n = sum(len(c.get("models") or []) for c in feed.get("categories") or [])
    print(f"updated: {n} models across {len(feed.get('categories') or [])} categories")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
