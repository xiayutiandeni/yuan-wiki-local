# -*- coding: utf-8 -*-
"""从 data/leftci_core/ 生成更适合角色长期记忆和世界书使用的干净文件。"""

import json
import re
from pathlib import Path

INPUT_CORE_NARRATIVE = Path("data/leftci_core/leftci_core_narrative_pages.jsonl")
INPUT_ITEM_CANDIDATE = Path("data/leftci_core/leftci_item_candidate_pages.jsonl")
INPUT_CANDIDATE = Path("data/leftci_core/leftci_candidate_pages.jsonl")
OUTPUT_DIR = Path("data/leftci_memory_pack")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

NOISE_PATTERNS = [
    r"^编$",
    r"^刷$",
    r"^历$",
    r"^目录$",
    r"^MediaWiki:Amplification-expansion$",
    r"^看到此行说明js未正常加载，请尝试刷新页面!$",
    r"^如有更多投稿/推荐，请联系编辑部$",
    r"^授权转载$",
    r"action=edit",
    r"redlink=1",
    r"NewPP limit report",
    r"Cached time",
    r"CPU time usage",
]

WORLDBOOK_KEYS = [
    {
        "key": "左慈",
        "aliases": ["左君", "燃灯照夜"],
        "description": "左慈是隐鸢阁的核心人物，具有强大仙术与玄学背景，是左氏家族关键角色。",
    },
    {
        "key": "师尊",
        "aliases": [],
        "description": "师尊是故事中的尊称角色，与左慈和隐鸢阁有关联。",
    },
    {
        "key": "隐鸢阁",
        "aliases": [],
        "description": "隐鸢阁是左慈相关剧情中的重要地点/组织，承载着许多线索与人物关系。",
    },
    {
        "key": "燃灯照夜",
        "aliases": [],
        "description": "燃灯照夜是左慈身份或称谓之一，常出现在核心剧情中。",
    },
    {
        "key": "左君",
        "aliases": ["左慈"],
        "description": "左君是左慈的称呼之一，重要于人物关系与剧情线索。",
    },
    {
        "key": "仙门",
        "aliases": ["仙人", "仙君", "仙道"],
        "description": "仙门代表世界观中的修真体系，与左慈、隐鸢阁等元素相关。",
    },
]

TEXT_CLEAN_PATTERNS = [
    re.compile(p) for p in NOISE_PATTERNS
]

SCENE_TITLE_RE = re.compile(r"^【.+】$")
ROLE_LINE_RE = re.compile(r"^([^\s:：]+)[：:]\s*(.+)$")


def clean_lines(text):
    lines = text.splitlines()
    cleaned = []
    prev_blank = False
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
            continue
        prev_blank = False

        if any(pattern.search(line) for pattern in TEXT_CLEAN_PATTERNS):
            continue
        if line.startswith("[") and line.endswith("]") and "file" in line.lower():
            continue
        if line.startswith("{") and line.endswith("}"):
            continue

        cleaned.append(line)
    return "\n".join(cleaned).strip()


COMMON_SPEAKER_NAMES = {
    "广陵王", "孙策", "刘辩", "袁基", "傅融", "阿蝉", "史子眇", "张仲景", "张机",
    "徐庶", "祢衡", "袁隗", "御史大夫", "舞女", "平氏家主", "侍女", "管家", "弟子",
    "仙人", "张邈", "张郃", "张闿",
}
SECTION_TITLE_RE = re.compile(r"^[^\s]+·[一二三四五六七八九十百零]+$")
NO_QUOTE_LINE_RE = re.compile(r"[\[\]]|编辑")
PUNCTUATION_RE = re.compile(r"[，。！？：:；;、“”‘’（）()《》【】\[\]{}]")


