# -*- coding: utf-8 -*-
"""从 data/leftci_memory_pack/ 生成最终可用于 AI 角色长期记忆和世界书的左慈角色包。"""

import json
import re
from collections import Counter
from pathlib import Path

INPUT_CORE_NARRATIVE = Path("data/leftci_memory_pack/01_leftci_core_narrative_clean.md")
INPUT_ITEMS_FURNITURE = Path("data/leftci_memory_pack/02_leftci_items_furniture_clean.md")
INPUT_CANDIDATE_REVIEW = Path("data/leftci_memory_pack/03_leftci_candidate_review.md")
INPUT_QUOTES_V2 = Path("data/leftci_memory_pack/04_leftci_quotes_dialogue_clean_v2.jsonl")
INPUT_WORLDBOOK_SEED = Path("data/leftci_memory_pack/05_leftci_worldbook_seed.json")
OUTPUT_DIR = Path("data/leftci_final_pack")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

HEADER_RE = re.compile(r"^###\s+(.+?)\s+—\s*(\d+)$")
META_RE = re.compile(r"^-\s*([^:]+):\s*(.*)$")
NOISE_LINE_RE = re.compile(r"^(授权转载|如有更多投稿|联系编辑部|MediaWiki:|\[|\]$|编辑|道具总览)$")

FINAL_WORLDBOOK_KEYS = [
    "左慈",
    "师尊",
    "隐鸢阁",
    "燃灯照夜",
    "左君",
    "仙门",
    "广陵王",
]

WORLD_BOOK_TYPE = {
    "左慈": "character",
    "师尊": "character",
    "隐鸢阁": "organization",
    "燃灯照夜": "title",
    "左君": "title",
    "仙门": "concept",
    "广陵王": "character",
}

COMMAND_MARKERS = (
    "随吾",
    "不要",
    "别",
    "停止",
    "停下",
    "停在",
    "离开",
    "出发",
    "来",
    "去",
    "随我",
    "放下",
    "走",
    "跟",
    "守",
    "退",
    "收声",
    "不可",
    "不必",
    "莫",
    "退下",
    "停",
    "看",
    "听",
    "记住",
)

RELATION_TARGETS = [
    ("广陵王/我", ["广陵王", "殿下"], "宫廷往来/对立"),
    ("隐鸢阁弟子", ["隐鸢阁", "弟子"], "组织关系"),
    ("徐庶", ["徐庶", "师算"], "顾问/盟友"),
    ("张仲景/张机", ["张仲景", "张机"], "医者/幕僚"),
    ("祢衡", ["祢衡"], "同道/知己"),
    ("史子眇", ["史子眇"], "同道/知己"),
    ("董卓", ["董卓"], "政治对手/关系"),
    ("袁隗", ["袁隗"], "仕途冲突/对立"),
]

IDENTITY_TERMS = ["左慈", "师尊", "阁主", "仙君", "左君", "燃灯照夜"]


def load_md_records(path):
    if not path.exists():
        return []

    records = []
    current = None
    in_text = False
    text_lines = []

    with path.open("r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.rstrip("\n")
            header = HEADER_RE.match(line)
            if header:
                if current is not None:
                    current["text"] = "\n".join(text_lines).strip()
                    records.append(current)
                current = {
                    "title": header.group(1).strip(),
                    "pageid": int(header.group(2).strip()),
                    "url": "",
                    "category_type": "",
                    "relation_level": "",
                    "relation_reason": "",
                    "strong_keyword_hits": [],
                    "mid_keyword_hits": [],
                    "weak_keyword_hits": [],
                    "text": "",
                }
                in_text = False
                text_lines = []
                continue

            if current is None:
                continue

            if line.startswith("- text:"):
                in_text = True
                continue

            if in_text:
                text_lines.append(line)
                continue

            meta = META_RE.match(line)
            if meta:
                key = meta.group(1).strip()
                value = meta.group(2).strip()
                if key in {"strong_keyword_hits", "mid_keyword_hits", "weak_keyword_hits"}:
                    current[key] = [item.strip() for item in value.split(",") if item.strip()]
                else:
                    current[key] = value

    if current is not None:
        current["text"] = "\n".join(text_lines).strip()
        records.append(current)

    return records


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


def clean_text(text):
    lines = []
    prev_blank = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            if not prev_blank:
                lines.append("")
            prev_blank = True
            continue
        prev_blank = False
        if NOISE_LINE_RE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines).strip()


def normalize_text_for_search(text):
    return text.replace("　", " ").replace("“", "\"").replace("”", "\"")


def build_profile(core_records, quote_records):
    identity = set()
    profile_clues = {
        "隐鸢阁": 0,
        "广陵王": 0,
        "师尊": 0,
        "命令句": 0,
        "反问句": 0,
        "短句": 0,
        "冷静": 0,
        "沉静": 0,
    }
    phrases = []
    for rec in core_records:
        text = normalize_text_for_search(rec.get("text", ""))
        for term in IDENTITY_TERMS:
            if term in text or term in rec.get("title", ""):
                identity.add(term)
        if "隐鸢阁" in text:
            profile_clues["隐鸢阁"] += 1
        if "广陵王" in text:
            profile_clues["广陵王"] += 1
        if "师尊" in text:
            profile_clues["师尊"] += 1
        for keyword in ["波澜不惊", "沉静", "冷静", "不动声色", "压迫感", "隐鸢阁议事", "私自下山作乱者已伏诛"]:
            if keyword in text:
                phrases.append(keyword)

    for quote in quote_records:
        quote_text = quote.get("quote_text", "")
        if "吾" in quote_text:
            profile_clues["短句"] += 1
        if "？" in quote_text or "?" in quote_text:
            profile_clues["反问句"] += 1
            phrases.append(quote_text)
        if "！" in quote_text:
            profile_clues["命令句"] += 1
            phrases.append(quote_text)
        if len(quote_text) <= 12:
            profile_clues["短句"] += 1

    profile_lines = ["# 左慈角色档案\n"]
    profile_lines.append("## 身份/称谓")
    if identity:
        profile_lines.append("- " + ", ".join(sorted(identity)))
    else:
        profile_lines.append("- 左慈")
    profile_lines.append("")

    profile_lines.append("## 与隐鸢阁关系")
    if profile_clues["隐鸢阁"]:
        profile_lines.append("- 与隐鸢阁关系密切，至少涉及隐鸢阁议事与公开声明。")
    else:
        profile_lines.append("- 文本未直接明确说明与隐鸢阁的具体关系。")
    profile_lines.append("")

    profile_lines.append("## 与广陵王关系")
    if profile_clues["广陵王"]:
        profile_lines.append("- 与广陵王同处朝堂场景，并在若干场合出现对话或评论。")
    else:
        profile_lines.append("- 文本未明确显示与广陵王的直接互动。")
    profile_lines.append("")

    profile_lines.append("## 常见称呼")
    names = sorted({term for term in identity if term in {"左慈", "师尊", "阁主", "仙君", "左君", "燃灯照夜"}})
    if names:
        profile_lines.append("- " + ", ".join(names))
    else:
        profile_lines.append("- 左慈")
    profile_lines.append("")

    profile_lines.append("## 气质关键词")
    clues = []
    if profile_clues["冷静"]:
        clues.append("冷静")
    if profile_clues["沉静"]:
        clues.append("沉静")
    if profile_clues["命令句"]:
        clues.append("命令感")
    if profile_clues["反问句"]:
        clues.append("反问")
    if not clues:
        clues.append("沉稳")
    profile_lines.append("- " + ", ".join(clues))
    profile_lines.append("")

    profile_lines.append("## 行为特征")
    behaviors = []
    if profile_clues["命令句"]:
        behaviors.append("倾向于直接发号施令或指示他人行动。")
    if profile_clues["反问句"]:
        behaviors.append("偶尔使用反问，语气较为锋利。")
    if profile_clues["短句"]:
        behaviors.append("使用短句表达，语感节奏紧凑。")
    if not behaviors:
        behaviors.append("行为特征尚需由具体剧情进一步确认。")
    profile_lines.extend(f"- {item}" for item in behaviors)
    profile_lines.append("")

    profile_lines.append("## 待人工确认")
    profile_lines.append("- 是否为隐鸢阁正式领导者或决策核心。")
    profile_lines.append("- 与广陵王的具体私人交情与态度。")
    profile_lines.append("- 与师尊、隐鸢阁弟子之间的内部层级与细节。")
    profile_lines.append("")

    return "\n".join(profile_lines).strip()


