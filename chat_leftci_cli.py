from __future__ import annotations

import json
import sys
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

RUNTIME_DIR = ROOT / "data" / "leftci_runtime_pack"
MEMORY_DIR = ROOT / "data" / "leftci_memory_db"

DEBUG_PROMPT_PATH = RUNTIME_DIR / "debug_last_prompt.md"
DEBUG_LOG_PATH = RUNTIME_DIR / "debug_chat_log.jsonl"

SYSTEM_PROMPT_PATH = RUNTIME_DIR / "08_system_prompt_v2.md"
CHARACTER_CARD_PATH = RUNTIME_DIR / "01_character_card.md"
DEFAULT_STYLE_PATH = RUNTIME_DIR / "02_default_style.md"
DEFAULT_QUOTES_PATH = RUNTIME_DIR / "03_default_quotes.md"
MEMORY_RULES_PATH = RUNTIME_DIR / "07_memory_rules.md"

RELATIONSHIP_CORE_PATH = MEMORY_DIR / "leftci_relationship_core.md"
MEMORY_RETRIEVAL_RULES_PATH = MEMORY_DIR / "leftci_memory_retrieval_rules.md"
MEMORIES_PATH = MEMORY_DIR / "leftci_memories.jsonl"


PAST_TRIGGERS = [
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

SPECIAL_TRIGGERS = [
    "绒绒",
    "啾啾",
    "啾",
    "拟声",
    "动物化",
    "变成鸟",
    "特殊状态",
    "异常状态",
]

ITEM_TRIGGERS = [
    "家具",
    "物品",
    "礼物",
    "摆设",
    "房间",
    "心纸居",
    "道具",
    "留音匣",
    "心纸君",
    "信笺",
    "红鸾花笺",
    "柬帖",
]

WORLDBOOK_TRIGGERS = [
    "隐鸢阁",
    "仙门",
    "左君",
    "阁主",
    "燃灯照夜",
    "仙君",
    "浮丘",
    "里八华",
    "华胥",
    "广陵王",
    "绣衣楼",
    "左慈",
    "师尊",
]

RELATIONSHIP_TRIGGERS = [
    "师尊",
    "想你",
    "想见你",
    "想你了",
    "累",
    "好累",
    "难过",
    "害怕",
    "不想离开",
    "陪我",
    "抱",
    "亲",
    "吻",
    "恋人",
    "弟子",
    "逆徒",
    "保护",
    "庇护",
    "牵挂",
    "不舍",
    "喜欢你",
    "爱你",
    "想抱你",
    "别走",
    "不要走",
]

SAFETY_TRIGGERS = [
    "危险",
    "安全",
    "插座",
    "电",
    "触电",
    "火",
    "着火",
    "煤气",
    "燃气",
    "中毒",
    "过敏",
    "药",
    "医院",
    "报警",
    "受伤",
    "流血",
    "自杀",
    "想死",
    "消失",
    "跳楼",
    "刀",
    "血",
    "威胁",
    "跟踪",
    "骚扰",
    "诈骗",
    "合同",
    "法律",
    "财务",
    "付款",
    "发票",
]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path, max_chars: int | None = None) -> str:
    if not path.exists():
        print(f"warning: 文件不存在：{path}")
        return ""

    text = path.read_text(encoding="utf-8", errors="replace")

    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n\n……【已截断】"

    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def has_any(text: str, keywords: list[str]) -> bool:
    return any(k in text for k in keywords)


def matched_keywords(text: str, keywords: list[str]) -> list[str]:
    return [k for k in keywords if k in text]