def clean_text_for_quote(text):
    lines = text.splitlines()
    cleaned = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        if line in {"编", "刷", "历", "目录", "编辑"}:
            continue
        if NO_QUOTE_LINE_RE.search(line):
            continue
        if "MediaWiki" in line or "看到此行说明js未正常加载" in line or "授权转载" in line or "如有更多投稿" in line:
            continue
        if SECTION_TITLE_RE.match(line):
            cleaned.append(line)
            continue
        if SCENE_TITLE_RE.match(line):
            cleaned.append(line)
            continue
        cleaned.append(line)
    return cleaned


def is_scene_title(line):
    return bool(SCENE_TITLE_RE.match(line))


def is_section_title(line):
    return bool(SECTION_TITLE_RE.match(line))


def is_speaker_line(line, next_line=None):
    if line == "我":
        return True
    if line in COMMON_SPEAKER_NAMES:
        return True
    if len(line) <= 8 and not PUNCTUATION_RE.search(line):
        if next_line and not is_scene_title(next_line) and not is_section_title(next_line) and not ROLE_LINE_RE.match(next_line):
            return True
    return False


NARRATION_START_WORDS = ("他", "她", "众", "两人", "满殿", "众侍女")
ACTION_WORDS = {
    "走去", "展开", "留在", "坐在", "抬手", "望向", "注视", "沉默", "苦笑",
    "低头", "转身", "离去", "停在", "跌坐", "涌出", "穿过", "扶着",
}


def is_narration_line(line):
    if not line:
        return False
    stripped = line.strip()
    if any(stripped.startswith(prefix) for prefix in NARRATION_START_WORDS):
        return True
    if any(word in stripped for word in ACTION_WORDS):
        return True
    if "。" in stripped and not ROLE_LINE_RE.match(stripped):
        return True
    return False


def find_section(lines, index):
    for j in range(index - 1, -1, -1):
        if is_scene_title(lines[j]) or is_section_title(lines[j]):
            return lines[j]
    return ""


def extract_leftci_quotes(text):
    lines = clean_text_for_quote(text)
    quotes = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == "左慈":
            section = find_section(lines, i)
            context_before = [l for l in lines[max(0, i - 3):i] if l]
            if len(context_before) > 3:
                context_before = context_before[-3:]
            quote_lines = []
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if is_scene_title(next_line) or is_section_title(next_line) or is_speaker_line(next_line, lines[i + 1] if i + 1 < len(lines) else None):
                    break
                if next_line:
                    quote_lines.append(next_line)
                i += 1
            if quote_lines:
                context_after = []
                j = i
                while j < len(lines) and len(context_after) < 3:
                    if lines[j].strip():
                        context_after.append(lines[j].strip())
                    j += 1
                quotes.append({
                    "section": section,
                    "quote_text": "\n".join(quote_lines).strip(),
                    "context_before": context_before,
                    "context_after": context_after,
                })
            continue
        i += 1
    return quotes


def extract_leftci_quotes_v2(text):
    lines = clean_text_for_quote(text)
    quotes = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if line == "左慈":
            section = find_section(lines, i)
            context_before = [l for l in lines[max(0, i - 3):i] if l]
            if len(context_before) > 3:
                context_before = context_before[-3:]
            quote_lines = []
            i += 1
            while i < len(lines):
                next_line = lines[i].strip()
                if not next_line:
                    if quote_lines:
                        break
                    i += 1
                    continue
                if is_scene_title(next_line) or is_section_title(next_line) or is_speaker_line(next_line, lines[i + 1] if i + 1 < len(lines) else None):
                    break
                if quote_lines and is_narration_line(next_line):
                    break
                if not quote_lines and is_narration_line(next_line):
                    break
                quote_lines.append(next_line)
                i += 1
            if quote_lines:
                context_after = []
                j = i
                while j < len(lines) and len(context_after) < 3:
                    if lines[j].strip():
                        context_after.append(lines[j].strip())
                    j += 1
                quotes.append({
                    "section": section,
                    "quote_text": "\n".join(quote_lines).strip(),
                    "context_before": context_before,
                    "context_after": context_after,
                })
            continue
        i += 1
    return quotes


def load_jsonl(path):
    if not path.exists():
        return []
    items = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return items


