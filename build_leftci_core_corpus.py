# -*- coding: utf-8 -*-
"""从 data/leftci_related/leftci_pages.jsonl 中筛选左慈核心语料。

输出目录: data/leftci_core/

生成文件:
- leftci_core_pages.jsonl
- leftci_candidate_pages.jsonl
- leftci_weak_context_pages.jsonl
- leftci_core_corpus.md
- leftci_candidate_corpus.md
- leftci_core_summary.json

用法: 直接运行脚本。
"""

import json
from pathlib import Path
import os

INPUT_FILE = Path("data/leftci_related/leftci_pages.jsonl")
OUTPUT_DIR = Path("data/leftci_core")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

STRONG_KEYWORDS = {"左慈", "左君", "燃灯照夜"}
WEAK_KEYWORDS = {"师尊", "仙门", "仙人", "仙君", "仙道"}
MID_KEYWORDS = {"隐鸢阁"}

# title patterns indicating leftci columns
LEFTCI_TITLE_PATTERNS = [
    "左慈-约会",
    "左慈-鸢记",
    "左慈-恋念之音",
    "左慈-恋念剧情",
    "左慈-红鸾花笺",
    "左慈-秘闻",
    "左慈-回忆",
    "信笺匣/左慈",
]

CATEGORY_FOR_CANDIDATE_IF_SHIZUN = {"约会", "鸢记", "活动剧情", "密探故事", "信件/语音", "恋念剧情", "恋念之音"}


def contains_any_in_text(record, keywords):
    """检查 record 的 text 字段中是否包含任一关键词。"""
    text = record.get("text") or ""
    if not isinstance(text, str):
        return False
    return any(kw in text for kw in keywords)


def contains_any_in_title_fields(record, keywords):
    """检查 title/source_title/displaytitle 中是否包含任一关键词。"""
    for k in ("title", "source_title", "displaytitle"):
        value = record.get(k)
        if isinstance(value, str) and any(kw in value for kw in keywords):
            return True
    return False


def title_matches_patterns(title):
    if not title:
        return False
    for p in LEFTCI_TITLE_PATTERNS:
        if p in title:
            return True
    return False