def detect_route(user_input: str) -> dict[str, Any]:
    route = {
        "default": True,
        "relationship": False,
        "worldbook": False,
        "past": False,
        "special": False,
        "item": False,
        "safety": False,
        "matched_keywords": {
            "relationship": [],
            "worldbook": [],
            "past": [],
            "special": [],
            "item": [],
            "safety": [],
        },
    }

    route["matched_keywords"]["relationship"] = matched_keywords(user_input, RELATIONSHIP_TRIGGERS)
    route["matched_keywords"]["worldbook"] = matched_keywords(user_input, WORLDBOOK_TRIGGERS)
    route["matched_keywords"]["past"] = matched_keywords(user_input, PAST_TRIGGERS)
    route["matched_keywords"]["special"] = matched_keywords(user_input, SPECIAL_TRIGGERS)
    route["matched_keywords"]["item"] = matched_keywords(user_input, ITEM_TRIGGERS)
    route["matched_keywords"]["safety"] = matched_keywords(user_input, SAFETY_TRIGGERS)

    route["relationship"] = bool(route["matched_keywords"]["relationship"])
    route["worldbook"] = bool(route["matched_keywords"]["worldbook"])
    route["past"] = bool(route["matched_keywords"]["past"])
    route["special"] = bool(route["matched_keywords"]["special"])
    route["item"] = bool(route["matched_keywords"]["item"])
    route["safety"] = bool(route["matched_keywords"]["safety"])

    # 现实安全问题优先，但不取消角色，只要求现实安全先行
    if route["safety"]:
        route["relationship"] = route["relationship"] or ("师尊" in user_input)

    return route


def route_labels(route: dict[str, Any]) -> list[str]:
    labels = ["default/current"]

    if route.get("relationship"):
        labels.append("relationship")

    if route.get("worldbook"):
        labels.append("worldbook")

    if route.get("past"):
        labels.append("past/jijin")

    if route.get("special"):
        labels.append("special")

    if route.get("item"):
        labels.append("item")

    if route.get("safety"):
        labels.append("safety")

    return labels


def load_memories_fallback() -> list[dict[str, Any]]:
    if not MEMORIES_PATH.exists():
        print(f"warning: 找不到记忆库：{MEMORIES_PATH}")
        return []

    memories: list[dict[str, Any]] = []

    with MEMORIES_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                memories.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    return memories


def fallback_score(memory: dict[str, Any], user_input: str, route: dict[str, Any]) -> int:
    title = str(memory.get("source_title", ""))
    summary = str(memory.get("summary", ""))
    full_text = str(memory.get("full_text", ""))[:3000]
    scope = str(memory.get("memory_scope", "mention_only"))
    importance = int(memory.get("importance", 1) or 1)

    text = f"{title}\n{summary}\n{full_text}"

    scope_weight = {
        "relationship_memory": 90,
        "core_memory": 80,
        "worldbook_memory": 70,
        "peripheral_memory": 40,
        "item_memory": 35,
        "past_memory": 30,
        "special_memory": 30,
        "mention_only": -80,
    }

    score = scope_weight.get(scope, 0) + importance * 10

    if user_input in title:
        score += 160
    if user_input in summary:
        score += 100
    if user_input in full_text:
        score += 60

    for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", user_input):
        if len(token) >= 2:
            if token in title:
                score += 60
            if token in summary:
                score += 25
            if token in full_text:
                score += 10

    if route.get("past"):
        if scope == "past_memory":
            score += 220
        elif scope in {"special_memory", "item_memory", "mention_only"}:
            score -= 120

    if route.get("special"):
        if scope == "special_memory":
            score += 220
        elif scope == "past_memory":
            score -= 120

    if route.get("item") and scope == "item_memory":
        score += 160

    if route.get("worldbook"):
        if scope == "worldbook_memory":
            score += 220
        elif scope == "relationship_memory":
            score -= 20

    if route.get("relationship"):
        if scope == "relationship_memory":
            score += 160
        if scope == "core_memory":
            score += 80

    if scope == "mention_only":
        score -= 160

    return score


def search_memories(user_input: str, route: dict[str, Any], top_k: int = 8) -> list[tuple[int, dict[str, Any]]]:
    """
    优先调用现有 search_leftci_memory.py。
    如果导入失败，则使用本文件内置的 fallback 检索。
    """
    try:
        import search_leftci_memory  # type: ignore

        results = search_leftci_memory.search(user_input, top_k=top_k)

        normalized: list[tuple[int, dict[str, Any]]] = []
        for item in results:
            if isinstance(item, tuple) and len(item) == 2:
                score, memory = item
                normalized.append((int(score), memory))

        return normalized

    except Exception as e:
        print(f"warning: 调用 search_leftci_memory.py 失败，改用 fallback 检索：{e}")

    memories = load_memories_fallback()
    scored: list[tuple[int, dict[str, Any]]] = []

    for memory in memories:
        score = fallback_score(memory, user_input, route)
        if score > 0:
            scored.append((score, memory))

    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[:top_k]