def write_md(path, sections):
    with path.open("w", encoding="utf-8") as fh:
        for section in sections:
            fh.write(section)
            fh.write("\n\n")


def page_unique_key(rec):
    return f"{rec.get('pageid')}-{rec.get('title') or ''}"


def page_info(rec):
    return {
        "pageid": rec.get("pageid"),
        "title": rec.get("title"),
        "url": rec.get("url"),
        "category_type": rec.get("category_type"),
    }


def page_title_text(rec):
    return " ".join(filter(None, [rec.get("title"), rec.get("source_title"), rec.get("displaytitle")] ))


def build_worldbook_seed(all_pages):
    seed = []
    for item in WORLDBOOK_KEYS:
        entries = select_source_pages_for_key(item["key"], all_pages)
        seed.append({
            "key": item["key"],
            "aliases": item["aliases"],
            "description": item["description"],
            "source_pages": entries,
        })
    return seed


def normalize_pages(pages):
    seen = set()
    unique = []
    for rec in pages:
        key = page_unique_key(rec)
        if key in seen:
            continue
        seen.add(key)
        unique.append(rec)
    return unique


def score_for_key(key, rec):
    title_text = page_title_text(rec)
    text = rec.get("text") or ""
    category = rec.get("category_type") or ""
    title_has = lambda kw: kw in title_text
    text_has = lambda kw: kw in text
    leftci_title_patterns = [
        "左慈-约会",
        "左慈-鸢记",
        "左慈-恋念之音",
        "左慈-恋念剧情",
        "左慈-红鸾花笺",
        "左慈-秘闻",
        "左慈-回忆",
        "信笺匣/左慈",
    ]
    title_has_any = lambda kws: any(kw in title_text for kw in kws)
    text_has_any = lambda kws: any(kw in text for kw in kws)
    text_has_both = lambda a, b: a in text and b in text

    if key == "左慈":
        if title_has("左慈"):
            return 100
        if category in {"左慈专页", "约会", "鸢记", "恋念之音", "恋念剧情", "红鸾花笺", "活动剧情", "信件/语音"}:
            return 80
        if text_has("左慈"):
            if category == "家具/道具" and not title_has("左慈"):
                return 0
            return 60
        return 0

    if key == "师尊":
        if text_has_both("师尊", "左慈"):
            return 100
        if title_has("左慈"):
            return 90
        if text_has_both("师尊", "隐鸢阁"):
            return 80
        return 0

    if key == "隐鸢阁":
        if title_has("隐鸢阁") or title_has("左慈"):
            return 100
        if text_has_both("隐鸢阁", "左慈") or text_has_both("隐鸢阁", "师尊"):
            return 90
        if category in {"家具/道具"} and not (title_has("隐鸢阁") or title_has("左慈")):
            return 0
        if title_has("沙盒") or title_has("活动玩法"):
            return 0
        return 0

    if key == "仙门":
        blocked_item_title = any(sub in title_text for sub in ["引仙门", "迎仙门"]) or ("称号" in title_text and "仙门" in title_text)
        if blocked_item_title and not title_has("左慈") and not title_has("隐鸢阁"):
            return 0
        if any(pattern in title_text for pattern in ["左慈-留音", "仙门表彰大会", "左慈", "世界杂闻-隐鸢阁", "年表/左慈"]):
            return 100
        if text_has_both("仙门", "左慈") or text_has_both("仙门", "师尊") or text_has_both("仙门", "隐鸢阁"):
            return 90
        return 0

    if key == "燃灯照夜":
        if title_has("燃灯照夜") or title_has("左慈-约会"):
            return 100
        if text_has("燃灯照夜"):
            return 80
        return 0

    if key == "左君":
        if text_has("左君"):
            return 100
        if title_has("左君"):
            return 80
        return 0

    return 0