def evaluate_relation(record):
    """Evaluate relation level, reason, and keyword hits from title/text/category_type."""
    title_hits = []
    text_hits = []
    weak_hits = []
    mid_hits = []

    for key in ("title", "source_title", "displaytitle"):
        value = record.get(key)
        if isinstance(value, str):
            for kw in STRONG_KEYWORDS:
                if kw in value:
                    title_hits.append(kw)
            for kw in MID_KEYWORDS:
                if kw in value:
                    mid_hits.append(kw)
            for kw in WEAK_KEYWORDS:
                if kw in value:
                    weak_hits.append(kw)

    text_value = record.get("text") or ""
    if isinstance(text_value, str):
        for kw in STRONG_KEYWORDS:
            if kw in text_value:
                text_hits.append(kw)
        for kw in MID_KEYWORDS:
            if kw in text_value:
                mid_hits.append(kw)
        for kw in WEAK_KEYWORDS:
            if kw in text_value:
                weak_hits.append(kw)

    category_type = record.get("category_type") or ""
    strong_hits = list({*title_hits, *text_hits})
    mid_hits = list(set(mid_hits))
    weak_hits = list(set(weak_hits))

    # core_narrative rules
    if title_hits:
        return {
            "relation_level": "core_narrative",
            "relation_reason": "title/source_title/displaytitle 包含强关键词",
            "strong_keyword_hits": strong_hits,
            "mid_keyword_hits": mid_hits,
            "weak_keyword_hits": weak_hits,
        }

    if title_matches_patterns(record.get("title") or "") or title_matches_patterns(record.get("source_title") or "") or title_matches_patterns(record.get("displaytitle") or ""):
        return {
            "relation_level": "core_narrative",
            "relation_reason": "标题属于左慈栏目",
            "strong_keyword_hits": strong_hits,
            "mid_keyword_hits": mid_hits,
            "weak_keyword_hits": weak_hits,
        }

    if category_type != "家具/道具" and text_hits:
        return {
            "relation_level": "core_narrative",
            "relation_reason": "非家具/道具页面 text包含强关键词",
            "strong_keyword_hits": strong_hits,
            "mid_keyword_hits": mid_hits,
            "weak_keyword_hits": weak_hits,
        }

    # item_candidate rules
    if category_type == "家具/道具":
        if title_hits or text_hits or mid_hits or weak_hits:
            return {
                "relation_level": "item_candidate",
                "relation_reason": "家具/道具页面包含强/中/泛关键词",
                "strong_keyword_hits": strong_hits,
                "mid_keyword_hits": mid_hits,
                "weak_keyword_hits": weak_hits,
            }
        return {
            "relation_level": "candidate",
            "relation_reason": "家具/道具页面未出现相关关键词，归入 candidate",
            "strong_keyword_hits": [],
            "mid_keyword_hits": [],
            "weak_keyword_hits": [],
        }

    # candidate rules for non-furniture
    if "隐鸢阁" in text_value:
        return {
            "relation_level": "candidate",
            "relation_reason": "非家具/道具页面 text出现隐鸢阁",
            "strong_keyword_hits": strong_hits,
            "mid_keyword_hits": mid_hits,
            "weak_keyword_hits": weak_hits,
        }

    if category_type in {"约会", "鸢记", "活动剧情", "密探故事", "信件/语音", "恋念剧情", "恋念之音", "红鸾花笺"} and contains_any_in_text(record, WEAK_KEYWORDS):
        return {
            "relation_level": "candidate",
            "relation_reason": "非家具/道具页面特定 category_type 且 text包含泛关键词",
            "strong_keyword_hits": strong_hits,
            "mid_keyword_hits": mid_hits,
            "weak_keyword_hits": weak_hits,
        }

    # weak_context rules
    if weak_hits and not strong_hits and not mid_hits:
        return {
            "relation_level": "weak_context",
            "relation_reason": "仅出现泛关键词，无强关键词或隐鸢阁",
            "strong_keyword_hits": [],
            "mid_keyword_hits": [],
            "weak_keyword_hits": weak_hits,
        }

    return {
        "relation_level": "candidate",
        "relation_reason": "未满足 core_narrative/item_candidate/weak_context 规则，归入 candidate",
        "strong_keyword_hits": strong_hits,
        "mid_keyword_hits": mid_hits,
        "weak_keyword_hits": weak_hits,
    }


def minimal_record(record, relation_info):
    """Return minimal record structure to save in jsonl outputs."""
    return {
        "pageid": record.get("pageid"),
        "title": record.get("title"),
        "source_title": record.get("source_title"),
        "displaytitle": record.get("displaytitle"),
        "url": record.get("url"),
        "category_type": record.get("category_type"),
        "matched_keywords": record.get("matched_keywords") or [],
        "match_count": record.get("match_count") or 0,
        "categories": record.get("categories") or [],
        "snippets": record.get("snippets") or [],
        "text": record.get("text") or "",
        "relation_level": relation_info["relation_level"],
        "relation_reason": relation_info["relation_reason"],
        "strong_keyword_hits": relation_info["strong_keyword_hits"],
        "mid_keyword_hits": relation_info["mid_keyword_hits"],
        "weak_keyword_hits": relation_info["weak_keyword_hits"],
    }


def write_markdown(grouped_records, output_path):
    """Write markdown grouped by category_type. grouped_records: dict category_type -> list(records)"""
    with output_path.open("w", encoding="utf-8") as fh:
        fh.write("# Leftci Core Corpus\n\n")
        for cat_type, recs in grouped_records.items():
            fh.write(f"## {cat_type} ({len(recs)})\n\n")
            for r in recs:
                fh.write(f"### {r.get('title')} — {r.get('pageid')}\n\n")
                fh.write(f"- url: {r.get('url')}\n")
                fh.write(f"- relation_level: {r.get('relation_level')}\n")
                fh.write(f"- relation_reason: {r.get('relation_reason')}\n")
                fh.write(f"- strong_keyword_hits: {', '.join(r.get('strong_keyword_hits') or [])}\n")
                fh.write(f"- mid_keyword_hits: {', '.join(r.get('mid_keyword_hits') or [])}\n")
                fh.write(f"- weak_keyword_hits: {', '.join(r.get('weak_keyword_hits') or [])}\n")
                fh.write(f"- category_type: {r.get('category_type')}\n")
                fh.write(f"- matched_keywords: {', '.join(r.get('matched_keywords') or [])}\n")
                fh.write(f"- snippets:\n\n")
                for s in (r.get('snippets') or []):
                    fh.write("```\n")
                    fh.write(s + "\n")
                    fh.write("```\n\n")
                fh.write("- text:\n\n")
                text = r.get('text') or ""
                fh.write(text + "\n\n")
                fh.write("---\n\n")


