from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
MEMORY_PATH = ROOT / "data" / "leftci_memory_db" / "leftci_memories.jsonl"


SCOPE_BASE_WEIGHT = {
    "relationship_memory": 80,
    "core_memory": 75,
    "worldbook_memory": 65,
    "peripheral_memory": 35,
    "item_memory": 30,
    "past_memory": 25,
    "special_memory": 25,
    "mention_only": -50,
}


PAST_TRIGGERS = [
    "姬晋", "八百年前", "平陵", "母后", "前尘", "过去身份",
    "梦境回忆", "回广陵吗", "去平陵", "广陵君，我们要去哪"
]
PAST_STRONG_TERMS = [
    "姬晋",
    "平陵",
    "母后",
    "八百年前",
    "前尘",
    "过去身份",
    "梦境回忆",
    "回广陵吗",
    "去平陵",
    "广陵君，我们要去哪",
]

SPECIAL_TRIGGERS = [
    "绒绒", "啾啾", "啾", "拟声", "动物化", "特殊状态", "异常状态"
]

ITEM_TRIGGERS = [
    "家具", "物品", "礼物", "摆设", "房间", "心纸居", "道具", "留音匣"
]

WORLDBOOK_TRIGGERS = [
    "隐鸢阁", "仙门", "左君", "阁主", "燃灯照夜", "仙君",
    "浮丘", "里八华", "广陵王", "左慈", "师尊"
]

RELATIONSHIP_TRIGGERS = [
    "师尊", "想你", "想见你", "想你了", "累", "难过", "害怕",
    "不想离开", "陪我", "抱", "亲", "吻", "恋人", "弟子",
    "逆徒", "保护", "庇护", "牵挂", "不舍"
]

LEFTCI_CORE_TITLE_MARKS = [
    "左慈-", "左慈/", "留音匣/左慈", "信笺匣/左慈",
    "夕情欢馀·左慈", "谷雨春风·左慈", "天下隐光"
]

LEFTCI_CLOSE_PAGE_MARKS = [
    "左慈-约会", "左慈-恋念", "左慈-红鸾花笺",
    "左慈-鸢记", "左慈-柬帖匣", "留音匣/左慈", "左慈-留音"
]

OTHER_CHARACTER_PREFIXES = [
    "刘辩-", "傅融-", "袁基-", "孙策-", "孔融-", "华佗-",
    "黄月英-", "张鲁-", "张邈-", "曹植-", "荀攸-"
]

GENERIC_TITLE_MARKS = [
    "活动玩法", "道具总览", "互动筛选器", "公告", "FB-",
    "家具采购单", "小头像汇总", "心纸君汇总", "游戏BGM",
    "测试手机", "沙盒"
]

KNOWN_TERMS = sorted(
    set(
        PAST_TRIGGERS
        + SPECIAL_TRIGGERS
        + ITEM_TRIGGERS
        + WORLDBOOK_TRIGGERS
        + RELATIONSHIP_TRIGGERS
        + ["房中术", "燃灯照夜", "隐鸢阁", "左慈", "师尊", "广陵王"]
    ),
    key=len,
    reverse=True,
)


def load_memories() -> list[dict[str, Any]]:
    memories: list[dict[str, Any]] = []
    with MEMORY_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                memories.append(json.loads(line))
    return memories


def has_any(text: str, words: list[str]) -> bool:
    return any(w in text for w in words)


def is_leftci_core_title(title: str) -> bool:
    return any(mark in title for mark in LEFTCI_CORE_TITLE_MARKS)


def is_leftci_close_page(title: str) -> bool:
    return any(mark in title for mark in LEFTCI_CLOSE_PAGE_MARKS)


def is_other_character_title(title: str) -> bool:
    return any(title.startswith(prefix) for prefix in OTHER_CHARACTER_PREFIXES)


def is_generic_title(title: str) -> bool:
    return any(mark in title for mark in GENERIC_TITLE_MARKS)