def select_source_pages_for_key(key, all_pages):
    scored = []
    for rec in all_pages:
        score = score_for_key(key, rec)
        if score > 0:
            scored.append((score, rec))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = []
    seen = set()
    for _, rec in scored:
        pageid_title = page_unique_key(rec)
        if pageid_title in seen:
            continue
        seen.add(pageid_title)
        selected.append(page_info(rec))
        if len(selected) >= 30:
            break
    if key == "燃灯照夜" and not selected:
        for rec in all_pages:
            if "燃灯照夜" in page_title_text(rec) or "燃灯照夜" in (rec.get("text") or ""):
                selected.append(page_info(rec))
                break
    if key == "左君" and not selected:
        for rec in all_pages:
            if "左君" in page_title_text(rec) or "左君" in (rec.get("text") or ""):
                selected.append(page_info(rec))
                break
    return selected


def clean_record_text(record):
    return clean_lines(record.get("text") or "")


def render_record_section(record, include_text=True):
    parts = [f"### {record.get('title')} — {record.get('pageid')}", f"- url: {record.get('url')}", f"- category_type: {record.get('category_type')}", f"- relation_level: {record.get('relation_level')}", f"- relation_reason: {record.get('relation_reason')}", f"- strong_keyword_hits: {', '.join(record.get('strong_keyword_hits') or [])}", f"- mid_keyword_hits: {', '.join(record.get('mid_keyword_hits') or [])}", f"- weak_keyword_hits: {', '.join(record.get('weak_keyword_hits') or [])}"]
    if include_text:
        parts.append("- text:")
        text = clean_record_text(record)
        parts.append(text)
    return "\n".join(parts)