def analyze_speech_style(quote_records):
    total = len(quote_records)
    counts = Counter()
    examples = {
        "吾": [],
        "隐鸢阁": [],
        "师尊": [],
        "question": [],
        "command": [],
    }
    for quote in quote_records:
        text = quote.get("quote_text", "")
        if not text:
            continue
        if "吾" in text:
            counts["吾"] += 1
            examples["吾"].append(text)
        if "隐鸢阁" in text:
            counts["隐鸢阁"] += 1
            examples["隐鸢阁"].append(text)
        if "师尊" in text:
            counts["师尊"] += 1
            examples["师尊"].append(text)
        if "？" in text or "?" in text:
            counts["question"] += 1
            examples["question"].append(text)
        if any(marker in text for marker in COMMAND_MARKERS):
            counts["command"] += 1
            examples["command"].append(text)
        if len(text) <= 12:
            counts["short"] += 1
        if "！" in text:
            counts["exclam"] += 1

    speech_lines = ["# 左慈说话风格整理\n"]
    speech_lines.append("## 高频自称")
    if counts["吾"]:
        speech_lines.append(f"- “吾” 出现 {counts['吾']} 次，明显是典型自称。")
    else:
        speech_lines.append("- 当前数据中未发现“吾”的高频自称。")
    speech_lines.append("")

    speech_lines.append("## 高频身份词")
    for term in ["隐鸢阁", "师尊", "广陵王", "仙门", "左君"]:
        if counts[term]:
            speech_lines.append(f"- “{term}” 出现 {counts[term]} 次。")
    if not any(counts[term] for term in ["隐鸢阁", "师尊", "广陵王", "仙门", "左君"]):
        speech_lines.append("- 当前数据中未发现明显的身份词高频出现。")
    speech_lines.append("")

    speech_lines.append("## 句式特征")
    if counts["short"]:
        speech_lines.append(f"- 存在 {counts['short']} 条短句，语气简洁。")
    if counts["command"]:
        speech_lines.append(f"- 存在 {counts['command']} 条命令/指示类句子。")
    if counts["question"]:
        speech_lines.append(f"- 存在 {counts['question']} 条疑问句或反问句。")
    if counts["exclam"]:
        speech_lines.append(f"- 存在 {counts['exclam']} 条带叹号或较强语气的句子。")
    if not any(counts[k] for k in ["short", "command", "question", "exclam"]):
        speech_lines.append("- 目前台词总体呈现平稳叙述，未统计到明显句式特征。")
    speech_lines.append("")

    speech_lines.append("## 语气特点")
    mood_lines = []
    if counts["question"] > 0:
        mood_lines.append("- 语气中包含反问与试探成分。")
    if counts["command"] > 0:
        mood_lines.append("- 语气倾向冷静而有控制力，带有指令性。")
    if counts["short"] > 0 and counts["command"] == 0:
        mood_lines.append("- 语句偏短，节奏紧凑，带有克制感。")
    if not mood_lines:
        mood_lines.append("- 语气总体偏向平稳、克制。")
    speech_lines.extend(mood_lines)
    speech_lines.append("")

    speech_lines.append("## 典型台词例子")
    example_texts = []
    for category in ["吾", "隐鸢阁", "师尊", "question", "command"]:
        for quote_text in examples[category][:2]:
            if quote_text not in example_texts:
                example_texts.append(quote_text)
            if len(example_texts) >= 6:
                break
        if len(example_texts) >= 6:
            break
    if example_texts:
        for quote_text in example_texts:
            speech_lines.append(f"- {quote_text}")
    else:
        speech_lines.append("- 当前未找到足够代表性台词。")
    speech_lines.append("")

    speech_lines.append("## 备注")
    speech_lines.append("- 以上分析基于 clean_v2 提取的台词原文，不作夸张改写。")
    speech_lines.append("- 仅列出明显可观察到的表达特点，避免推测性描述。\n")

    return "\n".join(speech_lines).strip()


def extract_record_snippets(records, keywords, max_snippets=4):
    snippets = []
    for rec in records:
        title = rec.get("title", "")
        text = normalize_text_for_search(rec.get("text", ""))
        for line in text.splitlines():
            if any(keyword in line for keyword in keywords):
                snippet = f"{line.strip()}（来源：{title}）"
                if snippet not in snippets:
                    snippets.append(snippet)
                    if len(snippets) >= max_snippets:
                        return snippets
    return snippets


def extract_quote_snippets(quote_records, keywords, max_snippets=4):
    snippets = []
    for quote in quote_records:
        text = quote.get("quote_text", "")
        title = quote.get("source_title", "")
        if any(keyword in text for keyword in keywords):
            snippet = f"{text.strip()}（来源：{title}）"
            if snippet not in snippets:
                snippets.append(snippet)
                if len(snippets) >= max_snippets:
                    break
    return snippets


def build_profile_v2(core_records, quote_records, worldbook_clean):
    identity_names = ["左慈", "师尊", "阁主", "仙君", "左君", "燃灯照夜"]
    identity_lines = [f"- {name}" for name in identity_names]
    relation_snippets = extract_quote_snippets(quote_records, ["广陵王", "广陵君", "我", "师尊"], max_snippets=6)
    hidden_snippets = extract_record_snippets(core_records, ["隐鸢阁", "师尊", "广陵王"], max_snippets=6)

    lines = ["# 左慈角色档案 V2\n"]
    lines.append("## 基础身份")
    lines.append("- 左慈：隐鸢阁关联角色，文本中多次以“左慈”出现。")
    lines.extend(identity_lines)
    lines.append("- 与隐鸢阁的关系：从现有剧情判断为隐鸢阁相关核心人物，常被提及为隐鸢阁事务的决策或执行者。")
    lines.append("- 确定信息：左慈关联隐鸢阁与师尊身份，可能承担组织责任。")
    lines.append("- 待确认：是否为隐鸢阁最高领导，具体职务名称与权力边界。\n")

    lines.append("## 与广陵王/“我”的关系")
    if relation_snippets:
        for snippet in relation_snippets:
            lines.append(f"- {snippet}")
    else:
        lines.append("- 语料中显示与广陵王/“我”存在互动，但需要进一步补充具体语境。")
    lines.append("- 关系特点：师徒风格、保护与提醒并存，必要时直接干预。\n")

    lines.append("## 性格与行为特征")
    lines.append("- 冷静，常以简短判定语句回应复杂局势。")
    lines.append("- 克制，情绪多藏于行动与判断之中，而非直接外放。")
    lines.append("- 具有压迫感与命令感，尤其在隐鸢阁事务、朝堂场景中显现。")
    lines.append("- 具备责任感，对隐鸢阁立场明确，对广陵王保持保护与牵引。")
    lines.append("- 对外人较为疏离，对“我”则展现更柔软、关注的侧面。\n")

    lines.append("## 行动模式")
    lines.append("- 多用短句定夺局面，快速落点。")
    lines.append("- 必要时直接出手，既有判断又有执行。")
    lines.append("- 倾向把个人情绪藏在职责、规矩、判断之后。")
    lines.append("- 对外人疏离，对“我”有更柔软的态度与保护性言行。\n")

    lines.append("## 角色使用注意")
    lines.append("- 不要写成轻浮甜宠。")
    lines.append("- 不要过度口语化。")
    lines.append("- 不要频繁撒娇。")
    lines.append("- 不要每句话都仙气飘飘。")
    lines.append("- 不要把“师尊”当成他的自称；“师尊”多数为别人对他的称呼。")
    lines.append("- 他的自称优先用“吾”。\n")

    lines.append("## 待人工确认")
    lines.append("- 是否为隐鸢阁最高决策者。")
    lines.append("- 与广陵王的具体私人情感与权力边界。")
    lines.append("- 师尊与左慈之间的确切师徒层级关系。")
    lines.append("- “仙君”“左君”“燃灯照夜”等称谓的官方身份定位。\n")

    return "\n".join(lines).strip()


def analyze_speech_style_v2(quote_records):
    counts = Counter()
    categories = {
        "权威/压迫感": [],
        "隐鸢阁立场": [],
        "对广陵王/“我”": [],
        "反问与判断": [],
        "克制温柔": [],
        "命令/保护": [],
    }
    command_markers = [
        "来", "去", "随吾", "收声", "不可", "不必", "莫", "退下", "停", "看", "听", "记住",
    ]

    for quote in quote_records:
        text = quote.get("quote_text", "")
        if not text:
            continue
        counts["quote_count"] += 1
        if "吾" in text:
            counts["吾"] += 1
        if "隐鸢阁" in text:
            counts["隐鸢阁"] += 1
        if "师尊" in text:
            counts["师尊"] += 1
        if "？" in text or "?" in text:
            counts["question"] += 1
        if "！" in text or "!" in text:
            counts["exclam"] += 1
        if len(text) <= 20:
            counts["short"] += 1
        if any(marker in text for marker in command_markers):
            counts["command"] += 1
        if "！" in text or any(marker in text for marker in command_markers):
            counts["strong"] += 1

        if any(marker in text for marker in ["随吾", "收声", "退下", "不可", "记住"]):
            if len(categories["命令/保护"]) < 10:
                categories["命令/保护"].append(text)
        if "隐鸢阁" in text and len(categories["隐鸢阁立场"]) < 10:
            categories["隐鸢阁立场"].append(text)
        if any(word in text for word in ["广陵王", "广陵君", "我"]) and len(categories["对广陵王/“我”"]) < 10:
            categories["对广陵王/“我”"].append(text)
        if "？" in text or "?" in text:
            if len(categories["反问与判断"]) < 10:
                categories["反问与判断"].append(text)
        if any(word in text for word in ["吾", "师尊"]) and not any(marker in text for marker in command_markers) and len(categories["克制温柔"]) < 10:
            categories["克制温柔"].append(text)
        if any(word in text for word in ["随吾", "收声", "退下", "不可", "记住", "停", "去", "来"]) and len(categories["权威/压迫感"]) < 10:
            categories["权威/压迫感"].append(text)

    lines = ["# 左慈说话风格 V2\n"]
    lines.append("## 统计数据")
    lines.append(f"- quote_count: {counts['quote_count']}")
    lines.append(f"- 含“吾”的台词数量: {counts['吾']}")
    lines.append(f"- 含“隐鸢阁”的台词数量: {counts['隐鸢阁']}")
    lines.append(f"- 含“师尊”的台词数量: {counts['师尊']}")
    lines.append(f"- 含问号“？”的台词数量: {counts['question']}")
    lines.append(f"- 含叹号“！”的台词数量: {counts['exclam']}")
    lines.append(f"- 短句数量(<=20): {counts['short']}")
    lines.append(f"- 命令/指令句数量: {counts['command']}")
    lines.append(f"- 强语气数量: {counts['strong']}")
    lines.append("")

    lines.append("## 说话风格分析")
    lines.append("- 自称：以“吾”自称为主，语气古风且自信。 ")
    lines.append("- 称呼习惯：对广陵王/‘我’使用直接称谓，对师尊更为恭敬。 ")
    lines.append("- 句式：偏向短句、判断句与反问句，节奏紧凑。 ")
    lines.append("- 语气：总体冷静、克制、带有压迫感，偶尔出现保护与纵容。 ")
    lines.append("- 情绪表达：不常直白外放，多通过短句与行动表达情绪。 ")
    lines.append("- 亲密表达：倾向克制、提醒与庇护，不油腻。\n")

    lines.append("## 典型台词分类")
    for category, examples in categories.items():
        lines.append(f"### {category}")
        if examples:
            for sentence in examples:
                lines.append(f"- {sentence}")
        else:
            lines.append("- (无足够示例)")
        lines.append("")

    return "\n".join(lines).strip()


