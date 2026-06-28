# -*- coding: utf-8 -*-
"""清洗已经抓取的左慈页面数据，生成 JSONL 和 Markdown 语料。"""

import json
import os
import re
from collections import Counter
from pathlib import Path

from bs4 import BeautifulSoup


DATA_DIR = Path("data")
PAGES_JSON_DIR = DATA_DIR / "pages_json"
OUTPUT_DIR = DATA_DIR / "cleaned"
JSONL_PATH = OUTPUT_DIR / "leftci_cleaned.jsonl"
CORPUS_PATH = OUTPUT_DIR / "leftci_corpus.md"


def load_page_json_files():
    """读取所有页面 JSON 文件。"""
    if not PAGES_JSON_DIR.exists():
        return []
    return sorted(PAGES_JSON_DIR.glob("*.json"))


def clean_text(text):
    """清洗页面正文。"""
    if not text:
        return ""

    # 先把 HTML 标签去掉，避免一些残留标签干扰
    text = BeautifulSoup(text, "lxml").get_text("\n", strip=True)

    # 把 Windows 风格换行统一成换行
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # 去掉多余空行：把连续的 3 行以上空白换成 2 行
    text = re.sub(r"\n{3,}", "\n\n", text)

    # 去掉一些常见 Wiki 杂项
    remove_patterns = [
        r"编辑",
        r"分类",
        r"本页面最后修订于.*",
        r"本页最后修订于.*",
        r"此页面最后修订于.*",
        r"查看.*编辑历史",
        r"当前版本.*",
        r"收起",
        r"展开",
        r"返回顶部",
    ]
    for pattern in remove_patterns:
        text = re.sub(pattern, "", text)

    # 去掉一些明显的导航或重复文字
    lines = []
    previous = None
    for raw_line in text.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        # 去掉连续重复导航文字
        if line == previous:
            continue

        # 去掉一些常见的导航短语
        if line in {"首页", "目录", "正文", "返回", "上一页", "下一页"}:
            continue

        # 进一步去掉“编 刷 历”等无用提示
        if re.search(r"编\s*刷\s*历", line):
            continue

        lines.append(line)
        previous = line

    text = "\n".join(lines)

    # 把多个空格压缩成一个
    text = re.sub(r"[ \t]{2,}", " ", text)

    # 清理头尾空白
    text = text.strip()
    return text


def guess_category(title):
    """根据标题粗略判断页面分类。"""
    title_lower = title.lower()

    if "恋念之音" in title:
        return "恋念之音"
    if "恋念剧情" in title:
        return "恋念剧情"
    if "鸢记" in title:
        return "鸢记"
    if "约会" in title:
        return "约会"
    if "红鸾花笺" in title:
        return "红鸾花笺"
    if "留音" in title or "留声" in title:
        return "留音"
    if "活动剧情" in title:
        return "活动剧情"
    if "信笺匣" in title or "柬帖匣" in title:
        return "信件"
    return "其他"


def build_record(page_data):
    """把单个页面数据整理成清洗后的记录。"""
    title = page_data.get("title", "")
    url = page_data.get("url", "")
    text = page_data.get("text", "")
    categories = page_data.get("categories", []) or []
    sections = page_data.get("sections", []) or []

    cleaned_text = clean_text(text)

    # 如果正文太短，尽量把标题、分类、章节信息补进去，方便后续查看
    if cleaned_text:
        if len(cleaned_text) < 80:
            parts = []
            if categories:
                parts.append("分类：" + "，".join([c.get("*", "") for c in categories[:5] if isinstance(c, dict)]))
            if sections:
                parts.append("章节：" + "，".join([s.get("line", "") for s in sections[:5] if isinstance(s, dict)]))
            cleaned_text = cleaned_text + "\n" + "\n".join(parts)

    return {
        "title": title,
        "url": url,
        "category_guess": guess_category(title),
        "text": cleaned_text,
    }


def write_outputs(records):
    """生成 JSONL 和 Markdown 语料。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with JSONL_PATH.open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")

    category_counter = Counter(record["category_guess"] for record in records)
    lines = []
    lines.append("# 左慈页面清洗语料")
    lines.append("")

    for category in sorted(category_counter):
        lines.append(f"# {category}")
        lines.append("")
        for record in records:
            if record["category_guess"] != category:
                continue
            lines.append(f"## {record['title']}")
            lines.append(f"来源：{record['url']}")
            lines.append("")
            lines.append(record["text"])
            lines.append("")

    with CORPUS_PATH.open("w", encoding="utf-8") as handle:
        handle.write("\n".join(lines).strip() + "\n")

    total_chars = sum(len(record.get("text", "")) for record in records)
    print(f"原始页面数: {len(records)}")
    print(f"成功清洗页面数: {len(records)}")
    print(f"总字数估算: {total_chars}")
    print("每个分类多少页:")
    for category, count in sorted(category_counter.items()):
        print(f"- {category}: {count}")
    print(f"JSONL 输出: {JSONL_PATH}")
    print(f"Markdown 输出: {CORPUS_PATH}")


def main():
    """主函数。"""
    page_files = load_page_json_files()
    records = []

    for page_file in page_files:
        try:
            with page_file.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
            record = build_record(data)
            if record.get("text"):
                records.append(record)
        except Exception as exc:
            print(f"清洗失败：{page_file.name} -> {exc}")

    write_outputs(records)


if __name__ == "__main__":
    main()