def main():
    core_narrative = load_jsonl(INPUT_CORE_NARRATIVE)
    item_candidate = load_jsonl(INPUT_ITEM_CANDIDATE)
    candidate = load_jsonl(INPUT_CANDIDATE)

    core_sections = []
    item_sections = []
    candidate_sections = []
    quote_sections = []
    quote_clean_sections = []
    quote_clean_records = []
    quote_clean_v2_sections = []
    quote_clean_v2_records = []

    all_pages = []
    extracted_quotes = 0
    extracted_quotes_clean = 0
    extracted_quotes_clean_v2 = 0

    for rec in core_narrative:
        cleaned_text = clean_record_text(rec)
        rec["text"] = cleaned_text
        core_sections.append(render_record_section(rec, include_text=True))
        all_pages.append(rec)

        quotes = extract_leftci_quotes(cleaned_text)
        for quote in quotes:
            quote_sections.append(f"### {rec.get('title')} — {rec.get('pageid')}\n- url: {rec.get('url')}\n- quote:\n{quote['quote_text']}")
            extracted_quotes += 1
            quote_clean_records.append({
                "source_title": rec.get("source_title"),
                "pageid": rec.get("pageid"),
                "url": rec.get("url"),
                "section": quote.get("section", ""),
                "quote_text": quote.get("quote_text", ""),
                "context_before": quote.get("context_before", []),
                "context_after": quote.get("context_after", []),
            })
            quote_clean_sections.append(
                "\n".join([
                    f"### {rec.get('title')} — {rec.get('pageid')}",
                    f"- source_title: {rec.get('source_title')}",
                    f"- url: {rec.get('url')}",
                    f"- section: {quote.get('section', '')}",
                    f"- quote_text:",
                    quote.get('quote_text', ''),
                    f"- context_before:",
                    "\n".join(quote.get('context_before', [])),
                    f"- context_after:",
                    "\n".join(quote.get('context_after', [])),
                ]).strip()
            )
            extracted_quotes_clean += 1

        quotes_v2 = extract_leftci_quotes_v2(cleaned_text)
        for quote in quotes_v2:
            quote_clean_v2_records.append({
                "source_title": rec.get("source_title"),
                "pageid": rec.get("pageid"),
                "url": rec.get("url"),
                "section": quote.get("section", ""),
                "quote_text": quote.get("quote_text", ""),
                "context_before": quote.get("context_before", []),
                "context_after": quote.get("context_after", []),
            })
            quote_clean_v2_sections.append(
                "\n".join([
                    f"### {rec.get('title')} — {rec.get('pageid')}",
                    f"- source_title: {rec.get('source_title')}",
                    f"- url: {rec.get('url')}",
                    f"- section: {quote.get('section', '')}",
                    f"- quote_text:",
                    quote.get('quote_text', ''),
                    f"- context_before:",
                    "\n".join(quote.get('context_before', [])),
                    f"- context_after:",
                    "\n".join(quote.get('context_after', [])),
                ]).strip()
            )
            extracted_quotes_clean_v2 += 1

    for rec in item_candidate:
        cleaned_text = clean_record_text(rec)
        rec["text"] = cleaned_text
        parts = [f"### {rec.get('title')} — {rec.get('pageid')}", f"- url: {rec.get('url')}", f"- category_type: {rec.get('category_type')}"]
        if cleaned_text:
            parts.append("- description:")
            parts.append(cleaned_text)
        item_sections.append("\n".join(parts))
        all_pages.append(rec)

    for rec in candidate:
        cleaned_text = clean_record_text(rec)
        rec["text"] = cleaned_text
        candidate_sections.append(render_record_section(rec, include_text=True))
        all_pages.append(rec)

    seed = build_worldbook_seed(all_pages)

    write_md(OUTPUT_DIR / "01_leftci_core_narrative_clean.md", core_sections)
    write_md(OUTPUT_DIR / "02_leftci_items_furniture_clean.md", item_sections)
    write_md(OUTPUT_DIR / "03_leftci_candidate_review.md", candidate_sections)
    write_md(OUTPUT_DIR / "04_leftci_quotes_dialogue.md", quote_sections)
    write_md(OUTPUT_DIR / "04_leftci_quotes_dialogue_clean.md", quote_clean_sections)
    write_md(OUTPUT_DIR / "04_leftci_quotes_dialogue_clean_v2.md", quote_clean_v2_sections)

    with (OUTPUT_DIR / "04_leftci_quotes_dialogue_clean.jsonl").open("w", encoding="utf-8") as fh:
        for quote_rec in quote_clean_records:
            fh.write(json.dumps(quote_rec, ensure_ascii=False) + "\n")

    with (OUTPUT_DIR / "04_leftci_quotes_dialogue_clean_v2.jsonl").open("w", encoding="utf-8") as fh:
        for quote_rec in quote_clean_v2_records:
            fh.write(json.dumps(quote_rec, ensure_ascii=False) + "\n")

    with (OUTPUT_DIR / "05_leftci_worldbook_seed.json").open("w", encoding="utf-8") as fh:
        json.dump(seed, fh, ensure_ascii=False, indent=2)

    summary = {
        "scanned_core_narrative_pages": len(core_narrative),
        "scanned_item_candidate_pages": len(item_candidate),
        "scanned_candidate_pages": len(candidate),
        "output_files": [
            "01_leftci_core_narrative_clean.md",
            "02_leftci_items_furniture_clean.md",
            "03_leftci_candidate_review.md",
            "04_leftci_quotes_dialogue.md",
            "04_leftci_quotes_dialogue_clean.md",
            "04_leftci_quotes_dialogue_clean_v2.md",
            "04_leftci_quotes_dialogue_clean.jsonl",
            "04_leftci_quotes_dialogue_clean_v2.jsonl",
            "05_leftci_worldbook_seed.json",
            "leftci_memory_summary.json",
        ],
        "extracted_leftci_quote_count": extracted_quotes,
        "extracted_leftci_quote_clean_count": extracted_quotes_clean,
        "extracted_leftci_quote_clean_v2_count": extracted_quotes_clean_v2,
    }

    with (OUTPUT_DIR / "leftci_memory_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"扫描 core narrative 页面数: {len(core_narrative)}")
    print(f"扫描 item candidate 页面数: {len(item_candidate)}")
    print(f"扫描 candidate 页面数: {len(candidate)}")
    print(f"抽取 leftci 台词数量: {extracted_quotes}")


if __name__ == "__main__":
    main()