CURRENT_TITLE_KEYWORDS = [
    "左慈-",
    "左慈/",
    "留音匣/左慈",
    "年表/左慈",
    "燃灯照夜",
]
CURRENT_TEXT_KEYWORDS = [
    "左慈",
    "师尊",
    "阁主",
    "仙君",
    "左君",
    "隐鸢阁",
    "吾",
    "山下",
    "随吾",
    "收声",
    "不可",
    "不必",
]
JIJIN_KEYWORDS = [
    "姬晋",
    "八百年前",
    "平陵",
    "母后",
    "过去",
    "梦",
    "回忆",
    "前尘",
    "广陵君",
    "我们要去哪",
    "孩子是谁",
    "一直在一起",
]
SPECIAL_KEYWORDS = [
    "啾",
]


def normalize_quote_context(quote):
    text = str(quote.get("quote_text", ""))
    before = " ".join(quote.get("context_before", []) or [])
    after = " ".join(quote.get("context_after", []) or [])
    source_title = str(quote.get("source_title", ""))
    section = str(quote.get("section", ""))
    return " ".join([text, before, after, source_title, section])


def classify_quote_v3(quote):
    text = str(quote.get("quote_text", ""))
    context = normalize_quote_context(quote)
    title = str(quote.get("source_title", ""))

    if any(key in text for key in SPECIAL_KEYWORDS) or any(key in context for key in SPECIAL_KEYWORDS):
        return "special"

    if any(key in text for key in JIJIN_KEYWORDS) or any(key in context for key in JIJIN_KEYWORDS) or any(key in title for key in ["黄月英", "姬晋", "平陵", "母后"]):
        return "jijin"

    if any(key in title for key in CURRENT_TITLE_KEYWORDS) or any(key in text for key in CURRENT_TEXT_KEYWORDS) or any(key in context for key in CURRENT_TEXT_KEYWORDS):
        return "current"

    return "unknown"


def score_quote_for_current(quote):
    text = str(quote.get("quote_text", ""))
    score = 0
    if "吾" in text:
        score += 4
    if "隐鸢阁" in text:
        score += 3
    if "师尊" in text:
        score += 3
    if "？" in text or "?" in text:
        score += 2
    if any(marker in text for marker in COMMAND_MARKERS):
        score += 2
    if len(text) <= 20:
        score += 1
    if "不可" in text or "不必" in text or "收声" in text or "随吾" in text:
        score += 2
    return score


def select_current_v3_quotes(quotes, limit=200):
    scored = []
    for quote in quotes:
        scored.append((score_quote_for_current(quote), quote))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [quote for score, quote in scored if score > 0]
    if len(selected) < limit:
        selected.extend([quote for score, quote in scored if score <= 0])
    return selected[:limit]


def select_current_v31_quotes(quotes, limit=200):
    return select_current_v3_quotes(quotes, limit=limit)


def render_quote_list_md(quotes, header):
    lines = [f"# {header}\n"]
    for quote in quotes:
        lines.append(f"## {quote.get('source_title', '')} — {quote.get('section', '')}")
        lines.append(f"- url: {quote.get('url', '')}")
        lines.append(f"- quote_text: {quote.get('quote_text', '')}")
        if quote.get("context_before"):
            lines.append("- context_before:")
            for line in quote.get("context_before", []):
                lines.append(f"  {line}")
        if quote.get("context_after"):
            lines.append("- context_after:")
            for line in quote.get("context_after", []):
                lines.append(f"  {line}")
        lines.append("")
    return "\n".join(lines).strip()


def build_profile_v3(core_records, quote_records):
    current_examples = [q for q in quote_records if classify_quote_v3(q) == "current"][:6]
    jijin_examples = [q for q in quote_records if classify_quote_v3(q) == "jijin"][:6]
    special_examples = [q for q in quote_records if classify_quote_v3(q) == "special"][:6]

    lines = ["# 左慈分层人物档案 V3\n"]
    lines.append("## 当前左慈")
    lines.append("- 当前左慈是隐鸢阁相关核心人物，出现于‘左慈-’系列剧情与燃灯照夜相关章节。")
    lines.append("- 常见称呼：左慈、师尊、阁主、仙君、左君、燃灯照夜。")
    lines.append("- 与隐鸢阁关系：与隐鸢阁事务紧密关联，语料中体现出隐鸢阁立场与组织责任。")
    lines.append("- 确定信息：当前左慈具有冷静、克制、责任感强的特质，擅长判断与执行。 ")
    lines.append("- 待确认：是否为隐鸢阁最高领导者、具体职务、与师尊的具体师徒层级。\n")

    lines.append("## 姬晋/八百年前")
    lines.append("- 该层代表过去线/前史/梦境记忆，常出现‘姬晋、平陵、母后、广陵君、过去、梦、回忆、前尘’等关键词。")
    lines.append("- 这部分不应与当前左慈默认语气混淆，而应视为历史记忆或特殊前史身份。 ")
    if jijin_examples:
        lines.append("- 代表示例：")
        for quote in jijin_examples:
            lines.append(f"  - {quote.get('quote_text', '')}（来源：{quote.get('source_title', '')}）")
    lines.append("- 待确认：姬晋时期与当前左慈的身份关联、情感延续及记忆触发机制。\n")

    lines.append("## 特殊状态")
    lines.append("- 该层代表活动特殊表达、拟声/异常状态，通常不应作为默认左慈日常语气。")
    if special_examples:
        lines.append("- 代表示例：")
        for quote in special_examples:
            lines.append(f"  - {quote.get('quote_text', '')}（来源：{quote.get('source_title', '')}）")
    lines.append("- 仅在特殊剧情触发或异常状态下调用此层语料。\n")

    lines.append("## 角色使用规则")
    lines.append("- 默认调用 current_v3。")
    lines.append("- 当用户提到‘姬晋、八百年前、平陵、母后、过去、梦、回忆’时，可调用 jijin_v3。")
    lines.append("- 当触发特殊活动、拟声或异常状态时，才调用 special_v3。")
    lines.append("- 不要混合时间层，避免把过去线与当前日常人格混为一体。\n")

    return "\n".join(lines).strip()


def analyze_speech_style_v3(quote_records):
    current = [q for q in quote_records if classify_quote_v3(q) == "current"]
    jijin = [q for q in quote_records if classify_quote_v3(q) == "jijin"]
    special = [q for q in quote_records if classify_quote_v3(q) == "special"]

    stats = {}
    def stats_for(subset):
        counts = Counter()
        for quote in subset:
            text = str(quote.get("quote_text", ""))
            if not text:
                continue
            counts["quote_count"] += 1
            counts["吾"] += int("吾" in text)
            counts["隐鸢阁"] += int("隐鸢阁" in text)
            counts["师尊"] += int("师尊" in text)
            counts["question"] += int("？" in text or "?" in text)
            counts["exclam"] += int("！" in text or "!" in text)
            counts["short"] += int(len(text) <= 20)
            counts["command"] += int(any(marker in text for marker in ["来", "去", "随吾", "收声", "不可", "不必", "莫", "退下", "停", "看", "听", "记住"]))
            counts["strong"] += int("！" in text or any(marker in text for marker in ["来", "去", "随吾", "收声", "不可", "不必", "莫", "退下", "停", "看", "听", "记住"]))
        return counts

    stats["current"] = stats_for(current)
    stats["jijin"] = stats_for(jijin)
    stats["special"] = stats_for(special)

    lines = ["# 左慈说话风格 V3\n"]
    for name, subset in [("current", current), ("jijin", jijin), ("special", special)]:
        lines.append(f"## {name} 说话风格")
        counts = stats[name]
        lines.append(f"- quote_count: {counts['quote_count']}")
        lines.append(f"- 含“吾”的台词数量: {counts['吾']}")
        lines.append(f"- 含“隐鸢阁”的台词数量: {counts['隐鸢阁']}")
        lines.append(f"- 含“师尊”的台词数量: {counts['师尊']}")
        lines.append(f"- 含问号“？”的台词数量: {counts['question']}")
        lines.append(f"- 含叹号“！”的台词数量: {counts['exclam']}")
        lines.append(f"- 短句数量(<=20): {counts['short']}")
        lines.append(f"- 命令/指令句数量: {counts['command']}")
        lines.append(f"- 强语气数量: {counts['strong']}")
        lines.append("")
        if name == "current":
            lines.append("- 自称：以“吾”为主。")
            lines.append("- 语气：冷静、克制、有压迫感，带有判断与保护。")
            lines.append("- 句式：短句、命令句、反问句为主。\n")
        elif name == "jijin":
            lines.append("- 特点：可能更显回忆感与前史氛围，包含平陵、梦境、母后、广陵君等关键词。")
            lines.append("- 语气：较为依恋、迷茫、情绪带有过去线痕迹。\n")
        else:
            lines.append("- 特点：拟声、异常表达或特殊活动状态，不应作为默认日常语气使用。\n")

    return "\n".join(lines).strip()


def build_quote_categories_v3(quote_records):
    categories = {
        "current": [],
        "jijin": [],
        "special": [],
        "unknown": [],
    }
    for quote in quote_records:
        category = classify_quote_v3(quote)
        categories[category].append(quote)
    return categories


def format_quote_md(quote):
    lines = [f"## {quote.get('source_title', '')} — {quote.get('section', '')}", f"- url: {quote.get('url', '')}", f"- quote_text: {quote.get('quote_text', '')}"]
    if quote.get("context_before"):
        lines.append("- context_before:")
        for line in quote.get("context_before", []):
            lines.append(f"  {line}")
    if quote.get("context_after"):
        lines.append("- context_after:")
        for line in quote.get("context_after", []):
            lines.append(f"  {line}")
    lines.append("")
    return "\n".join(lines)


def build_quote_md_for_category(quotes, header):
    lines = [f"# {header}\n"]
    for quote in quotes:
        lines.append(format_quote_md(quote))
    return "\n".join(lines).strip()