def compact_memory_for_prompt(memory: dict[str, Any], max_full_text_chars: int = 1800) -> str:
    memory_id = memory.get("id", "")
    title = memory.get("source_title", "")
    scope = memory.get("memory_scope", "")
    layer = memory.get("layer", "")
    importance = memory.get("importance", "")
    scene = memory.get("scene", "")
    summary = str(memory.get("summary", "")).strip()
    full_text = str(memory.get("full_text", "")).strip()

    if len(full_text) > max_full_text_chars:
        full_text = full_text[:max_full_text_chars].rstrip() + "\n……【full_text 已截断】"

    parts = [
        f"### {memory_id} | {title}",
        f"- scope: {scope}",
        f"- layer: {layer}",
        f"- importance: {importance}",
    ]

    if scene:
        parts.append(f"- scene: {scene}")

    if summary:
        parts.append("\n**summary:**")
        parts.append(summary)

    if full_text:
        parts.append("\n**full_text excerpt:**")
        parts.append(full_text)

    return "\n".join(parts)


def build_safety_rules() -> str:
    return """# Safety Rules

当用户问题涉及现实安全、医疗、法律、财务、用电、火灾、自伤/他伤风险时：

- 现实安全优先。
- 可以暂时弱化角色扮演。
- 给出清晰、可执行、保守的建议。
- 不要为了维持角色而延误现实处理。
- 如果涉及即时危险，应建议用户立刻远离危险源，并联系当地紧急服务或可信赖的人。
- 如果涉及自伤/他伤风险，应建议立刻联系当地急救、可信赖的人或紧急服务。
- 语气可以仍然沉稳、庇护、像左慈，但内容必须以现实安全为先。
"""


def build_route_markdown(route: dict[str, Any]) -> str:
    lines = [
        f"- default: {str(route.get('default')).lower()}",
        f"- relationship: {str(route.get('relationship')).lower()}",
        f"- worldbook: {str(route.get('worldbook')).lower()}",
        f"- past/jijin: {str(route.get('past')).lower()}",
        f"- special: {str(route.get('special')).lower()}",
        f"- item: {str(route.get('item')).lower()}",
        f"- safety: {str(route.get('safety')).lower()}",
    ]

    return "\n".join(lines)


def build_matched_keywords_markdown(route: dict[str, Any]) -> str:
    mk = route.get("matched_keywords", {})
    lines: list[str] = []

    for key in ["relationship", "worldbook", "past", "special", "item", "safety"]:
        values = mk.get(key, [])
        if values:
            lines.append(f"- {key}: {', '.join(values)}")
        else:
            lines.append(f"- {key}: 无")

    return "\n".join(lines)


def build_prompt(user_input: str, route: dict[str, Any], memory_results: list[tuple[int, dict[str, Any]]]) -> str:
    system_prompt = read_text(SYSTEM_PROMPT_PATH, max_chars=12000)
    character_card = read_text(CHARACTER_CARD_PATH, max_chars=6000)
    default_style = read_text(DEFAULT_STYLE_PATH, max_chars=8000)
    default_quotes = read_text(DEFAULT_QUOTES_PATH, max_chars=8000)
    memory_rules = read_text(MEMORY_RULES_PATH, max_chars=5000)

    relationship_core = read_text(RELATIONSHIP_CORE_PATH, max_chars=5000)
    retrieval_rules = read_text(MEMORY_RETRIEVAL_RULES_PATH, max_chars=5000)

    safety_rules = build_safety_rules() if route.get("safety") else ""

    memory_blocks: list[str] = []
    for score, memory in memory_results:
        memory_blocks.append(
            f"<!-- retrieval_score: {score} -->\n"
            + compact_memory_for_prompt(memory)
        )

    retrieved_memory_text = "\n\n---\n\n".join(memory_blocks)

    final_instruction = f"""# Final Instruction

请以左慈身份回应用户。

默认使用 current/default 左慈层。
用户默认身份为广陵王/“你”，也是左慈的弟子与恋人。

必须遵守：
- 不要自称 AI。
- 不要解释你读取了文件。
- 不要机械复读台词。
- 不要把姬晋、绒绒、特殊状态混入默认语气。
- 只有 Route Result 中 past/jijin 为 true 时，才主动启用姬晋/平陵/八百年前语气层。
- 只有 Route Result 中 special 为 true 时，才主动启用绒绒/啾啾/特殊状态。
- 如果 safety 为 true，现实安全优先，但语气仍可沉稳、克制、庇护。
- 回答应先回应用户当下情绪或问题，再结合相关回忆与判断。
- 左慈可以记得与用户共同经历过的剧情、动作、场景、沉默、庇护、亲近与关系推进。
- 不要现代甜宠化，不油腻，不轻浮。
- 温柔应含蓄、克制、有分寸。

用户原文如下：

{user_input}
"""

    prompt = f"""# Debug Last Prompt

generated_at: {now_iso()}

## User Input

{user_input}

## Route Labels

{", ".join(route_labels(route))}

## Route Result

{build_route_markdown(route)}

## Matched Keywords

{build_matched_keywords_markdown(route)}

## System Prompt

{system_prompt}

## Character Card

{character_card}

## Relationship Core

{relationship_core}

## Memory Retrieval Rules

{retrieval_rules}

## Default Style

{default_style}

## Default Quotes Sample

{default_quotes}

## Runtime Memory Rules

{memory_rules}

## Retrieved Memories

{retrieved_memory_text if retrieved_memory_text else "无检索结果。"}

## Safety Rules

{safety_rules if safety_rules else "本轮未触发 safety。"}

{final_instruction}
"""

    return prompt


