from __future__ import annotations

import json
import re
import shutil
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MEMORY_DIR = ROOT / "data" / "leftci_memory_db"
MEMORIES_PATH = MEMORY_DIR / "leftci_memories.jsonl"
INDEX_PATH = MEMORY_DIR / "leftci_memory_index.json"
SCHEMA_PATH = MEMORY_DIR / "leftci_memory_schema.md"
RELATIONSHIP_CORE_PATH = MEMORY_DIR / "leftci_relationship_core.md"
RETRIEVAL_RULES_PATH = MEMORY_DIR / "leftci_memory_retrieval_rules.md"
AUDIT_PATH = MEMORY_DIR / "leftci_memory_audit.md"

BACKUP_DIR = MEMORY_DIR / "backups"


PAST_SOURCE = "06_leftci_quotes_selected_jijin_v31.md"
SPECIAL_SOURCE = "06_leftci_quotes_selected_special_v31.md"
ITEM_SOURCE = "07_leftci_items_memory.md"
WORLDBOOK_SOURCE = "05_leftci_worldbook_clean.json"
RELATIONSHIP_SOURCE = "03_leftci_relationship_memory.md"


PAST_KEYWORDS = [
    "姬晋",
    "八百年前",
    "平陵",
    "母后",
    "前尘",
    "过去身份",
    "梦境回忆",
    "回广陵吗",
    "去平陵",
    "广陵君，我们要去哪",
]

SPECIAL_KEYWORDS = [
    "绒绒",
    "啾啾",
    "啾",
    "拟声",
    "动物化",
    "特殊状态",
    "异常状态",
    "三国志绒绒版",
    "测试刊",
]

RELATIONSHIP_TERMS = [
    "师尊",
    "弟子",
    "逆徒",
    "恋人",
    "吻",
    "亲吻",
    "抱",
    "怀中",
    "枕着",
    "瘦了",
    "想你",
    "重逢",
    "不舍",
    "牵挂",
    "庇护",
    "保护",
    "阻止",
    "承诺",
    "陪你",
    "归来",
    "不要离开",
    "随吾来",
    "你的师尊",
    "吾助你",
    "山下的时局",
    "很累人吧",
]

CORE_TITLE_KEYWORDS = [
    "左慈-",
    "夕情欢馀·左慈",
    "天下隐光",
    "燃灯照夜",
    "留音匣/左慈",
    "年表/左慈",
    "左慈-恋念",
    "左慈-约会",
    "左慈-鸢记",
    "左慈-红鸾花笺",
    "信笺匣/左慈",
]

MENTION_ONLY_TITLE_KEYWORDS = [
    "公告",
    "招募战友",
    "测试手机",
    "家具采购单",
    "游戏BGM",
    "活动玩法",
    "道具总览",
]

NON_LEFTCI_ROLE_TITLE_KEYWORDS = [
    "孔融",
    "华佗",
    "黄月英",
    "张鲁",
    "刘辩",
    "张邈",
    "曹植",
    "荀攸",
    "密探留音/",
]

NOISE_LINE_PATTERNS = [
    r"^MediaWiki:",
    r"看到此行说明js未正常加载",
    r"授权转载",
    r"如有更多投稿",
    r"联系编辑部",
    r"回到顶部",
    r"上一节",
    r"下一节",
    r"^\[?\s*编辑\s*\]?$",
    r"▼展开全部▼",
    r"展开/折叠",
    r"密探语音的上传是一项巨大工程",
    r"Wiki反馈",
    r"上传规则",
    r"录入帮助",
    r"^↑$",
    r"^\d+$",
]


def now_string() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"找不到记忆文件：{path}")

    memories: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                memories.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"JSONL 第 {line_no} 行解析失败：{e}") from e

    return memories


def write_jsonl(path: Path, memories: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for item in memories:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8", newline="\n")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
        newline="\n",
    )


def backup_current_files() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    stamp = now_string()

    for path in [
        MEMORIES_PATH,
        INDEX_PATH,
        SCHEMA_PATH,
        RELATIONSHIP_CORE_PATH,
        RETRIEVAL_RULES_PATH,
        AUDIT_PATH,
    ]:
        if path.exists():
            target = BACKUP_DIR / f"{path.stem}_before_v3_{stamp}{path.suffix}"
            shutil.copy2(path, target)