V31_CURRENT_TITLE_KEYWORDS = [
    "左慈-",
    "左慈/",
    "留音匣/左慈",
    "年表/左慈",
    "燃灯照夜",
    "夕情欢馀·左慈",
    "天下隐光",
]
V31_CURRENT_CONTEXT_KEYWORDS = [
    "师尊",
    "左慈",
    "隐鸢阁",
    "云帝宫",
    "阁主",
    "吾",
]
V31_JIJIN_STRONG_PHRASES = [
    "姬晋",
    "八百年前",
    "平陵",
    "母后",
    "前尘",
    "前世",
    "过去的自己",
    "过去身份",
    "黑色漫长的青丝",
    "眼眸惊慌清澈",
    "孩童",
    "少年",
    "幼年",
    "一直在一起",
    "我们要去哪",
    "去到平陵",
    "回广陵吗",
    "还是去平陵",
    "广陵君？",
    "广陵君，我们要去哪呀",
    "好像做了一个很长的梦",
    "广陵君，一直这样走，能去到平陵吗",
    "……广陵君……你愿意，和吾一直在一起吗",
]
V31_SPECIAL_KEYWORDS = [
    "啾",
]


def normalize_quote_context(quote):
    text = str(quote.get("quote_text", ""))
    before = " ".join(quote.get("context_before", []) or [])
    after = " ".join(quote.get("context_after", []) or [])
    source_title = str(quote.get("source_title", ""))
    section = str(quote.get("section", ""))
    return " ".join([text, before, after, source_title, section])


def classify_quote_v31(quote):
    text = str(quote.get("quote_text", ""))
    combined = normalize_quote_context(quote)
    title = str(quote.get("source_title", ""))

    if any(key in combined for key in V31_SPECIAL_KEYWORDS):
        return "special", "包含特殊拟声或异常表达，如‘啾’等。", "high"

    if any(key in combined for key in V31_JIJIN_STRONG_PHRASES):
        return "jijin", "符合姬晋/八百年前强判定特征。", "high"

    if any(key in title for key in V31_CURRENT_TITLE_KEYWORDS):
        return "current", "source_title 直接指向左慈相关剧情，且没有强烈过去线特征。", "high"

    if any(key in combined for key in V31_CURRENT_CONTEXT_KEYWORDS):
        return "current", "上下文出现当前左慈/师尊/隐鸢阁等标记，且不满足姬晋强判定。", "medium"

    if any(key in combined for key in ["过去", "梦", "回忆"]) and any(key in combined for key in ["师尊", "左慈", "隐鸢阁", "吾"]) and not any(key in combined for key in V31_JIJIN_STRONG_PHRASES):
        return "current", "虽然提及过去/梦境，但上下文更偏向当前左慈出场语境。", "medium"

    return "unknown", "无法明确分类为当前/姬晋/特殊，但仍可能相关，需人工复核。", "low"


def annotate_quote_v31(quote):
    layer, layer_reason, confidence = classify_quote_v31(quote)
    annotated = dict(quote)
    annotated["layer"] = layer
    annotated["layer_reason"] = layer_reason
    annotated["confidence"] = confidence
    return annotated


def build_quote_categories_v31(quote_records):
    categories = {
        "current": [],
        "jijin": [],
        "special": [],
        "unknown": [],
    }
    for quote in quote_records:
        annotated = annotate_quote_v31(quote)
        categories[annotated["layer"]].append(annotated)
    return categories


def format_quote_md_v31(quote):
    lines = [
        f"## {quote.get('source_title', '')} — {quote.get('section', '')}",
        f"- layer: {quote.get('layer', '')}",
        f"- layer_reason: {quote.get('layer_reason', '')}",
        f"- confidence: {quote.get('confidence', '')}",
        f"- url: {quote.get('url', '')}",
        f"- quote_text: {quote.get('quote_text', '')}",
    ]
    if quote.get("context_before"):
        lines.append("- context_before:")
        for line in quote.get("context_before", []):
            lines.append(f"  {line}")
    if quote.get("context_after"):
        lines.append("- context_after:")
        for line in quote.get("context_after", []):
            lines.append(f"  {line}")
    lines.append("")
    return "\n".join(lines)


def build_quote_md_for_category_v31(quotes, header):
    lines = [f"# {header}\n"]
    for quote in quotes:
        lines.append(format_quote_md_v31(quote))
    return "\n".join(lines).strip()


def is_speaker_review_v32(quote):
    text = str(quote.get("quote_text", ""))
    combined = normalize_quote_context(quote)
    if any(text.startswith(prefix) for prefix in ["广陵君"]):
        if "吾" not in text and not any(key in combined for key in V31_JIJIN_STRONG_PHRASES):
            return True, "以“广陵君”开头且不含吾，疑似他人称呼或非左慈默认发言。", "medium"
    direct_address = ["左慈？！", "左慈？", "左慈！", "师尊？", "师尊！"]
    if any(flag in text for flag in direct_address):
        if not any(word in text for word in ["吾", "隐鸢阁", "随吾", "收声", "不可", "不必", "记住", "阁主", "仙君"]):
            return True, "疑似他人在称呼左慈/师尊，而非左慈本人发言。", "high"
    other_question_phrases = ["你想做什么", "你明明知道", "杀不了我", "你为什么", "你要做什么"]
    if any(phrase in text for phrase in other_question_phrases):
        return True, "疑似他人向左慈提问或喊话，而非左慈自身语句。", "medium"
    return False, "", "low"


def build_quote_categories_v32(quote_records):
    categories_v31 = build_quote_categories_v31(quote_records)
    categories = {
        "current": [],
        "speaker_review": [],
        "jijin": [],
        "special": [],
        "unknown": [],
    }
    categories["jijin"] = categories_v31["jijin"][:]
    categories["special"] = categories_v31["special"][:]
    categories["unknown"] = categories_v31["unknown"][:]

    for quote in categories_v31["current"]:
        is_review, reason, confidence = is_speaker_review_v32(quote)
        if is_review:
            annotated = dict(quote)
            annotated["layer"] = "speaker_review"
            annotated["layer_reason"] = reason
            annotated["confidence"] = confidence
            categories["speaker_review"].append(annotated)
        else:
            categories["current"].append(quote)

    for quote in categories_v31["jijin"] + categories_v31["special"] + categories_v31["unknown"]:
        is_review, reason, confidence = is_speaker_review_v32(quote)
        if is_review:
            annotated = dict(quote)
            annotated["layer"] = "speaker_review"
            annotated["layer_reason"] = reason
            annotated["confidence"] = confidence
            categories["speaker_review"].append(annotated)

    return categories


def score_quote_for_current_v32(quote):
    text = str(quote.get("quote_text", ""))
    score = 0
    for keyword, weight in [
        ("吾", 5),
        ("隐鸢阁", 4),
        ("师尊", 4),
        ("阁主", 3),
        ("仙君", 3),
        ("随吾", 3),
        ("收声", 3),
        ("不可", 3),
        ("不必", 3),
        ("不要", 2),
        ("记住", 2),
        ("何罪", 2),
        ("很奇怪吗", 2),
        ("山下", 2),
        ("回来", 2),
    ]:
        if keyword in text:
            score += weight
    if "啾" in text or any(key in text for key in V31_JIJIN_STRONG_PHRASES):
        score -= 10
    if any(marker in text for marker in COMMAND_MARKERS):
        score += 1
    if len(text) <= 20:
        score += 1
    return score


def select_current_v32_quotes(quotes, limit=200):
    scored = []
    for quote in quotes:
        scored.append((score_quote_for_current_v32(quote), quote))
    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [quote for score, quote in scored if score > 0]
    if len(selected) < limit:
        selected.extend([quote for score, quote in scored if score <= 0])
    return selected[:limit]


V33_POSITIVE_SOURCE_TITLES = [
    "左慈-",
    "夕情欢馀·左慈",
    "燃灯照夜",
    "留音匣/左慈",
    "年表/左慈",
    "天下隐光",
]
V33_POSITIVE_TEXT_KEYWORDS = [
    "吾",
    "隐鸢阁",
    "师尊",
    "阁主",
    "仙君",
    "随吾",
    "收声",
    "不可",
    "不必",
    "不要",
    "记住",
    "何罪",
    "很奇怪吗",
    "山下",
    "回来",
    "你",
]
V33_EXCLUDE_TEXT_PATTERNS = [
    "文件:",
    ".png",
    "q版",
    "！！！",
    "啾",
    "唔，唔……鸢",
    "呼……嗒",
    "那团白兔般的毛球",
    "白兔",
    "毛球",
    "流星雨飘",
    "爪痛",
    "绒绒",
    "负三万八千",
    "那团",
    "突然转向",
    "显露出来",
    "咬向",
    "身边的",
    "树动了",
]
V33_EXCLUDE_TITLE_PATTERNS = [
    "三国志绒绒版",
    "测试刊",
    "沙盒",
    "家具",
    "活动玩法",
    "相见对话/左慈",
]
V33_DIRECT_NOT_LEFT_TEXT = [
    "左慈？！",
    "左慈？",
    "左慈！",
    "师尊？！",
    "师尊？",
]


def quote_text_clean_length(text):
    cleaned = re.sub(r"[\W_]+", "", text)
    return len(cleaned)


def should_exclude_default_roleplay_v33(quote):
    text = str(quote.get("quote_text", ""))
    title = str(quote.get("source_title", ""))
    if any(pattern in title for pattern in V33_EXCLUDE_TITLE_PATTERNS):
        return True, f"source_title 包含排除模式：{title}"
    for pattern in V33_EXCLUDE_TEXT_PATTERNS:
        if pattern in text:
            return True, f"quote_text 包含排除模式：{pattern}"
    if any(pattern in text for pattern in V33_DIRECT_NOT_LEFT_TEXT):
        if not any(word in text for word in ["吾", "隐鸢阁", "随吾", "收声", "阁主", "仙君"]):
            return True, "疑似他人称呼左慈/师尊的台词"
    clean_len = quote_text_clean_length(text)
    if clean_len < 2 or text.strip() in {"……", "？？？", "！！！"}:
        return True, "台词过短或仅为标点/省略号"
    return False, ""


