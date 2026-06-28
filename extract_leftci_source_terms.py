from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

MEMORY_PATH = ROOT / "data" / "leftci_memory_db" / "leftci_memories.jsonl"
OUTPUT_PATH = ROOT / "data" / "leftci_project_sources" / "LEFTCI_SOURCE_TERMS_FROM_WIKI.md"


# 只在原文命中后才写入。
# 没有命中的典籍，不会被输出，避免凭空给左慈塞知识。
KNOWN_TEXTS: list[dict[str, Any]] = [
    {
        "name": "《道德经》/《老子》",
        "aliases": ["道德经", "老子", "道法自然", "无为", "不争", "守柔", "知足", "知止", "上善若水"],
        "points": [
            "重在观势、知止、少妄为。",
            "无为不是不做，而是不以躁心乱动。",
            "守柔、不争、留余地，是处世之法。",
        ],
    },
    {
        "name": "《庄子》",
        "aliases": ["庄子", "逍遥", "齐物", "无用之用", "安时处顺", "南华经"],
        "points": [
            "不被一时得失役使心神。",
            "外物纷扰，不足以定人之贵贱。",
            "有些事不可强求，须知顺势与自守。",
        ],
    },
    {
        "name": "《周易》",
        "aliases": ["周易", "易经", "易", "乾坤", "阴阳", "卦", "变易", "时位", "吉凶", "爻"],
        "points": [
            "事在变化之中，不可用一刻定终局。",
            "判断须看时位、进退、动静。",
            "吉凶不是空谈，是对局势轻重的辨别。",
        ],
    },
    {
        "name": "《黄帝内经》",
        "aliases": ["黄帝内经", "内经", "气血", "心神", "五脏", "情志", "治未病", "劳倦", "寒热", "虚实"],
        "points": [
            "身与心相连，劳倦、饥饿、恐惧都会扰乱判断。",
            "小损不养，久则成疾。",
            "饮食、睡眠、寒暖不是小事，是守身之本。",
        ],
    },
    {
        "name": "《孙子兵法》",
        "aliases": ["孙子兵法", "孙子", "知己知彼", "虚实", "势", "谋攻", "先胜", "兵法"],
        "points": [
            "先辨敌我虚实，再动手。",
            "先求不败，再求胜。",
            "不要四面用力，要抓真正的关节。",
        ],
    },
    {
        "name": "《论语》",
        "aliases": ["论语", "孔子", "学而", "温故", "不愤不启", "不悱不发", "过犹不及", "君子不器"],
        "points": [
            "学问重在践行与反复。",
            "教人要等其有疑、有困，再点破。",
            "过度用力与不足一样会坏事。",
        ],
    },
    {
        "name": "《礼记》/《学记》",
        "aliases": ["礼记", "学记", "教学相长", "长善救失", "道而弗牵", "强而弗抑", "开而弗达"],
        "points": [
            "授人要先观其失，再救其偏。",
            "教人不是替他走完全程，而是引其自明。",
            "师者不贵多言，贵在启发。",
        ],
    },
    {
        "name": "《孟子》",
        "aliases": ["孟子", "浩然之气", "不动心", "求放心", "穷则独善其身"],
        "points": [
            "乱中先守心。",
            "困厄时先保全自身，再谋外事。",
            "人不可被一时贫困与恐惧夺去心志。",
        ],
    },
    {
        "name": "《大学》/《中庸》",
        "aliases": ["大学", "中庸", "格物", "致知", "诚意", "正心", "修身", "慎独", "中和"],
        "points": [
            "先看清事物，再谈判断。",
            "心乱则事乱。",
            "做事须有次第，不可本末倒置。",
        ],
    },
    {
        "name": "《荀子》/《劝学》",
        "aliases": ["荀子", "劝学", "学不可以已", "不积跬步", "青出于蓝"],
        "points": [
            "学问靠积累，不靠一时逞强。",
            "小步稳行，比躁进更可靠。",
            "不足不羞，停学才可惜。",
        ],
    },
    {
        "name": "史书传统",
        "aliases": ["史记", "汉书", "后汉书", "三国志", "左传", "春秋", "治乱", "兴亡", "君臣", "乱世"],
        "points": [
            "一人一事不可脱离时势判断。",
            "乱世行事须看权势、人心、粮秣、退路。",
            "成败不由一日一事定。",
        ],
    },
    {
        "name": "道教与方术传统",
        "aliases": ["太平经", "抱朴子", "神仙传", "方士", "方术", "符", "祝由", "导引", "服气", "辟谷", "仙道", "修行"],
        "points": [
            "方术不只是神异，也关乎治身、治心、观时。",
            "修行不离饮食、起居、心神、节律。",
            "不可装神弄鬼，须把术理化为判断。",
        ],
    },
]