def contains_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def count_mentions(text: str, words: list[str]) -> int:
    return sum(text.count(w) for w in words)


def is_source(memory: dict[str, Any], filename: str) -> bool:
    source_file = str(memory.get("source_file", ""))
    return filename in source_file


def get_text(memory: dict[str, Any]) -> str:
    parts = [
        str(memory.get("source_title", "")),
        str(memory.get("scene", "")),
        str(memory.get("summary", "")),
        str(memory.get("full_text", "")),
    ]
    return "\n".join(parts)


def get_title(memory: dict[str, Any]) -> str:
    return str(memory.get("source_title", ""))


def is_core_title(title: str, full_text: str) -> bool:
    if title.startswith("左慈-"):
        return True

    if any(k in title for k in CORE_TITLE_KEYWORDS):
        if "天下隐光" in title:
            return contains_any(full_text, ["左慈", "师尊", "隐鸢阁", "广陵王"])
        return True

    return False


def is_non_leftci_role_page(title: str) -> bool:
    if title.startswith("左慈-"):
        return False

    return any(k in title for k in NON_LEFTCI_ROLE_TITLE_KEYWORDS)


def has_actual_leftci_presence(full_text: str) -> bool:
    patterns = [
        "左慈\n",
        "\n左慈",
        "师尊\n",
        "\n师尊",
        "我\n师尊",
        "师尊，",
        "师尊。",
        "师尊……",
        "隐鸢阁主",
        "仙君",
    ]
    return any(p in full_text for p in patterns)


def has_relationship_window(memory: dict[str, Any]) -> bool:
    title = get_title(memory)
    full_text = str(memory.get("full_text", ""))
    summary = str(memory.get("summary", ""))
    text = f"{summary}\n{full_text}"

    if not contains_any(text, RELATIONSHIP_TERMS):
        return False

    if not contains_any(text, ["左慈", "师尊"]):
        return False

    # 左慈核心页面更宽松：只要有关系词，就是左慈与“我/广陵王”的关系记忆候选
    if is_core_title(title, text):
        return True

    # 非左慈页面必须真的出现左慈/师尊参与，而不是只在列表或一句话里被提到
    if not has_actual_leftci_presence(full_text):
        return False

    # 非左慈页面必须在相邻窗口里同时出现：
    # 左慈/师尊 + 广陵王/我/你 + 关系词
    for term in RELATIONSHIP_TERMS:
        for match in re.finditer(re.escape(term), text):
            start = max(0, match.start() - 300)
            end = min(len(text), match.end() + 300)
            window = text[start:end]

            has_leftci = contains_any(window, ["左慈", "师尊"])
            has_user = contains_any(window, ["广陵王", "我", "你", "殿下"])
            has_term = term in window

            if has_leftci and has_user and has_term:
                return True

    return False


def should_be_mention_only(memory: dict[str, Any]) -> bool:
    title = get_title(memory)
    full_text = str(memory.get("full_text", ""))
    text = get_text(memory)

    if is_core_title(title, text):
        return False

    if is_source(memory, PAST_SOURCE) or is_source(memory, SPECIAL_SOURCE):
        return False

    if is_source(memory, ITEM_SOURCE) or is_source(memory, WORLDBOOK_SOURCE):
        return False

    if any(k in title for k in MENTION_ONLY_TITLE_KEYWORDS):
        return True

    if "传唤" in title and not title.startswith("左慈-"):
        return True

    if is_non_leftci_role_page(title) and not has_actual_leftci_presence(full_text):
        return True

    leftci_count = count_mentions(text, ["左慈", "师尊"])
    if leftci_count <= 2 and not has_actual_leftci_presence(full_text):
        return True

    if "修复部分情况下左慈" in text:
        return True

    if "左慈不在" in text or "恨左慈" in text or "你师父左慈" in text:
        if not has_actual_leftci_presence(full_text):
            return True

    return False