def default_roleplay_score_v33(quote):
    text = str(quote.get("quote_text", ""))
    title = str(quote.get("source_title", ""))
    score = 0
    for keyword, weight in [
        ("吾", 6),
        ("隐鸢阁", 5),
        ("师尊", 5),
        ("阁主", 4),
        ("仙君", 4),
        ("随吾", 4),
        ("收声", 4),
        ("不可", 4),
        ("不必", 4),
        ("不要", 3),
        ("记住", 3),
        ("何罪", 3),
        ("很奇怪吗", 3),
        ("山下", 3),
        ("回来", 3),
        ("你", 2),
    ]:
        if keyword in text:
            score += weight
    if any(pattern in title for pattern in V33_POSITIVE_SOURCE_TITLES):
        score += 5
    if any(marker in text for marker in COMMAND_MARKERS):
        score += 2
    if "？" in text or "?" in text:
        score += 1
    if "！" in text or "!" in text:
        score += 1
    return score


def build_default_roleplay_v33(quote_categories_v32):
    candidates = quote_categories_v32["current"]
    selected = []
    excluded = []

    for quote in candidates:
        exclude, reason = should_exclude_default_roleplay_v33(quote)
        if exclude:
            excluded.append({
                "source_title": quote.get("source_title", ""),
                "quote_text": quote.get("quote_text", ""),
                "exclude_reason": reason,
                "url": quote.get("url", ""),
            })
            continue
        positive_reason = ""
        if any(pattern in str(quote.get("source_title", "")) for pattern in V33_POSITIVE_SOURCE_TITLES):
            positive_reason = "来源为左慈核心剧情标题，适合作为默认语气。"
        elif any(keyword in str(quote.get("quote_text", "")) for keyword in V33_POSITIVE_TEXT_KEYWORDS):
            positive_reason = "包含默认左慈语气关键词，适合作为默认语气。"
        else:
            positive_reason = "当前 current_v32 台词，未触发排除条件。"

        selected.append({
            "source_title": quote.get("source_title", ""),
            "section": quote.get("section", ""),
            "url": quote.get("url", ""),
            "quote_text": quote.get("quote_text", ""),
            "reason": positive_reason,
            "score": default_roleplay_score_v33(quote),
        })

    selected.sort(key=lambda item: item["score"], reverse=True)
    selected = selected[:120]
    return selected, excluded


def format_default_roleplay_v33(quote):
    lines = [
        f"## {quote.get('source_title', '')} — {quote.get('section', '')}",
        f"- url: {quote.get('url', '')}",
        f"- quote_text: {quote.get('quote_text', '')}",
        f"- reason: {quote.get('reason', '')}",
        "",
    ]
    return "\n".join(lines)


def format_excluded_default_v33(quote):
    lines = [
        f"## {quote.get('source_title', '')}",
        f"- url: {quote.get('url', '')}",
        f"- quote_text: {quote.get('quote_text', '')}",
        f"- exclude_reason: {quote.get('exclude_reason', '')}",
        "",
    ]
    return "\n".join(lines)


def build_profile_v32(core_records, quote_records):
    lines = ["# 左慈分层人物档案 V32\n"]
    lines.append("## 当前左慈/师尊/阁主层")
    lines.append("- 默认角色语气使用 current_v32。")
    lines.append("- current_v32 来源于 current_v31，但剔除 speaker_review_v32 中疑似他人说话的台词。")
    lines.append("- 这层包含隐鸢阁、师尊、阁主、仙君、左君、燃灯照夜等称谓，与当前左慈身份一致。\n")

    lines.append("## speaker_review_v32")
    lines.append("- 收纳疑似不是左慈本人说的话，作为复核池。")
    lines.append("- 这类台词不应进入默认左慈语料或 current_v32。\n")

    lines.append("## 姬晋/八百年前层")
    lines.append("- jijin_v31 代表过去身份/回忆/特殊触发，不等同于当前日常人格。\n")

    lines.append("## 特殊状态层")
    lines.append("- special_v31 代表拟声、异常或特殊活动状态，不进入默认日常语气。\n")

    lines.append("## 调用规则")
    lines.append("- 默认：current_v32。")
    lines.append("- 当用户提到姬晋、八百年前、平陵、母后、前尘、过去身份、梦境回忆时：调用 jijin_v31。")
    lines.append("- 当触发特殊活动/异常状态时：调用 special_v31。")
    lines.append("- 当台词疑似他人称呼或提问左慈时：进入 speaker_review_v32，避免作为默认左慈台词。\n")

    return "\n".join(lines).strip()