TERM_GROUPS: dict[str, list[str]] = {
    "师道与授业": [
        "师者", "授业", "弟子", "师尊", "教", "学", "讲", "根基", "开悟", "点化", "不愤不启", "不悱不发",
    ],
    "医理与心神": [
        "心神", "气血", "肺热", "药", "汤", "病", "脉", "寒", "热", "虚", "实", "劳倦", "静养", "养病",
    ],
    "道术与修行": [
        "道", "术", "法", "符", "仙", "修行", "羽化", "魂魄", "灵", "气", "闭关", "长生", "服气",
    ],
    "阴阳与天时": [
        "阴阳", "五行", "天时", "节气", "星", "月", "日", "风雪", "寒暑", "昼夜", "卦", "乾坤",
    ],
    "乱世与权衡": [
        "乱世", "天下", "广陵", "绣衣楼", "权", "势", "进退", "取舍", "轻重", "缓急", "局势", "退路",
    ],
    "仙门与隐鸢阁": [
        "隐鸢阁", "左君", "阁主", "仙门", "山水郎", "长生塔", "云帝宫", "百仙华经", "灵山",
    ],
}


BOOK_TITLE_PATTERN = re.compile(r"《([^》]{1,30})》")


def load_memories() -> list[dict[str, Any]]:
    if not MEMORY_PATH.exists():
        raise FileNotFoundError(f"找不到记忆库：{MEMORY_PATH}")

    memories: list[dict[str, Any]] = []

    with MEMORY_PATH.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                memories.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"第 {line_no} 行 JSON 解析失败：{e}") from e

    return memories


def get_text(memory: dict[str, Any]) -> str:
    return "\n".join(
        [
            str(memory.get("source_title", "") or ""),
            str(memory.get("scene", "") or ""),
            str(memory.get("summary", "") or ""),
            str(memory.get("full_text", "") or ""),
        ]
    )


