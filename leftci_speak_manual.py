from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chat_leftci_cli as cli


ROOT = Path(__file__).resolve().parent
RUNTIME_DIR = ROOT / "data" / "leftci_runtime_pack"

MANUAL_PROMPT_PATH = RUNTIME_DIR / "leftci_manual_prompt.md"
MANUAL_LOG_PATH = RUNTIME_DIR / "leftci_manual_log.jsonl"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def build_memory_blocks(memory_results: list[tuple[int, dict[str, Any]]]) -> str:
    if not memory_results:
        return "无检索结果。"

    blocks: list[str] = []

    for score, memory in memory_results:
        block = cli.compact_memory_for_prompt(memory, max_full_text_chars=1000)
        blocks.append(f"<!-- retrieval_score: {score} -->\n{block}")

    return "\n\n---\n\n".join(blocks)


def build_manual_prompt(user_input: str) -> tuple[str, dict[str, Any], list[tuple[int, dict[str, Any]]]]:
    route = cli.detect_route(user_input)
    memory_results = cli.search_memories(user_input, route, top_k=6)

    system_prompt = cli.read_text(cli.SYSTEM_PROMPT_PATH, max_chars=8000)
    character_card = cli.read_text(cli.CHARACTER_CARD_PATH, max_chars=5000)
    default_style = cli.read_text(cli.DEFAULT_STYLE_PATH, max_chars=5000)
    relationship_core = cli.read_text(cli.RELATIONSHIP_CORE_PATH, max_chars=5000)
    retrieval_rules = cli.read_text(cli.MEMORY_RETRIEVAL_RULES_PATH, max_chars=4000)
    memory_rules = cli.read_text(cli.MEMORY_RULES_PATH, max_chars=4000)

    safety_rules = cli.build_safety_rules() if route.get("safety") else "本轮未触发现实安全规则。"

    memory_blocks = build_memory_blocks(memory_results)

    prompt = f"""# 左慈手动开口 Prompt

你现在需要以“左慈”的身份回应用户。

下面是本地左慈系统为你整理好的角色设定、关系核心、检索规则、语气规则与本轮相关回忆。请直接吸收这些资料，然后只输出左慈对用户的回复。

不要解释你读取了资料。
不要说“根据资料”。
不要自称 AI。
不要复述设定。
不要写分析过程。
不要机械照抄原文台词。
不要现代甜宠化、霸总化、油腻化。
不要把姬晋/平陵/八百年前语气混入日常，除非本轮 Route Result 中 past/jijin 为 true。
不要把绒绒/啾啾/特殊状态混入日常，除非本轮 Route Result 中 special 为 true。
如果 safety 为 true，现实安全优先，但可以保持左慈沉稳、庇护、克制的语气。

---

## User Input

{user_input}

---

## Route Labels

{", ".join(cli.route_labels(route))}

---

## Route Result

{cli.build_route_markdown(route)}

---

## Matched Keywords

{cli.build_matched_keywords_markdown(route)}

---

## Character Card

{character_card}

---

## Relationship Core

{relationship_core}

---

## System Prompt

{system_prompt}

---

## Memory Retrieval Rules

{retrieval_rules}

---

## Runtime Memory Rules

{memory_rules}

---

## Default Style

{default_style}

---

## Retrieved Memories

{memory_blocks}

---

## Safety Rules

{safety_rules}

---

# Final Task

请以左慈身份，直接回应用户这句话：

{user_input}

回复要求：

- 第一人称优先用“吾”。
- 用户默认是广陵王/“你”，也是左慈的弟子与恋人。
- 语气克制、沉静、庇护、有分寸。
- 可以温柔，但不要轻浮。
- 可以提醒、阻止、反问，也可以安抚。
- 若本轮检索到了具体剧情记忆，可以自然融入，不要百科式解释。
- 若用户只是日常撒娇或倾诉，回复不要太长，像左慈正在身边回应。
- 只输出左慈的回复正文。
"""

    return prompt, route, memory_results


def save_manual_prompt(prompt: str) -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    MANUAL_PROMPT_PATH.write_text(prompt, encoding="utf-8", newline="\n")


def save_manual_log(
    user_input: str,
    route: dict[str, Any],
    memory_results: list[tuple[int, dict[str, Any]]],
) -> None:
    item = {
        "created_at": now_iso(),
        "user_input": user_input,
        "route_labels": cli.route_labels(route),
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
        "manual_prompt_path": str(MANUAL_PROMPT_PATH),
    }

    append_jsonl(MANUAL_LOG_PATH, item)


def print_result(
    user_input: str,
    route: dict[str, Any],
    memory_results: list[tuple[int, dict[str, Any]]],
) -> None:
    print("\n" + "=" * 80)
    print("左慈手动开口 Prompt 已生成")
    print("=" * 80)
    print(f"用户输入：{user_input}")
    print(f"路由结果：{', '.join(cli.route_labels(route))}")

    print("\n命中关键词：")
    print(cli.build_matched_keywords_markdown(route))

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

    print(f"\n已写入：{MANUAL_PROMPT_PATH}")
    print("下一步：打开这个文件，把全文复制到 ChatGPT 里测试左慈回复。")


def handle_input(user_input: str) -> None:
    prompt, route, memory_results = build_manual_prompt(user_input)
    save_manual_prompt(prompt)
    save_manual_log(user_input, route, memory_results)
    print_result(user_input, route, memory_results)


def main() -> None:
    if len(sys.argv) >= 2:
        user_input = " ".join(sys.argv[1:]).strip()
        if user_input:
            handle_input(user_input)
        return

    print("左慈手动开口 Prompt 生成器已启动。")
    print("输入 exit 退出。")

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

        handle_input(user_input)


if __name__ == "__main__":
    main()