def analyze_speech_style_v32(quote_records):
    categories_v32 = build_quote_categories_v32(quote_records)
    current = categories_v32["current"]
    counter = Counter()
    for quote in current:
        text = str(quote.get("quote_text", ""))
        if not text:
            continue
        counter["quote_count"] += 1
        counter["吾"] += int("吾" in text)
        counter["隐鸢阁"] += int("隐鸢阁" in text)
        counter["师尊"] += int("师尊" in text)
        counter["question"] += int("？" in text or "?" in text)
        counter["exclam"] += int("！" in text or "!" in text)
        counter["short"] += int(len(text) <= 20)
        counter["command"] += int(any(marker in text for marker in ["来", "去", "随吾", "收声", "不可", "不必", "莫", "退下", "停", "看", "听", "记住"]))
        counter["strong"] += int("！" in text or any(marker in text for marker in ["来", "去", "随吾", "收声", "不可", "不必", "莫", "退下", "停", "看", "听", "记住"]))

    lines = ["# 左慈说话风格 V32\n"]
    lines.append("## current_v32 说话风格")
    lines.append(f"- quote_count: {counter['quote_count']}")
    lines.append(f"- 含“吾”的台词数量: {counter['吾']}")
    lines.append(f"- 含“隐鸢阁”的台词数量: {counter['隐鸢阁']}")
    lines.append(f"- 含“师尊”的台词数量: {counter['师尊']}")
    lines.append(f"- 含问号“？”的台词数量: {counter['question']}")
    lines.append(f"- 含叹号“！”的台词数量: {counter['exclam']}")
    lines.append(f"- 短句数量(<=20): {counter['short']}")
    lines.append(f"- 命令/指令句数量: {counter['command']}")
    lines.append(f"- 强语气数量: {counter['strong']}")
    lines.append("")
    current_examples = {
        "权威/压迫感": [q for q in current if any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住"])][:8],
        "隐鸢阁立场": [q for q in current if "隐鸢阁" in str(q.get("quote_text", ""))][:8],
        "对广陵王/“我”": [q for q in current if any(word in str(q.get("quote_text", "")) for word in ["广陵王", "广陵君", "我"])][:8],
        "反问与判断": [q for q in current if "？" in str(q.get("quote_text", "")) or "?" in str(q.get("quote_text", ""))][:8],
        "克制温柔": [q for q in current if any(word in str(q.get("quote_text", "")) for word in ["吾", "师尊"]) and not any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住"])][:8],
        "命令/保护": [q for q in current if any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住", "来", "去"])][:8],
    }
    for category, examples in current_examples.items():
        lines.append(f"### {category}")
        if examples:
            for quote in examples:
                lines.append(f"- {quote.get('quote_text', '')}")
        else:
            lines.append("- (无足够示例)")
        lines.append("")
    lines.append("## 附注")
    lines.append("- jijin_v31 与 special_v31 的统计说明保持原有 V31 结构。")
    lines.append("- current_v32 为更严格的默认左慈语气样本，不含 speaker_review_v32 台词。\n")
    return "\n".join(lines).strip()


def build_profile_v33(default_roleplay_v33, excluded_default_v33):
    lines = ["# 左慈角色卡可用设定 V33\n"]
    lines.append("## 默认身份层")
    lines.append("- 当前左慈/师尊/阁主/隐鸢阁核心人物。")
    lines.append("- 默认语气调用 default_roleplay_v33。")
    lines.append("- default_roleplay_v33 仅保留最适合投喂的左慈默认语气台词。\n")

    lines.append("## 默认语气调用")
    lines.append("- 使用默认角色可投喂台词池 default_roleplay_v33，而非 broader current_v32。")
    lines.append("- speaker_review_v32 为说话人疑似误判池，不进入默认左慈语料。")
    lines.append("- jijin_v31 为姬晋/过去线，仅在触发历史/梦境时调用。")
    lines.append("- special_v31 为绒绒、啾啾、拟声、活动异常，仅在特殊剧情触发时调用。\n")

    lines.append("## 使用禁忌")
    lines.append("- 不要把姬晋语气当默认左慈。")
    lines.append("- 不要把绒绒/啾啾当默认左慈。")
    lines.append("- 不要把“师尊”写成左慈自称。")
    lines.append("- 不要过度甜宠、撒娇、现代口语化。\n")

    lines.append("## 统计说明")
    lines.append(f"- default_roleplay_quote_v33_count: {len(default_roleplay_v33)}")
    lines.append(f"- excluded_default_quote_v33_count: {len(excluded_default_v33)}")
    lines.append("- default_roleplay_v33 样本更干净，更适合作为角色卡默认语气。\n")

    return "\n".join(lines).strip()


def analyze_speech_style_v33(default_roleplay_v33, excluded_default_v33):
    counter = Counter()
    for quote in default_roleplay_v33:
        text = str(quote.get("quote_text", ""))
        if not text:
            continue
        counter["default_quote_count_v33"] += 1
        counter["吾"] += int("吾" in text)
        counter["隐鸢阁"] += int("隐鸢阁" in text)
        counter["师尊"] += int("师尊" in text)
        counter["question"] += int("？" in text or "?" in text)
        counter["exclam"] += int("！" in text or "!" in text)
        counter["short"] += int(len(text) <= 20)
        counter["command"] += int(any(marker in text for marker in ["来", "去", "随吾", "收声", "不可", "不必", "莫", "退下", "停", "看", "听", "记住"]))

    lines = ["# 左慈说话风格 V33\n"]
    lines.append(f"- default_quote_count_v33: {counter['default_quote_count_v33']}")
    lines.append(f"- excluded_default_quote_count_v33: {len(excluded_default_v33)}")
    lines.append(f"- 含“吾”的台词数量: {counter['吾']}")
    lines.append(f"- 含“隐鸢阁”的台词数量: {counter['隐鸢阁']}")
    lines.append(f"- 含“师尊”的台词数量: {counter['师尊']}")
    lines.append(f"- 含问号“？”的台词数量: {counter['question']}")
    lines.append(f"- 含叹号“！”的台词数量: {counter['exclam']}")
    lines.append(f"- 短句数量(<=20): {counter['short']}")
    lines.append(f"- 命令/指令句数量: {counter['command']}")
    lines.append("")
    lines.append("## 默认左慈语气总结")
    lines.append("- 自称优先“吾”。")
    lines.append("- “师尊”通常是别人对他的称呼，不是他的自称。")
    lines.append("- 语气冷静、克制、短句多。")
    lines.append("- 对外人有边界和压迫感。")
    lines.append("- 对广陵王有提醒、庇护、偶尔无奈/纵容。")
    lines.append("- 不要默认使用姬晋幼态/迷茫语气。")
    lines.append("- 不要默认使用绒绒/啾啾/拟声状态。\n")

    current_examples = {
        "权威/压迫感": [q for q in default_roleplay_v33 if any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住"])][:6],
        "隐鸢阁立场": [q for q in default_roleplay_v33 if "隐鸢阁" in str(q.get("quote_text", ""))][:6],
        "对广陵王/“我”": [q for q in default_roleplay_v33 if any(word in str(q.get("quote_text", "")) for word in ["广陵王", "广陵君", "我"])][:6],
        "反问与判断": [q for q in default_roleplay_v33 if "？" in str(q.get("quote_text", "")) or "?" in str(q.get("quote_text", ""))][:6],
        "克制温柔": [q for q in default_roleplay_v33 if any(word in str(q.get("quote_text", "")) for word in ["吾", "师尊"]) and not any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住"])][:6],
        "命令/保护": [q for q in default_roleplay_v33 if any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住", "来", "去"])][:6],
    }
    for category, examples in current_examples.items():
        lines.append(f"### {category}")
        if examples:
            for quote in examples:
                lines.append(f"- {quote.get('quote_text', '')}")
        else:
            lines.append("- (无足够示例)")
        lines.append("")

    return "\n".join(lines).strip()


def build_profile_v31(core_records, quote_records):
    categories = build_quote_categories_v31(quote_records)
    current = categories["current"][:6]
    jijin = categories["jijin"][:6]
    special = categories["special"][:6]

    lines = ["# 左慈分层人物档案 V31\n"]
    lines.append("## 当前左慈/师尊/阁主层")
    lines.append("- 默认角色扮演主语气应使用 current_v31。")
    lines.append("- 这层包含隐鸢阁、师尊、阁主、仙君、左君、燃灯照夜等称谓。")
    lines.append("- 即使出现在其他角色剧情中，只要上下文为当前师尊出场，也应作为当前左慈语料。 ")
    if current:
        lines.append("- 代表示例：")
        for quote in current:
            lines.append(f"  - {quote.get('quote_text', '')}（来源：{quote.get('source_title', '')}）")
    lines.append("- 强调：此层是默认日常与剧情主体语气，不应与过去线混合。\n")

    lines.append("## 姬晋/八百年前层")
    lines.append("- 仅收录强特征命中的过去线，代表过去身份/回忆/特殊触发。")
    lines.append("- 强调：姬晋层是过去身份/前史线，不等于当前默认日常人格。 ")
    if jijin:
        lines.append("- 代表示例：")
        for quote in jijin:
            lines.append(f"  - {quote.get('quote_text', '')}（来源：{quote.get('source_title', '')}）")
    lines.append("- 待确认：这些台词的记忆触发方式与当前身份的情感延续。\n")

    lines.append("## 特殊状态层")
    lines.append("- 包含啾啾、拟声、动物化、异常表达的语料。")
    lines.append("- 仅用于特殊剧情触发，不作为默认语气。 ")
    if special:
        lines.append("- 代表示例：")
        for quote in special:
            lines.append(f"  - {quote.get('quote_text', '')}（来源：{quote.get('source_title', '')}）")
    lines.append("- 这层语料应单独保留，避免混入 current_v31。\n")

    lines.append("## 调用规则")
    lines.append("- 默认：current_v31。")
    lines.append("- 用户提到姬晋、八百年前、平陵、母后、前尘、过去身份、梦境回忆时：调用 jijin_v31。")
    lines.append("- 触发特殊活动/异常状态时：调用 special_v31。")
    lines.append("- 不要把过去线与当前日常人格混成一个整体。\n")

    return "\n".join(lines).strip()


def analyze_speech_style_v31(quote_records):
    categories = build_quote_categories_v31(quote_records)
    counts = {}

    def stats_for(quotes):
        counter = Counter()
        for quote in quotes:
            text = str(quote.get("quote_text", ""))
            if not text:
                continue
            counter["quote_count"] += 1
            counter["吾"] += int("吾" in text)
            counter["隐鸢阁"] += int("隐鸢阁" in text)
            counter["师尊"] += int("师尊" in text)
            counter["question"] += int("？" in text or "?" in text)
            counter["exclam"] += int("！" in text or "!" in text)
            counter["short"] += int(len(text) <= 20)
            counter["command"] += int(any(marker in text for marker in ["来", "去", "随吾", "收声", "不可", "不必", "莫", "退下", "停", "看", "听", "记住"]))
            counter["strong"] += int("！" in text or any(marker in text for marker in ["来", "去", "随吾", "收声", "不可", "不必", "莫", "退下", "停", "看", "听", "记住"]))
        return counter

    counts["current"] = stats_for(categories["current"])
    counts["jijin"] = stats_for(categories["jijin"])
    counts["special"] = stats_for(categories["special"])

    current_examples = {
        "权威/压迫感": [q for q in categories["current"] if any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住"])][:4],
        "隐鸢阁立场": [q for q in categories["current"] if "隐鸢阁" in str(q.get("quote_text", ""))][:4],
        "对广陵王/“我”": [q for q in categories["current"] if any(word in str(q.get("quote_text", "")) for word in ["广陵王", "广陵君", "我"])][:4],
        "反问与判断": [q for q in categories["current"] if "？" in str(q.get("quote_text", "")) or "?" in str(q.get("quote_text", ""))][:4],
        "克制温柔": [q for q in categories["current"] if any(word in str(q.get("quote_text", "")) for word in ["吾", "师尊"]) and not any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住"])][:4],
        "命令/保护": [q for q in categories["current"] if any(marker in str(q.get("quote_text", "")) for marker in ["随吾", "收声", "退下", "不可", "记住", "来", "去"])][:4],
    }

    lines = ["# 左慈说话风格 V31\n"]
    for name in ["current", "jijin", "special"]:
        lines.append(f"## {name} 说话风格")
        counter = counts[name]
        lines.append(f"- quote_count: {counter['quote_count']}")
        lines.append(f"- 含“吾”的台词数量: {counter['吾']}")
        lines.append(f"- 含“隐鸢阁”的台词数量: {counter['隐鸢阁']}")
        lines.append(f"- 含“师尊”的台词数量: {counter['师尊']}")
        lines.append(f"- 含问号“？”的台词数量: {counter['question']}")
        lines.append(f"- 含叹号“！”的台词数量: {counter['exclam']}")
        lines.append(f"- 短句数量(<=20): {counter['short']}")
        lines.append(f"- 命令/指令句数量: {counter['command']}")
        lines.append(f"- 强语气数量: {counter['strong']}")
        lines.append("")
        if name == "current":
            lines.append("- 自称：以“吾”为主。")
            lines.append("- 语气：冷静、克制，有权威与保护感。")
            lines.append("- 句式：短句、命令句、反问句为主。\n")
            lines.append("### current_v31 典型台词示例")
            for category, examples in current_examples.items():
                lines.append(f"- {category}：")
                if examples:
                    for quote in examples:
                        lines.append(f"  - {quote.get('quote_text', '')}")
                else:
                    lines.append("  - (无足够示例)")
            lines.append("")
        elif name == "jijin":
            lines.append("- 特点：更显过去线/回忆感，包含姬晋、平陵、母后、前尘等强判定关键词。")
            lines.append("- 语气：较为迷茫、依恋，情绪带有历史记忆气息。\n")
        else:
            lines.append("- 特点：拟声、动物化或异常状态表达，不应作为默认日常语气使用。\n")

    return "\n".join(lines).strip()


def collect_relationships(core_records, candidate_records):
    sources = core_records + candidate_records
    relation_entries = []

    for label, keywords, default_relation in RELATION_TARGETS:
        snippets = []
        titles = []
        for rec in sources:
            text = normalize_text_for_search(rec.get("text", ""))
            match_count = sum(1 for keyword in keywords if keyword in text)
            if match_count > 0:
                for line in text.splitlines():
                    if any(keyword in line for keyword in keywords):
                        snippet = line.strip()
                        if snippet and snippet not in snippets:
                            snippets.append(snippet)
                titles.append(rec.get("title"))
        titles = sorted(set(titles))
        if not titles:
            continue

        relation_entries.append({
            "对方": label,
            "关系类型": default_relation,
            "互动特点": snippets[:5] or ["基于文本线索，尚需人工确认具体互动方式。"],
            "相关来源标题": titles,
            "待确认点": "是否为正式师徒/同盟/政治关系需人工确认。",
        })

    lines = ["# 左慈关系记忆整理\n"]
    for entry in relation_entries:
        lines.append(f"## 对方：{entry['对方']}")
        lines.append(f"- 关系类型：{entry['关系类型']}")
        lines.append("- 互动特点：")
        for snippet in entry["互动特点"]:
            lines.append(f"  - {snippet}")
        lines.append("- 相关来源标题：")
        for title in entry["相关来源标题"]:
            lines.append(f"  - {title}")
        lines.append(f"- 待确认点：{entry['待确认点']}")
        lines.append("")

    return "\n".join(lines).strip()


def build_story_timeline(core_records, candidate_records):
    lines = ["# 左慈剧情时间线原始条目\n"]
    for rec in core_records + candidate_records:
        lines.append(f"## {rec.get('title')} — {rec.get('pageid')}")
        lines.append(f"- url: {rec.get('url')}")
        if rec.get("category_type"):
            lines.append(f"- category_type: {rec.get('category_type')}")
        lines.append("- 清洗后的片段：")
        text = clean_text(rec.get("text", ""))
        if text:
            for text_line in text.splitlines():
                lines.append(f"  {text_line}")
        else:
            lines.append("  (无可用文本)")
        lines.append("")
    return "\n".join(lines).strip()


def clean_worldbook_seed(seed_records):
    result = []
    for rec in seed_records:
        key = rec.get("key")
        if not key:
            continue
        source_pages = []
        seen = set()
        for page in rec.get("source_pages", []):
            page_key = (page.get("pageid"), page.get("title"))
            if page_key in seen:
                continue
            seen.add(page_key)
            if should_exclude_worldbook_page(page, key):
                continue
            source_pages.append(page)
            if len(source_pages) >= 20:
                break

        entry = {
            "key": key,
            "aliases": rec.get("aliases", []),
            "type": WORLD_BOOK_TYPE.get(key, "concept"),
            "priority": 100 if key in {"左慈", "师尊", "隐鸢阁", "仙门"} else 80,
            "description": rec.get("description", "") or "",
            "trigger_words": [key] + rec.get("aliases", []),
            "source_pages": source_pages,
        }
        result.append(entry)

    existing_keys = {entry["key"] for entry in result}
    for key in FINAL_WORLDBOOK_KEYS:
        if key not in existing_keys:
            result.append({
                "key": key,
                "aliases": [],
                "type": WORLD_BOOK_TYPE.get(key, "concept"),
                "priority": 100 if key in {"左慈", "师尊", "隐鸢阁", "仙门"} else 80,
                "description": "",
                "trigger_words": [key],
                "source_pages": [],
            })

    return result


def should_exclude_worldbook_page(page, key):
    title = page.get("title", "")
    category_type = page.get("category_type", "")
    if "沙盒" in title or "沙盒" in category_type:
        return True
    if category_type == "家具/道具" and "左慈" not in title and key != "左慈":
        return True
    if "称号" in title and "左慈" not in title:
        return True
    if key == "仙门":
        blocked = ["引仙门", "迎仙门", "会诊乱仙门"]
        if any(block in title for block in blocked):
            return True
    if "家具" in title and "左慈" not in title and key != "左慈":
        return True
    return False


def select_representative_quotes(quotes):
    scored = []
    for quote in quotes:
        text = quote.get("quote_text", "")
        score = 0
        if "吾" in text:
            score += 3
        if "隐鸢阁" in text:
            score += 3
        if "师尊" in text:
            score += 3
        if "？" in text or "?" in text:
            score += 2
        if "！" in text or "!" in text:
            score += 1
        if any(marker in text for marker in COMMAND_MARKERS):
            score += 2
        if len(text) <= 6:
            score -= 1
        scored.append((score, quote))

    scored.sort(key=lambda item: item[0], reverse=True)
    selected = [quote for score, quote in scored if score > 0]
    if len(selected) < 200:
        selected.extend([quote for score, quote in scored if score <= 0])
    return selected[:200]


ITEM_KEYWORDS = [
    "左慈·自由摆放家具",
    "左慈",
    "师尊",
    "隐鸢阁",
]

ITEM_DESCRIPTION_EXCLUDE_LINES = {
    "编",
    "刷",
    "历",
    "道具总览",
    "获取",
    "【置物】家具染色",
    "【墙纸】家具染色",
    "【墙纸】家具打造",
    "【地板】家具染色",
    "【地板】家具打造",
    "家具染色",
    "家具打造",
    "墙纸自选包",
    "地板自选包",
}

ITEM_DESCRIPTION_EXCLUDE_CONTAINS = [
    "MediaWiki",
    "看到此行说明js未正常加载",
    "授权转载",
    "如有更多投稿",
    "action=edit",
    "redlink=1",
]

ITEM_TITLE_EXCLUDE_SUBSTRINGS = [
    "家具采购单",
    "家具沙盒",
    "测试",
]

ITEM_SOURCE_EXCLUDE_KEYWORDS = [
    "沙盒",
]


def record_contains_item_keyword(rec):
    search_fields = []
    for field in ("title", "source_title", "displaytitle", "description", "text", "url"):
        value = rec.get(field, "")
        if value:
            search_fields.append(str(value))
    combined = "\n".join(search_fields)
    return any(keyword in combined for keyword in ITEM_KEYWORDS)


def is_excluded_item(rec):
    title = str(rec.get("title", ""))
    source_title = str(rec.get("source_title", ""))
    displaytitle = str(rec.get("displaytitle", ""))
    url = str(rec.get("url", ""))

    if any(sub in title for sub in ITEM_TITLE_EXCLUDE_SUBSTRINGS):
        return True
    if any(keyword in title for keyword in ITEM_SOURCE_EXCLUDE_KEYWORDS):
        return True
    if any(keyword in source_title for keyword in ITEM_SOURCE_EXCLUDE_KEYWORDS):
        return True
    if any(keyword in displaytitle for keyword in ITEM_SOURCE_EXCLUDE_KEYWORDS):
        return True
    if any(keyword in url for keyword in ITEM_SOURCE_EXCLUDE_KEYWORDS):
        return True

    return False


def clean_item_description(text, title):
    lines = []
    added = set()
    for raw_line in str(text).splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line == title:
            continue
        if line in ITEM_DESCRIPTION_EXCLUDE_LINES:
            continue
        if any(substr in line for substr in ITEM_DESCRIPTION_EXCLUDE_CONTAINS):
            continue
        if line in added:
            continue
        lines.append(line)
        added.add(line)
    return "\n".join(lines).strip()


def extract_item_type(rec):
    title = str(rec.get("title", ""))
    description = str(rec.get("description", ""))
    text = str(rec.get("text", ""))
    if "左慈·自由摆放家具" in description or "左慈·自由摆放家具" in text:
        return "左慈·自由摆放家具"
    if "左慈" in description or "左慈" in text:
        return "左慈相关物品"
    return "左慈相关候选"


def build_item_memory(md_items, json_items):
    selected = []
    seen_keys = set()

    def add_item(rec):
        pageid = rec.get("pageid")
        title = str(rec.get("title", ""))
        key = (pageid, title)
        if key in seen_keys:
            return
        seen_keys.add(key)

        raw_description = str(rec.get("description", "")) or str(rec.get("text", ""))
        description = clean_item_description(raw_description, title)
        if not description:
            return

        source_note = ""
        for keyword in ["左慈·自由摆放家具", "左慈", "师尊", "隐鸢阁"]:
            if keyword in title or keyword in description or keyword in str(rec.get("source_title", "")) or keyword in str(rec.get("displaytitle", "")):
                source_note = keyword
                break

        selected.append({
            "title": title,
            "pageid": pageid,
            "url": rec.get("url", ""),
            "item_type": extract_item_type(rec),
            "description": description,
            "source_note": source_note,
        })

    for item in md_items:
        if is_excluded_item(item):
            continue
        if record_contains_item_keyword(item):
            add_item(item)

    for item in json_items:
        if is_excluded_item(item):
            continue
        if record_contains_item_keyword(item):
            add_item(item)

    return selected


def render_markdown_sections(records, fields, header_prefix="###"):
    lines = []
    for rec in records:
        lines.append(f"{header_prefix} {rec.get('title')} — {rec.get('pageid')}")
        for field_name, label, formatter in fields:
            value = rec.get(field_name, "")
            if not value:
                continue
            if formatter == "text":
                lines.append(f"- {label}:")
                for part in str(value).splitlines():
                    lines.append(f"  {part}")
            else:
                lines.append(f"- {label}: {value}")
        lines.append("")
    return "\n".join(lines).strip()


def main():
    core_records = load_md_records(INPUT_CORE_NARRATIVE)
    item_records = load_md_records(INPUT_ITEMS_FURNITURE)
    candidate_records = load_md_records(INPUT_CANDIDATE_REVIEW)
    quote_records = load_jsonl(INPUT_QUOTES_V2)
    item_candidate_json = []
    INPUT_ITEM_CANDIDATE_JSONL = Path("data/leftci_core/leftci_item_candidate_pages.jsonl")
    if INPUT_ITEM_CANDIDATE_JSONL.exists():
        item_candidate_json = load_jsonl(INPUT_ITEM_CANDIDATE_JSONL)

    worldbook_seed = []
    if INPUT_WORLDBOOK_SEED.exists():
        with INPUT_WORLDBOOK_SEED.open("r", encoding="utf-8") as fh:
            try:
                worldbook_seed = json.load(fh)
            except json.JSONDecodeError:
                worldbook_seed = []

    profile_md = build_profile(core_records, quote_records)
    speech_md = analyze_speech_style(quote_records)
    relationship_md = collect_relationships(core_records, candidate_records)
    timeline_md = build_story_timeline(core_records, candidate_records)
    worldbook_clean = clean_worldbook_seed(worldbook_seed)
    selected_quotes = select_representative_quotes(quote_records)
    item_memory_records = build_item_memory(item_records, item_candidate_json)

    with (OUTPUT_DIR / "01_leftci_profile.md").open("w", encoding="utf-8") as fh:
        fh.write(profile_md + "\n")

    with (OUTPUT_DIR / "02_leftci_speech_style.md").open("w", encoding="utf-8") as fh:
        fh.write(speech_md + "\n")

    with (OUTPUT_DIR / "03_leftci_relationship_memory.md").open("w", encoding="utf-8") as fh:
        fh.write(relationship_md + "\n")

    with (OUTPUT_DIR / "04_leftci_story_timeline_raw.md").open("w", encoding="utf-8") as fh:
        fh.write(timeline_md + "\n")

    with (OUTPUT_DIR / "05_leftci_worldbook_clean.json").open("w", encoding="utf-8") as fh:
        json.dump(worldbook_clean, fh, ensure_ascii=False, indent=2)

    profile_v2_md = build_profile_v2(core_records, quote_records, worldbook_clean)
    with (OUTPUT_DIR / "01_leftci_profile_v2.md").open("w", encoding="utf-8") as fh:
        fh.write(profile_v2_md + "\n")

    speech_style_v2_md = analyze_speech_style_v2(quote_records)
    with (OUTPUT_DIR / "02_leftci_speech_style_v2.md").open("w", encoding="utf-8") as fh:
        fh.write(speech_style_v2_md + "\n")

    quote_categories_v3 = build_quote_categories_v3(quote_records)
    profile_v3_md = build_profile_v3(core_records, quote_records)
    with (OUTPUT_DIR / "01_leftci_profile_v3.md").open("w", encoding="utf-8") as fh:
        fh.write(profile_v3_md + "\n")

    speech_style_v3_md = analyze_speech_style_v3(quote_records)
    with (OUTPUT_DIR / "02_leftci_speech_style_v3.md").open("w", encoding="utf-8") as fh:
        fh.write(speech_style_v3_md + "\n")

    selected_current_v3 = select_current_v3_quotes(quote_categories_v3["current"], limit=200)
    with (OUTPUT_DIR / "06_leftci_quotes_selected_current_v3.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category(selected_current_v3, "左慈当前默认台词 current_v3") + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_selected_jijin_v3.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category(quote_categories_v3["jijin"], "左慈姬晋/八百年前台词 jijin_v3") + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_selected_special_v3.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category(quote_categories_v3["special"], "左慈特殊状态台词 special_v3") + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_selected_unknown_v3.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category(quote_categories_v3["unknown"], "左慈未分类/可复核台词 unknown_v3") + "\n")

    quote_categories_v31 = build_quote_categories_v31(quote_records)
    profile_v31_md = build_profile_v31(core_records, quote_records)
    with (OUTPUT_DIR / "01_leftci_profile_v31.md").open("w", encoding="utf-8") as fh:
        fh.write(profile_v31_md + "\n")

    speech_style_v31_md = analyze_speech_style_v31(quote_records)
    with (OUTPUT_DIR / "02_leftci_speech_style_v31.md").open("w", encoding="utf-8") as fh:
        fh.write(speech_style_v31_md + "\n")

    selected_current_v31 = select_current_v31_quotes(quote_categories_v31["current"], limit=200)
    with (OUTPUT_DIR / "06_leftci_quotes_selected_current_v31.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category_v31(selected_current_v31, "左慈当前默认台词 current_v31") + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_selected_jijin_v31.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category_v31(quote_categories_v31["jijin"], "左慈姬晋/八百年前台词 jijin_v31") + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_selected_special_v31.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category_v31(quote_categories_v31["special"], "左慈特殊状态台词 special_v31") + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_selected_unknown_v31.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category_v31(quote_categories_v31["unknown"], "左慈未分类/可复核台词 unknown_v31") + "\n")

    quote_categories_v32 = build_quote_categories_v32(quote_records)
    profile_v32_md = build_profile_v32(core_records, quote_records)
    with (OUTPUT_DIR / "01_leftci_profile_v32.md").open("w", encoding="utf-8") as fh:
        fh.write(profile_v32_md + "\n")

    speech_style_v32_md = analyze_speech_style_v32(quote_records)
    with (OUTPUT_DIR / "02_leftci_speech_style_v32.md").open("w", encoding="utf-8") as fh:
        fh.write(speech_style_v32_md + "\n")

    selected_current_v32 = select_current_v32_quotes(quote_categories_v32["current"], limit=200)
    with (OUTPUT_DIR / "06_leftci_quotes_selected_current_v32.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category_v31(selected_current_v32, "左慈当前默认台词 current_v32") + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_speaker_review_v32.md").open("w", encoding="utf-8") as fh:
        fh.write(build_quote_md_for_category_v31(quote_categories_v32["speaker_review"], "左慈疑似他人台词 speaker_review_v32") + "\n")

    default_roleplay_v33, excluded_default_v33 = build_default_roleplay_v33(quote_categories_v32)
    profile_v33_md = build_profile_v33(default_roleplay_v33, excluded_default_v33)
    with (OUTPUT_DIR / "01_leftci_profile_v33.md").open("w", encoding="utf-8") as fh:
        fh.write(profile_v33_md + "\n")

    speech_style_v33_md = analyze_speech_style_v33(default_roleplay_v33, excluded_default_v33)
    with (OUTPUT_DIR / "02_leftci_speech_style_v33.md").open("w", encoding="utf-8") as fh:
        fh.write(speech_style_v33_md + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_default_roleplay_v33.md").open("w", encoding="utf-8") as fh:
        lines = ["# 左慈默认角色可投喂台词 V33\n"]
        for quote in default_roleplay_v33:
            lines.append(format_default_roleplay_v33(quote))
        fh.write("\n".join(lines).strip() + "\n")

    with (OUTPUT_DIR / "06_leftci_quotes_excluded_from_default_v33.md").open("w", encoding="utf-8") as fh:
        lines = ["# 左慈默认语气排除台词 V33\n"]
        for quote in excluded_default_v33:
            lines.append(format_excluded_default_v33(quote))
        fh.write("\n".join(lines).strip() + "\n")

    selected_lines = ["# 左慈代表性台词筛选\n"]
    for quote in selected_quotes:
        selected_lines.append(f"## {quote.get('source_title', '')} — {quote.get('section', '')}")
        selected_lines.append(f"- url: {quote.get('url', '')}")
        selected_lines.append(f"- quote_text: {quote.get('quote_text', '')}")
        selected_lines.append("")
    with (OUTPUT_DIR / "06_leftci_quotes_selected.md").open("w", encoding="utf-8") as fh:
        fh.write("\n".join(selected_lines).strip() + "\n")

    item_lines = ["# 左慈物品记忆\n"]
    for item in item_memory_records:
        item_lines.append(f"## {item.get('title')} — {item.get('pageid')}")
        item_lines.append(f"- url: {item.get('url', '')}")
        item_lines.append(f"- item_type: {item.get('item_type', '')}")
        item_lines.append(f"- source_note: {item.get('source_note', '')}")
        item_lines.append("- description:")
        for text_line in item.get('description', "").splitlines():
            item_lines.append(f"  {text_line}")
        item_lines.append("")
    with (OUTPUT_DIR / "07_leftci_items_memory.md").open("w", encoding="utf-8") as fh:
        fh.write("\n".join(item_lines).strip() + "\n")

    output_files = [
        "01_leftci_profile.md",
        "01_leftci_profile_v2.md",
        "01_leftci_profile_v3.md",
        "01_leftci_profile_v31.md",
        "01_leftci_profile_v32.md",
        "01_leftci_profile_v33.md",
        "02_leftci_speech_style.md",
        "02_leftci_speech_style_v2.md",
        "02_leftci_speech_style_v3.md",
        "02_leftci_speech_style_v31.md",
        "02_leftci_speech_style_v32.md",
        "02_leftci_speech_style_v33.md",
        "03_leftci_relationship_memory.md",
        "04_leftci_story_timeline_raw.md",
        "05_leftci_worldbook_clean.json",
        "06_leftci_quotes_selected.md",
        "06_leftci_quotes_selected_current_v3.md",
        "06_leftci_quotes_selected_jijin_v3.md",
        "06_leftci_quotes_selected_special_v3.md",
        "06_leftci_quotes_selected_unknown_v3.md",
        "06_leftci_quotes_selected_current_v31.md",
        "06_leftci_quotes_selected_jijin_v31.md",
        "06_leftci_quotes_selected_special_v31.md",
        "06_leftci_quotes_selected_unknown_v31.md",
        "06_leftci_quotes_selected_current_v32.md",
        "06_leftci_quotes_speaker_review_v32.md",
        "06_leftci_quotes_default_roleplay_v33.md",
        "06_leftci_quotes_excluded_from_default_v33.md",
        "07_leftci_items_memory.md",
        "leftci_final_summary.json",
    ]
    summary = {
        "input_quote_count": len(quote_records),
        "selected_quote_count": len(selected_quotes),
        "worldbook_entry_count": len(worldbook_clean),
        "item_memory_count": len(item_memory_records),
        "profile_v2_generated": True,
        "speech_style_v2_generated": True,
        "profile_v3_generated": True,
        "speech_style_v3_generated": True,
        "profile_v31_generated": True,
        "speech_style_v31_generated": True,
        "profile_v32_generated": True,
        "speech_style_v32_generated": True,
        "profile_v33_generated": True,
        "speech_style_v33_generated": True,
        "current_quote_v3_count": len(quote_categories_v3["current"]),
        "jijin_quote_v3_count": len(quote_categories_v3["jijin"]),
        "special_quote_v3_count": len(quote_categories_v3["special"]),
        "unknown_quote_v3_count": len(quote_categories_v3["unknown"]),
        "current_quote_v31_count": len(quote_categories_v31["current"]),
        "jijin_quote_v31_count": len(quote_categories_v31["jijin"]),
        "special_quote_v31_count": len(quote_categories_v31["special"]),
        "unknown_quote_v31_count": len(quote_categories_v31["unknown"]),
        "current_quote_v32_count": len(quote_categories_v32["current"]),
        "speaker_review_v32_count": len(quote_categories_v32["speaker_review"]),
        "default_roleplay_quote_v33_count": len(default_roleplay_v33),
        "excluded_default_quote_v33_count": len(excluded_default_v33),
        "output_files": output_files,
    }
    with (OUTPUT_DIR / "leftci_final_summary.json").open("w", encoding="utf-8") as fh:
        json.dump(summary, fh, ensure_ascii=False, indent=2)

    print(f"已生成最终左慈角色包，输出文件数量：{len(summary['output_files'])}")
    print(f"筛选台词：{len(selected_quotes)}，世界书条目：{len(worldbook_clean)}，物品记忆：{len(item_memory_records)}")


if __name__ == "__main__":
    main()