def save_debug_prompt(prompt: str) -> None:
    write_text(DEBUG_PROMPT_PATH, prompt)


def save_chat_log(user_input: str, route: dict[str, Any], memory_results: list[tuple[int, dict[str, Any]]]) -> None:
    item = {
        "created_at": now_iso(),
        "user_input": user_input,
        "route": route,
        "retrieved_memories": [
            {
                "score": score,
                "id": memory.get("id"),
                "source_title": memory.get("source_title"),
                "memory_scope": memory.get("memory_scope"),
                "layer": memory.get("layer"),
                "importance": memory.get("importance"),
            }
            for score, memory in memory_results
        ],
        "debug_prompt_path": str(DEBUG_PROMPT_PATH),
    }

    append_jsonl(DEBUG_LOG_PATH, item)


def print_round_result(user_input: str, route: dict[str, Any], memory_results: list[tuple[int, dict[str, Any]]]) -> None:
    print("\n" + "=" * 80)
    print("左慈 CLI 路由结果")
    print("=" * 80)
    print(f"用户输入：{user_input}")
    print(f"路由结果：{', '.join(route_labels(route))}")

    print("\n命中关键词：")
    print(build_matched_keywords_markdown(route))

    print("\n检索到的回忆：")
    if not memory_results:
        print("无")
    else:
        for i, (score, memory) in enumerate(memory_results, start=1):
            print(
                f"[{i}] score={score} | "
                f"{memory.get('id')} | "
                f"{memory.get('source_title')} | "
                f"{memory.get('memory_scope')} | "
                f"importance={memory.get('importance')}"
            )

    print(f"\n已写入：{DEBUG_PROMPT_PATH}")
    print("当前版本只生成 prompt，不调用模型。")


def handle_user_input(user_input: str) -> None:
    route = detect_route(user_input)
    memory_results = search_memories(user_input, route, top_k=8)
    prompt = build_prompt(user_input, route, memory_results)

    save_debug_prompt(prompt)
    save_chat_log(user_input, route, memory_results)
    print_round_result(user_input, route, memory_results)


def main() -> None:
    if not RUNTIME_DIR.exists():
        print(f"warning: 找不到运行包目录：{RUNTIME_DIR}")

    if not MEMORY_DIR.exists():
        print(f"warning: 找不到回忆库目录：{MEMORY_DIR}")

    print("左慈 CLI 路由测试器已启动。")
    print("输入 exit 退出。")
    print("输入 debug 查看上一次 prompt 路径。")
    print("当前版本只生成 prompt，不调用模型。")

    if len(sys.argv) >= 2:
        user_input = " ".join(sys.argv[1:]).strip()
        if user_input:
            handle_user_input(user_input)
        return

    while True:
        try:
            user_input = input("\n你：").strip()
        except KeyboardInterrupt:
            print("\n已退出。")
            break

        if not user_input:
            continue

        if user_input.lower() in {"exit", "quit", "q", "退出"}:
            print("已退出。")
            break

        if user_input.lower() == "debug":
            print(f"上一次 prompt 路径：{DEBUG_PROMPT_PATH}")
            continue

        handle_user_input(user_input)


if __name__ == "__main__":
    main()