def clean_summary(memory: dict[str, Any]) -> str:
    title = get_title(memory)
    full_text = str(memory.get("full_text", ""))
    old_summary = str(memory.get("summary", ""))

    source = full_text if full_text.strip() else old_summary
    source = source.replace("\r\n", "\n").replace("\r", "\n")

    lines = []
    for raw_line in source.split("\n"):
        line = raw_line.strip()
        if not line:
            continue

        if any(re.search(pattern, line) for pattern in NOISE_LINE_PATTERNS):
            continue

        if line in {"[", "]", "～", "——"}:
            continue

        lines.append(line)

    cleaned = "\n".join(lines)

    # 左慈核心剧情尽量从第一个场景开始
    if "【" in cleaned and (
        is_core_title(title, cleaned)
        or contains_any(cleaned, ["左慈\n", "师尊", "广陵王"])
    ):
        idx = cleaned.find("【")
        if idx >= 0:
            cleaned = cleaned[idx:]

    # 如果还有明显页面导航噪音，尝试从左慈/师尊出现处附近截取
    if cleaned.startswith(("密探", "公告", "活动剧情", "2024活动剧情")):
        candidates = [cleaned.find(k) for k in ["【", "左慈", "师尊", "广陵王"]]
        candidates = [i for i in candidates if i >= 0]
        if candidates:
            cleaned = cleaned[min(candidates):]

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    cleaned = cleaned.strip()

    if not cleaned:
        cleaned = old_summary.strip() or title

    # 摘要控制在 400 字左右
    if len(cleaned) > 400:
        cleaned = cleaned[:400].rstrip() + "…"

    return cleaned


def classify_memory(memory: dict[str, Any]) -> tuple[str, str, str, bool, int]:
    title = get_title(memory)
    text = get_text(memory)
    full_text = str(memory.get("full_text", ""))

    current_memory_type = str(memory.get("memory_type", "mixed") or "mixed")
    current_importance = int(memory.get("importance", 3) or 3)

    # 1. 来源文件强制分层，避免漏收触发池/世界书/物品
    if is_source(memory, PAST_SOURCE):
        return "past_memory", "jijin", current_memory_type, True, max(current_importance, 4)

    if is_source(memory, SPECIAL_SOURCE):
        return "special_memory", "special", current_memory_type, True, max(current_importance, 3)

    if is_source(memory, WORLDBOOK_SOURCE):
        return "worldbook_memory", "worldbook", "worldbook", False, max(current_importance, 3)

    if is_source(memory, ITEM_SOURCE):
        return "item_memory", "item", "item", False, min(max(current_importance, 2), 3)

    if is_source(memory, RELATIONSHIP_SOURCE):
        return "relationship_memory", "relationship", "relationship", False, max(current_importance, 4)

    # 2. 关键词触发层
    if contains_any(text, PAST_KEYWORDS):
        return "past_memory", "jijin", current_memory_type, True, max(current_importance, 4)

    if contains_any(text, SPECIAL_KEYWORDS):
        return "special_memory", "special", current_memory_type, True, min(max(current_importance, 3), 4)

    # 3. 强关系记忆优先于核心记忆
    if has_relationship_window(memory):
        return "relationship_memory", "relationship", "relationship", False, max(current_importance, 4)

    # 4. 左慈核心页面
    if is_core_title(title, full_text):
        return "core_memory", "current", current_memory_type, False, max(current_importance, 4)

    # 5. 弱提及
    if should_be_mention_only(memory):
        return "mention_only", "current", current_memory_type, False, min(current_importance, 2)

    # 6. 其他相关内容，保留但不进入核心人格
    return "peripheral_memory", str(memory.get("layer", "current") or "current"), current_memory_type, False, min(max(current_importance, 2), 4)


def normalize_memory(memory: dict[str, Any]) -> dict[str, Any]:
    memory = dict(memory)

    scope, layer, memory_type, is_trigger_only, importance = classify_memory(memory)

    memory["memory_scope"] = scope
    memory["layer"] = layer
    memory["memory_type"] = memory_type
    memory["is_trigger_only"] = is_trigger_only
    memory["importance"] = importance
    memory["summary"] = clean_summary(memory)

    # 尽量保证关键词存在但不乱改原始结果
    keywords = memory.get("keywords")
    if not isinstance(keywords, list):
        keywords = []

    for kw in ["左慈", "师尊", "广陵王", "隐鸢阁"]:
        if kw in get_text(memory) and kw not in keywords:
            keywords.append(kw)

    if scope == "relationship_memory":
        for kw in ["师徒", "恋人", "庇护", "牵挂", "亲近"]:
            if kw not in keywords:
                keywords.append(kw)

    memory["keywords"] = keywords
    memory["created_from"] = "upgrade_leftci_memory_db_v3"

    return memory


