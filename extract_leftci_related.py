# -*- coding: utf-8 -*-
"""从本地 data/all_pages_json/*.json 中抽取所有左慈相关内容。

输出：
- data/leftci_related/leftci_pages.jsonl
- data/leftci_related/leftci_pages.md
- data/leftci_related/leftci_snippets.jsonl
- data/leftci_related/leftci_summary.json

用法：直接运行脚本。
"""

import json
import os
from pathlib import Path
import re
from bs4 import BeautifulSoup

INPUT_DIR = Path("data/all_pages_json")
OUTPUT_DIR = Path("data/leftci_related")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

KEYWORDS = [
    "左慈",
    "左君",
    "师尊",
    "隐鸢阁",
    "仙门",
    "仙人",
    "仙君",
    "仙道",
    "燃灯照夜",
]

SNIPPET_RADIUS = 120

CATEGORY_TYPES = [
    "左慈专页",
    "约会",
    "鸢记",
    "恋念之音",
    "恋念剧情",
    "红鸾花笺",
    "活动剧情",
    "密探故事",
    "家具/道具",
    "信件/语音",
    "其他",
]


def text_from_html(html):
    if not html:
        return ""
    try:
        soup = BeautifulSoup(html, "lxml")
        return soup.get_text(separator="\n", strip=True)
    except Exception:
        return re.sub(r"<[^>]+>", "", html or "")


def find_matches_in_field(field_text, keywords):
    if not field_text:
        return []
    matches = []
    lower = field_text
    for kw in keywords:
        # find all occurrences (case-sensitive for Chinese; keep simple)
        start = 0
        while True:
            idx = lower.find(kw, start)
            if idx == -1:
                break
            matches.append((kw, idx))
            start = idx + len(kw)
    return matches


def extract_snippets(source_text, matches):
    snippets = []
    if not source_text:
        return snippets
    length = len(source_text)
    for kw, idx in matches:
        start = max(0, idx - SNIPPET_RADIUS)
        end = min(length, idx + len(kw) + SNIPPET_RADIUS)
        snippet = source_text[start:end]
        snippets.append({
            "keyword": kw,
            "snippet": snippet,
            "start": start,
            "end": end,
        })
    return snippets

def normalize_categories(categories):
    """Normalize categories field into a list of strings.

    Rules:
    - If item is string, keep it.
    - If item is dict, pick first existing of: 'category', 'title', 'name', '*'.
    - If none of those keys present, dump the dict as JSON string.
    - Other types: convert to str().
    """
    if not categories:
        return []
    normalized = []
    for item in categories:
        if isinstance(item, str):
            normalized.append(item)
            continue
        if isinstance(item, dict):
            for key in ("category", "title", "name", "*"):
                if key in item and item.get(key) is not None:
                    val = item.get(key)
                    # ensure string
                    if not isinstance(val, str):
                        val = str(val)
                    normalized.append(val)
                    break
            else:
                try:
                    normalized.append(json.dumps(item, ensure_ascii=False))
                except Exception:
                    normalized.append(str(item))
            continue
        # other types
        try:
            normalized.append(str(item))
        except Exception:
            normalized.append(repr(item))
    return normalized


def classify_page(record):
    # record: dict contains title, displaytitle, categories (list), text
    title = (record.get("title") or "")
    display = (record.get("displaytitle") or "")
    cats = normalize_categories(record.get("categories") or [])
    text = record.get("text") or ""
    combined = "\n".join([title, display, "\n".join(cats), text])

    # heuristics in order
    if any(word in combined for word in ("约会",)):
        return "约会"
    if any(word in combined for word in ("隐鸢", "鸢")):
        return "鸢记"
    if "恋念之音" in combined:
        return "恋念之音"
    if "恋念" in combined and "剧情" in combined:
        return "恋念剧情"
    if any(word in combined for word in ("红鸾", "红鸾花笺")):
        return "红鸾花笺"
    if "活动" in combined:
        return "活动剧情"
    if any(word in combined for word in ("密探", "密探羁绊")):
        return "密探故事"
    if any(word in combined for word in ("家具", "道具")):
        return "家具/道具"
    if any(word in combined for word in ("信件", "语音", "信")):
        return "信件/语音"
    # 左慈专页判定：标题直接包含左慈并且不是已经归类的其他类型
    if "左慈" in title or "左慈" in display or any("左慈" in c for c in cats):
        return "左慈专页"
    return "其他"