def extract_terms(query: str) -> list[str]:
    terms = []

    for term in KNOWN_TERMS:
        if term in query:
            terms.append(term)

    # 中文没有分词库，这里只保留比较可靠的连续关键词；
    # 不再把整句“隐鸢阁到底是什么地方”当成唯一 token。
    raw_tokens = re.findall(r"[A-Za-z0-9]{2,}", query)
    terms.extend(raw_tokens)

    # 去重，保持顺序
    seen = set()
    result = []
    for t in terms:
        if t not in seen:
            seen.add(t)
            result.append(t)

    return result


def detect_intent(query: str) -> set[str]:
    intent = {"default"}

    if has_any(query, PAST_TRIGGERS):
        intent.add("past")

    if has_any(query, SPECIAL_TRIGGERS):
        intent.add("special")

    if has_any(query, ITEM_TRIGGERS):
        intent.add("item")

    if has_any(query, WORLDBOOK_TRIGGERS):
        intent.add("worldbook")

    if has_any(query, RELATIONSHIP_TRIGGERS):
        intent.add("relationship")

    return intent


def score_memory(memory: dict[str, Any], query: str) -> int:
    title = str(memory.get("source_title", ""))
    summary = str(memory.get("summary", ""))
    full_text = str(memory.get("full_text", ""))
    keywords = memory.get("keywords", [])
    scope = str(memory.get("memory_scope", "mention_only"))
    importance = int(memory.get("importance", 1) or 1)

    terms = extract_terms(query)
    intent = detect_intent(query)

    searchable_short = f"{title}\n{summary}\n{' '.join(map(str, keywords))}"
    searchable_long = f"{searchable_short}\n{full_text[:6000]}"

    score = 0
    score += SCOPE_BASE_WEIGHT.get(scope, 0)
    score += importance * 8

    # 1. 精确标题优先
    if query == title:
        score += 260 if is_leftci_core_title(title) else 80

    if query in title:
        score += 180 if is_leftci_core_title(title) else 80

    # 2. 已知关键词命中
    for term in terms:
        if not term:
            continue

        if term == title:
            score += 180 if is_leftci_core_title(title) else 50

        if term in title:
            score += 100
            if is_leftci_core_title(title):
                score += 90

        if term in summary:
            score += 45

        if term in full_text[:6000]:
            score += 20

        if term in keywords:
            score += 50

    # 3. 左慈核心页优先
    if is_leftci_core_title(title):
        score += 110

    if is_leftci_close_page(title):
        score += 80

    # 4. 泛用页面降权
    if is_generic_title(title):
        score -= 120

    if "活动玩法" in title:
        score -= 180

    if title in {"房中术", "燃灯照夜"} and not is_leftci_core_title(title):
        score -= 80

    # 5. 其他男主页面默认降权，除非用户明确搜这个角色
    if is_other_character_title(title):
        if not any(name.replace("-", "") in query for name in OTHER_CHARACTER_PREFIXES):
            score -= 180

    # 6. worldbook 查询：先看设定，再看核心剧情
    if "worldbook" in intent:
        if scope == "worldbook_memory":
            score += 240
        if is_leftci_core_title(title):
            score += 70
        if scope == "relationship_memory" and not is_leftci_core_title(title):
            score -= 60

    # 7. 关系/情绪查询：优先亲密页，不要总是把大事件顶到第一
    if "relationship" in intent:
        if scope == "relationship_memory":
            score += 120
        if is_leftci_close_page(title):
            score += 160
        if has_any(searchable_short, ["想你", "不离开", "牵挂", "陪", "抱", "吻", "亲", "恋人", "逆徒"]):
            score += 80
        if "活动玩法" in title or is_generic_title(title):
            score -= 120

    # 8. past/special/item 触发
    if "past" in intent:
        past_hit_count = 0
        for term in PAST_STRONG_TERMS:
            if term in searchable_long:
                past_hit_count += 1

        query_past_terms = [term for term in PAST_STRONG_TERMS if term in query]

        if scope == "past_memory":
            score += 160

            # 用户明确问姬晋/平陵时，真正含这些词的记忆强力提前
            for term in query_past_terms:
                if term in title:
                    score += 260
                if term in summary:
                    score += 180
                if term in full_text[:6000]:
                    score += 120

            # past_memory 但完全不含本次查询的强触发词，降权
            if query_past_terms and not any(term in searchable_long for term in query_past_terms):
                score -= 260

            # 同时命中多个过去线关键词，说明更相关
            score += past_hit_count * 80

        elif scope in {"special_memory", "item_memory", "mention_only"}:
            score -= 160

    if "special" in intent:
        if scope == "special_memory":
            score += 260
        elif scope == "past_memory":
            score -= 120
    else:
        if scope == "special_memory":
            score -= 180

    if "item" in intent:
        if scope == "item_memory":
            score += 180

    # 9. 特定查询微调
    if "房中术" in query:
        if title.startswith("左慈-约会/房中术"):
            score += 260
        if title == "房中术":
            score -= 160

    if "燃灯照夜" in query:
        if title == "左慈-约会/燃灯照夜":
            score += 320
        elif title.startswith("左慈-") and "燃灯照夜" in title:
            score += 260
        elif title == "燃灯照夜" and scope == "worldbook_memory":
            score += 220
        elif "活动玩法" in title:
            score -= 220
        elif is_other_character_title(title):
            score -= 220

    if "隐鸢阁" in query:
        if title == "隐鸢阁" and scope == "worldbook_memory":
            score += 350
        if scope == "worldbook_memory":
            score += 180

    # 10. mention_only 默认不参与
    if scope == "mention_only":
        score -= 180

    return score