def main():
    if not INPUT_FILE.exists():
        print(f"输入文件不存在: {INPUT_FILE}")
        return

    core_path = OUTPUT_DIR / "leftci_core_narrative_pages.jsonl"
    item_candidate_path = OUTPUT_DIR / "leftci_item_candidate_pages.jsonl"
    candidate_path = OUTPUT_DIR / "leftci_candidate_pages.jsonl"
    weak_path = OUTPUT_DIR / "leftci_weak_context_pages.jsonl"
    core_md = OUTPUT_DIR / "leftci_core_narrative_corpus.md"
    item_candidate_md = OUTPUT_DIR / "leftci_item_candidate_corpus.md"
    summary_path = OUTPUT_DIR / "leftci_core_summary.json"

    scanned = 0
    core_narrative_count = 0
    item_candidate_count = 0
    candidate_count = 0
    weak_count = 0

    core_narrative_category_counts = {}
    item_candidate_category_counts = {}
    candidate_category_counts = {}
    weak_category_counts = {}
    reason_counts = {}

    grouped_core_narrative = {}
    grouped_item_candidate = {}

    with INPUT_FILE.open("r", encoding="utf-8") as inp, \
            core_path.open("w", encoding="utf-8") as core_out, \
            item_candidate_path.open("w", encoding="utf-8") as item_out, \
            candidate_path.open("w", encoding="utf-8") as cand_out, \
            weak_path.open("w", encoding="utf-8") as weak_out:

        for line in inp:
            scanned += 1
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue

            relation_info = evaluate_relation(rec)
            classification = relation_info["relation_level"]
            minimal = minimal_record(rec, relation_info)

            reason = minimal.get("relation_reason") or ""
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

            if classification == "core_narrative":
                core_out.write(json.dumps(minimal, ensure_ascii=False) + "\n")
                core_narrative_count += 1
                ct = minimal.get("category_type") or "其他"
                core_narrative_category_counts[ct] = core_narrative_category_counts.get(ct, 0) + 1
                grouped_core_narrative.setdefault(ct, []).append(minimal)
            elif classification == "item_candidate":
                item_out.write(json.dumps(minimal, ensure_ascii=False) + "\n")
                item_candidate_count += 1
                ct = minimal.get("category_type") or "其他"
                item_candidate_category_counts[ct] = item_candidate_category_counts.get(ct, 0) + 1
                grouped_item_candidate.setdefault(ct, []).append(minimal)
            elif classification == "candidate":
                cand_out.write(json.dumps(minimal, ensure_ascii=False) + "\n")
                candidate_count += 1
                ct = minimal.get("category_type") or "其他"
                candidate_category_counts[ct] = candidate_category_counts.get(ct, 0) + 1
            else:
                weak_out.write(json.dumps(minimal, ensure_ascii=False) + "\n")
                weak_count += 1
                ct = minimal.get("category_type") or "其他"
                weak_category_counts[ct] = weak_category_counts.get(ct, 0) + 1

    write_markdown(grouped_core_narrative, core_md)
    write_markdown(grouped_item_candidate, item_candidate_md)

    summary = {
        "scanned_pages": scanned,
        "core_narrative_count": core_narrative_count,
        "item_candidate_count": item_candidate_count,
        "candidate_count": candidate_count,
        "weak_context_count": weak_count,
        "core_narrative_category_counts": core_narrative_category_counts,
        "item_candidate_category_counts": item_candidate_category_counts,
        "candidate_category_counts": candidate_category_counts,
        "weak_category_counts": weak_category_counts,
        "reason_counts": reason_counts,
    }

    with summary_path.open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"扫描宽筛页面数: {scanned}")
    print(f"core_narrative_count: {core_narrative_count}")
    print(f"item_candidate_count: {item_candidate_count}")
    print(f"candidate_count: {candidate_count}")
    print(f"weak_context_count: {weak_count}")
    print("各 category_type 在 core_narrative 中的数量:")
    for k, v in core_narrative_category_counts.items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