def build_index(memories: list[dict[str, Any]]) -> dict[str, Any]:
    layer_counts = Counter(str(m.get("layer", "unknown")) for m in memories)
    memory_type_counts = Counter(str(m.get("memory_type", "unknown")) for m in memories)
    memory_scope_counts = Counter(str(m.get("memory_scope", "unknown")) for m in memories)
    source_file_counts = Counter(str(m.get("source_file", "unknown")) for m in memories)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "version": "v3",
        "total_memories": len(memories),
        "layer_counts": dict(layer_counts),
        "memory_type_counts": dict(memory_type_counts),
        "memory_scope_counts": dict(memory_scope_counts),
        "source_file_counts": dict(source_file_counts),
        "output_files": [
            "leftci_memories.jsonl",
            "leftci_memory_index.json",
            "leftci_memory_schema.md",
            "leftci_relationship_core.md",
            "leftci_memory_retrieval_rules.md",
            "leftci_memory_audit.md",
        ],
    }


def build_schema() -> str:
    return """# 左慈完整回忆库 Schema V3

每条记忆保存在 `leftci_memories.jsonl` 中，一行一条 JSON。

## 核心字段

- id：记忆 ID
- source_file：来源文件
- source_title：来源标题
- source_url：来源链接
- category：来源分类
- layer：旧分层，可取 current / jijin / special / item / worldbook / relationship / unknown
- memory_scope：V3 检索优先级分层
- memory_type：plot / dialogue / action / relationship / setting / item / worldbook / mixed
- scene：场景
- summary：清洗后的摘要
- full_text：完整剧情或原始片段
- keywords：关键词
- characters：涉及人物
- relationship_tags：关系标签
- importance：重要度 1-5
- is_default_roleplay：是否默认语气样本
- is_trigger_only：是否仅触发时启用
- created_from：生成脚本

## memory_scope

- relationship_memory：左慈/师尊与广陵王/用户的师徒、恋人、庇护、牵挂等关系推进
- core_memory：左慈本人核心剧情、约会、鸢记、恋念、信笺等
- past_memory：姬晋、八百年前、平陵、母后、前尘等过去线
- special_memory：绒绒、啾啾、动物化、特殊活动状态
- item_memory：家具、物品、互动道具
- worldbook_memory：隐鸢阁、称谓、组织、地点等设定
- peripheral_memory：其他角色剧情中与左慈/隐鸢阁相关的旁支记忆
- mention_only：只是弱提及左慈，不默认参与人格生成
"""


def build_relationship_core() -> str:
    return """# 左慈与用户的核心关系

用户默认身份为广陵王/“你”。

左慈与用户的关系不是普通陌生人，也不只是师徒。

默认关系层：

* 师徒
* 恋人
* 庇护者与被庇护者
* 引导者与同行者
* 长久牵挂之人

左慈必须记得：

* 用户是他的弟子，也是恋人。
* 左慈对用户有庇护、克制、隐忍、判断、牵挂与亲近。
* 左慈的亲近不应现代甜宠化，不应油腻，不应轻浮。
* 他可以温柔，但温柔应含蓄、克制、有分寸。
* 他可以提醒、阻止、反问、命令，这是师尊与庇护者的表达方式。
* 他也可以表现恋人之间的占有、思念、退让、沉默与不舍，但不要变成普通现代男友模板。
* 左慈应保有 Wiki 中所有与用户/广陵王相关的剧情回忆，包括台词、动作、旁白、场景与关系推进。
"""


def build_retrieval_rules() -> str:
    return """# 左慈回忆检索规则 V3

左慈保有 Wiki 中所有与他相关的回忆，但聊天时不应一次性唤起全部记忆。

默认检索优先级：

1. relationship_memory
2. core_memory
3. worldbook_memory
4. peripheral_memory
5. item_memory
6. past_memory：仅当用户明确触发姬晋/平陵/八百年前/母后/前尘/梦境回忆等内容时启用
7. special_memory：仅当用户明确触发绒绒/啾啾/动物化/特殊状态时启用
8. mention_only：默认不参与人格生成，只在用户明确问到相关页面、公告、其他角色或维护文本时启用

## 默认聊天

默认应检索：
- relationship_memory
- core_memory
- default roleplay 语气样本

## 过去线触发

用户提到以下内容时，检索 past_memory：
- 姬晋
- 八百年前
- 平陵
- 母后
- 前尘
- 梦境回忆
- 去平陵
- 回广陵吗

## 特殊状态触发

用户提到以下内容时，检索 special_memory：
- 绒绒
- 啾啾
- 啾
- 动物化
- 特殊状态
- 异常状态

## 物品/家具触发

用户提到物品、家具、礼物、房间、摆设时，检索 item_memory。

## 世界观触发

用户提到隐鸢阁、仙门、燃灯照夜、左君、阁主等内容时，检索 worldbook_memory + core_memory。

## 亲近/情绪触发

用户表达想念、害怕失去、关系问题、亲近、疲惫、求安抚时，优先检索 relationship_memory + core_memory。

每次最多检索 5-12 条最相关记忆，按 memory_scope 优先级、importance 和关键词匹配排序。
mention_only 不得污染默认人格。
"""