def search(query: str, top_k: int = 8) -> list[tuple[int, dict[str, Any]]]:
    memories = load_memories()
    scored: list[tuple[int, dict[str, Any]]] = []

    for memory in memories:
        score = score_memory(memory, query)
        if score > 0:
            scored.append((score, memory))

    scored.sort(key=lambda x: x[0], reverse=True)

    # 简单去重：同一标题完全重复时少拿一点
    results: list[tuple[int, dict[str, Any]]] = []
    seen_titles: dict[str, int] = {}

    for score, memory in scored:
        title = str(memory.get("source_title", ""))
        seen_titles[title] = seen_titles.get(title, 0) + 1

        if seen_titles[title] > 3:
            continue

        results.append((score, memory))

        if len(results) >= top_k:
            break

    return results


def print_result(query: str, results: list[tuple[int, dict[str, Any]]]) -> None:
    print("=" * 80)
    print(f"查询：{query}")
    print("=" * 80)

    if not results:
        print("没有找到相关记忆。")
        return

    for i, (score, memory) in enumerate(results, start=1):
        print(f"\n[{i}] score={score}")
        print(f"id: {memory.get('id')}")
        print(f"title: {memory.get('source_title')}")
        print(f"scope: {memory.get('memory_scope')}")
        print(f"layer: {memory.get('layer')}")
        print(f"importance: {memory.get('importance')}")
        print(f"summary: {str(memory.get('summary', ''))[:260]}...")


def main() -> None:
    if not MEMORY_PATH.exists():
        print(f"找不到记忆库：{MEMORY_PATH}")
        return

    if len(sys.argv) >= 2:
        query = " ".join(sys.argv[1:]).strip()
        results = search(query)
        print_result(query, results)
        return

    print("左慈记忆检索测试器 V2 已启动。输入 exit 退出。")
    while True:
        query = input("\n请输入查询：").strip()
        if query.lower() in {"exit", "quit", "q"}:
            break
        if not query:
            continue
        results = search(query)
        print_result(query, results)


if __name__ == "__main__":
    main()