def main():
    jsonl_path = OUTPUT_DIR / "leftci_pages.jsonl"
    md_path = OUTPUT_DIR / "leftci_pages.md"
    snippets_jsonl = OUTPUT_DIR / "leftci_snippets.jsonl"
    summary_path = OUTPUT_DIR / "leftci_summary.json"

    scanned = 0
    hit_pages = 0
    hit_snippets = 0
    category_counts = {k: 0 for k in CATEGORY_TYPES}

    with jsonl_path.open("w", encoding="utf-8") as out_jsonl, \
            md_path.open("w", encoding="utf-8") as out_md, \
            snippets_jsonl.open("w", encoding="utf-8") as out_snip:

        out_md.write("# 左慈相关页面汇总\n\n")

        for path in sorted(INPUT_DIR.glob("*.json")):
            scanned += 1
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
            except Exception:
                continue

            # read required fields
            title = data.get("title")
            source_title = data.get("source_title")
            displaytitle = data.get("displaytitle")
            pageid = data.get("pageid")
            url = data.get("url")
            categories = normalize_categories(data.get("categories") or [])
            text = data.get("text") or ""
            html = data.get("html") or ""

            html_text = text_from_html(html) if html and not text else text

            # search fields
            matched = set()
            matches_positions = []

            for field_text in (title, source_title, displaytitle, text, html):
                if not field_text:
                    continue
                field_matches = find_matches_in_field(field_text, KEYWORDS)
                for kw, pos in field_matches:
                    matched.add(kw)
                    matches_positions.append((kw, pos, field_text))

            if not matched:
                continue

            # build snippets using text (prefer plain text)
            # For snippet positions from html, map into html_text if needed.
            # We'll use html_text (which is text if available else extracted html) as source for snippet extraction.
            source_for_snip = html_text or text or ""
            # derive unique (kw, idx) matches in source_for_snip
            combined_matches = []
            for kw in matched:
                start = 0
                while True:
                    idx = source_for_snip.find(kw, start)
                    if idx == -1:
                        break
                    combined_matches.append((kw, idx))
                    start = idx + len(kw)

            snippets = extract_snippets(source_for_snip, combined_matches)

            record = {
                "pageid": pageid,
                "title": title,
                "source_title": source_title,
                "displaytitle": displaytitle,
                "url": url,
                "matched_keywords": sorted(list(matched)),
                "match_count": len(combined_matches),
                "categories": categories,
                "text": text,
                "snippets": [s["snippet"] for s in snippets],
            }

            # classification
            category_type = classify_page({
                "title": title,
                "displaytitle": displaytitle,
                "categories": categories,
                "text": text,
            })
            record["category_type"] = category_type

            # write records
            out_jsonl.write(json.dumps(record, ensure_ascii=False) + "\n")

            # md entry
            out_md.write(f"## {title}  — {pageid}\n\n")
            out_md.write(f"- source_title: {source_title}\n")
            out_md.write(f"- displaytitle: {displaytitle}\n")
            out_md.write(f"- url: {url}\n")
            out_md.write(f"- matched_keywords: {', '.join(sorted(list(matched)))}\n")
            out_md.write(f"- match_count: {len(combined_matches)}\n")
            out_md.write(f"- category_type: {category_type}\n")
            out_md.write(f"- categories: {', '.join(categories)}\n\n")
            out_md.write("### snippets\n")
            for s in snippets:
                out_md.write("\n``\n")
                # snippet may contain braces etc; write safely
                out_md.write(s.get("snippet", "") + "\n")
                out_md.write("```\n")
            out_md.write("\n---\n\n")

            # snippets jsonl: one entry per snippet
            for s in snippets:
                sn_entry = {
                    "pageid": pageid,
                    "title": title,
                    "keyword": s.get("keyword"),
                    "snippet": s.get("snippet"),
                    "start": s.get("start"),
                    "end": s.get("end"),
                }
                out_snip.write(json.dumps(sn_entry, ensure_ascii=False) + "\n")

            hit_pages += 1
            hit_snippets += len(snippets)
            category_counts.setdefault(category_type, 0)
            category_counts[category_type] = category_counts.get(category_type, 0) + 1

    summary = {
        "scanned_pages": scanned,
        "hit_pages": hit_pages,
        "hit_snippets": hit_snippets,
        "category_counts": category_counts,
    }

    with summary_path.open("w", encoding="utf-8") as handle:
        json.dump(summary, handle, ensure_ascii=False, indent=2)

    # final prints
    print(f"扫描页面数: {scanned}")
    print(f"命中页面数: {hit_pages}")
    print(f"命中 snippet 数: {hit_snippets}")
    print("各 category_type 数量:")
    for k, v in category_counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