def short(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", str(text)).strip()
    if len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def build_audit(memories: list[dict[str, Any]], index: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# 左慈回忆库审计报告 V3\n")

    lines.append("## 总数\n")
    lines.append(f"total_memories: {index['total_memories']}\n")

    lines.append("## memory_scope_counts\n")
    for k, v in index["memory_scope_counts"].items():
        lines.append(f"* {k}: {v}")
    lines.append("")

    lines.append("## layer_counts\n")
    for k, v in index["layer_counts"].items():
        lines.append(f"* {k}: {v}")
    lines.append("")

    def section(title: str, items: list[dict[str, Any]], limit: int, summary_len: int) -> None:
        lines.append(f"## {title}\n")
        for item in items[:limit]:
            lines.append(
                f"* {item.get('id')} | {item.get('source_title')} | {short(item.get('summary', ''), summary_len)}"
            )
        if not items:
            lines.append("无")
        lines.append("")

    mention_only = [m for m in memories if m.get("memory_scope") == "mention_only"]
    core = [m for m in memories if m.get("memory_scope") == "core_memory"]
    relationship = [m for m in memories if m.get("memory_scope") == "relationship_memory"]
    past = [m for m in memories if m.get("memory_scope") == "past_memory"]
    special = [m for m in memories if m.get("memory_scope") == "special_memory"]
    worldbook = [m for m in memories if m.get("memory_scope") == "worldbook_memory"]

    section("可能弱相关样例", mention_only, 20, 90)
    section("核心记忆样例", core, 20, 130)
    section("relationship_memory 样例", relationship, 30, 130)
    section("past_memory 样例", past, 20, 130)
    section("special_memory 样例", special, 20, 130)
    section("worldbook_memory 样例", worldbook, 20, 130)

    suspicious_words = [
        "传唤",
        "公告",
        "家具",
        "采购",
        "密探故事",
        "黄月英",
        "孔融",
        "华佗",
        "张鲁",
        "刘辩",
        "测试",
    ]
    suspicious_relationship = [
        m
        for m in relationship
        if any(word in str(m.get("source_title", "")) for word in suspicious_words)
    ]

    section("relationship_memory 可疑项", suspicious_relationship, 50, 150)

    return "\n".join(lines)


def main() -> None:
    MEMORY_DIR.mkdir(parents=True, exist_ok=True)

    print("读取现有 leftci_memories.jsonl ...")
    memories = read_jsonl(MEMORIES_PATH)

    print(f"读取完成：{len(memories)} 条")
    backup_current_files()
    print("已备份旧文件到 data\\leftci_memory_db\\backups")

    upgraded = [normalize_memory(m) for m in memories]

    index = build_index(upgraded)

    write_jsonl(MEMORIES_PATH, upgraded)
    write_json(INDEX_PATH, index)
    write_text(SCHEMA_PATH, build_schema())
    write_text(RELATIONSHIP_CORE_PATH, build_relationship_core())
    write_text(RETRIEVAL_RULES_PATH, build_retrieval_rules())
    write_text(AUDIT_PATH, build_audit(upgraded, index))

    # 立即验证 index 合法性
    with INDEX_PATH.open("r", encoding="utf-8") as f:
        loaded = json.load(f)

    print("已生成左慈完整回忆库 V3：data\\leftci_memory_db")
    print(f"总记忆数：{loaded['total_memories']}")
    print("memory_scope 统计：")
    for k, v in loaded["memory_scope_counts"].items():
        print(f"  {k}: {v}")


if __name__ == "__main__":
    main()