def clean_space(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def snippet(text: str, keyword: str, width: int = 90) -> str:
    i = text.find(keyword)
    if i < 0:
        return ""

    start = max(0, i - width)
    end = min(len(text), i + len(keyword) + width)
    return clean_space(text[start:end])


def memory_allowed(memory: dict[str, Any]) -> bool:
    title = str(memory.get("source_title", "") or "")
    scope = str(memory.get("memory_scope", "") or "")
    layer = str(memory.get("layer", "") or "")

    if title.startswith("左慈"):
        return True

    if "左慈" in title:
        return True

    if scope in {
        "relationship_memory",
        "core_memory",
        "worldbook_memory",
        "past_memory",
        "special_memory",
        "item_memory",
    }:
        return True

    if layer in {"relationship", "current", "worldbook", "jijin", "special", "item"}:
        return True

    return False


def detect_book_titles(memories: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    found: dict[str, list[dict[str, str]]] = defaultdict(list)

    for memory in memories:
        if not memory_allowed(memory):
            continue

        text = get_text(memory)
        for match in BOOK_TITLE_PATTERN.finditer(text):
            title = match.group(1)
            if not title:
                continue

            found[title].append(
                {
                    "id": str(memory.get("id", "")),
                    "source_title": str(memory.get("source_title", "")),
                    "hit": f"《{title}》",
                    "context": snippet(text, f"《{title}》"),
                }
            )

    return dict(found)


def detect_known_texts(memories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []

    for item in KNOWN_TEXTS:
        hits: list[dict[str, str]] = []
        aliases = item["aliases"]

        for memory in memories:
            if not memory_allowed(memory):
                continue

            text = get_text(memory)

            for alias in aliases:
                if alias in text:
                    hits.append(
                        {
                            "id": str(memory.get("id", "")),
                            "source_title": str(memory.get("source_title", "")),
                            "hit": alias,
                            "context": snippet(text, alias),
                        }
                    )
                    break

        if hits:
            results.append(
                {
                    "name": item["name"],
                    "points": item["points"],
                    "hits": hits,
                }
            )

    return results


def detect_term_groups(memories: list[dict[str, Any]]) -> dict[str, list[dict[str, str]]]:
    results: dict[str, list[dict[str, str]]] = {}

    for group_name, terms in TERM_GROUPS.items():
        group_hits: list[dict[str, str]] = []

        for memory in memories:
            if not memory_allowed(memory):
                continue

            text = get_text(memory)

            for term in terms:
                if term in text:
                    group_hits.append(
                        {
                            "id": str(memory.get("id", "")),
                            "source_title": str(memory.get("source_title", "")),
                            "hit": term,
                            "context": snippet(text, term),
                        }
                    )
                    break

        results[group_name] = group_hits

    return results


def top_source_titles(memories: list[dict[str, Any]]) -> list[tuple[str, int]]:
    counter: Counter[str] = Counter()

    for memory in memories:
        if memory_allowed(memory):
            counter[str(memory.get("source_title", "") or "")] += 1

    return counter.most_common(40)


def format_hits(hits: list[dict[str, str]], limit: int = 18) -> list[str]:
    lines: list[str] = []

    for hit in hits[:limit]:
        lines.append(
            f"- {hit['id']} | {hit['source_title']} | 命中：{hit['hit']} | {hit['context']}"
        )

    if len(hits) > limit:
        lines.append(f"- ……另有 {len(hits) - limit} 条。")

    return lines


def build_markdown(memories: list[dict[str, Any]]) -> str:
    book_titles = detect_book_titles(memories)
    known_texts = detect_known_texts(memories)
    term_groups = detect_term_groups(memories)
    source_titles = top_source_titles(memories)

    parts: list[str] = [
        "# 左慈 Wiki 原文中的典籍、术语与思想线索",
        "",
        "本文件只整理左慈相关 Wiki 原文中实际出现过的书名、术语与思想线索。",
        "",
        "使用规则：",
        "",
        "- 未在原文中命中的典籍，不写入本文件。",
        "- 不要把本文件当成左慈说话范文。",
        "- 不要模仿本文件的说明语气。",
        "- 不要在角色对话中说“根据本文件”。",
        "- 这些内容只用于帮助左慈形成判断：轻重、缓急、进退、取舍、师道、医理、修行、乱世分寸。",
        "- 左慈说话时仍应以 Wiki 原文风格为主。",
        "",
        "---",
        "",
        "## 一、实际出现的书名号内容",
        "",
    ]

    if book_titles:
        for title, hits in sorted(book_titles.items(), key=lambda x: (-len(x[1]), x[0])):
            parts.append(f"### 《{title}》")
            parts.append("")
            parts.extend(format_hits(hits, limit=8))
            parts.append("")
    else:
        parts.append("未检测到书名号格式的典籍或篇名。")
        parts.append("")

    parts.extend(
        [
            "---",
            "",
            "## 二、实际命中的典籍或思想传统",
            "",
            "只有在 Wiki 原文中出现过相关词的条目才会列出。",
            "",
        ]
    )

    if known_texts:
        for item in known_texts:
            parts.append(f"### {item['name']}")
            parts.append("")
            parts.append("原文命中：")
            parts.extend(format_hits(item["hits"], limit=12))
            parts.append("")
            parts.append("可内化的核心观点：")
            for point in item["points"]:
                parts.append(f"- {point}")
            parts.append("")
            parts.append("使用边界：")
            parts.append("- 不要直接背诵典籍。")
            parts.append("- 不要把这些观点讲成课堂笔记。")
            parts.append("- 只在相应语境中化为左慈的判断。")
            parts.append("")
    else:
        parts.append("未检测到预设典籍名或思想传统词。")
        parts.append("")

    parts.extend(
        [
            "---",
            "",
            "## 三、剧情术语与思想线索",
            "",
        ]
    )

    for group_name, hits in term_groups.items():
        parts.append(f"### {group_name}")
        parts.append("")
        if hits:
            parts.append(f"命中 {len(hits)} 条。")
            parts.append("")
            parts.extend(format_hits(hits, limit=16))
        else:
            parts.append("未检测到。")
        parts.append("")

    parts.extend(
        [
            "---",
            "",
            "## 四、左慈相关资料来源分布",
            "",
        ]
    )

    for title, count in source_titles:
        if title:
            parts.append(f"- {title}: {count}")

    parts.extend(
        [
            "",
            "---",
            "",
            "## 五、给角色调用的限制",
            "",
            "左慈不应把这些资料说成现代解释文。",
            "",
            "禁止：",
            "",
            "- 你怕的不是……是……",
            "- 你不是……而是……",
            "- 本质上是……",
            "- 核心问题是……",
            "- 今晚只做几件事",
            "- 家长看的只有几件事",
            "- 以下是建议",
            "- 首先、其次、最后",
            "",
            "正确方向不是“古风化现代建议”，而是：",
            "",
            "- 先判断轻重。",
            "- 再定进退。",
            "- 再给一句能落地的安排。",
            "- 若须解释，短而不尽。",
            "",
        ]
    )

    return "\n".join(parts).strip() + "\n"


def main() -> None:
    memories = load_memories()
    text = build_markdown(memories)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(text, encoding="utf-8", newline="\n")

    print("已生成：")
    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()