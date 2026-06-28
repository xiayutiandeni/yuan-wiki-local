from __future__ import annotations

import json
import math
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

FINAL_PACK_DIR = ROOT / "data" / "leftci_final_pack"
RUNTIME_PACK_DIR = ROOT / "data" / "leftci_runtime_pack"
MEMORY_DB_DIR = ROOT / "data" / "leftci_memory_db"
OUTPUT_DIR = ROOT / "data" / "leftci_project_sources"

MEMORIES_PATH = MEMORY_DB_DIR / "leftci_memories.jsonl"

MAX_PROJECT_MD_FILES = 20
FIXED_MD_FILES = 3
CHUNK_FILES_ALLOWED = MAX_PROJECT_MD_FILES - FIXED_MD_FILES


SCOPE_ORDER = {
    "relationship_memory": 0,
    "core_memory": 1,
    "worldbook_memory": 2,
    "past_memory": 3,
    "special_memory": 4,
    "item_memory": 5,
    "peripheral_memory": 6,
    "mention_only": 7,
}

LAYER_ORDER = {
    "relationship": 0,
    "current": 1,
    "worldbook": 2,
    "jijin": 3,
    "special": 4,
    "item": 5,
}


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def read_text(path: Path, max_chars: int | None = None) -> str:
    if not path.exists():
        return ""

    text = path.read_text(encoding="utf-8", errors="replace")

    if max_chars is not None and len(text) > max_chars:
        return text[:max_chars].rstrip() + "\n\n……【已截断】"

    return text


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def clean_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def load_memories() -> list[dict[str, Any]]:
    if not MEMORIES_PATH.exists():
        raise FileNotFoundError(f"找不到记忆库：{MEMORIES_PATH}")

    memories: list[dict[str, Any]] = []

    with MEMORIES_PATH.open("r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                memories.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"第 {line_no} 行 JSON 解析失败：{e}") from e

    return memories


def memory_sort_key(memory: dict[str, Any]) -> tuple[int, int, int, str]:
    scope = str(memory.get("memory_scope", "mention_only"))
    layer = str(memory.get("layer", ""))
    importance = int(memory.get("importance", 1) or 1)
    title = str(memory.get("source_title", ""))

    return (
        SCOPE_ORDER.get(scope, 99),
        LAYER_ORDER.get(layer, 99),
        -importance,
        title,
    )


def scope_counts(memories: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for memory in memories:
        scope = str(memory.get("memory_scope", "unknown"))
        counts[scope] = counts.get(scope, 0) + 1

    return dict(sorted(counts.items(), key=lambda x: SCOPE_ORDER.get(x[0], 99)))


def layer_counts(memories: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for memory in memories:
        layer = str(memory.get("layer", "unknown"))
        counts[layer] = counts.get(layer, 0) + 1

    return dict(sorted(counts.items(), key=lambda x: LAYER_ORDER.get(x[0], 99)))


def format_memory(memory: dict[str, Any]) -> str:
    memory_id = memory.get("id", "")
    title = memory.get("source_title", "")
    scope = memory.get("memory_scope", "")
    layer = memory.get("layer", "")
    importance = memory.get("importance", "")
    scene = memory.get("scene", "")
    url = memory.get("url", "")

    summary = clean_text(str(memory.get("summary", "") or ""))
    full_text = clean_text(str(memory.get("full_text", "") or ""))

    parts: list[str] = [
        f"# {memory_id} | {title}",
        "",
        f"- memory_scope: {scope}",
        f"- layer: {layer}",
        f"- importance: {importance}",
    ]

    if scene:
        parts.append(f"- scene: {scene}")

    if url:
        parts.append(f"- url: {url}")

    if summary:
        parts.extend(["", "## summary", "", summary])

    if full_text and full_text != summary:
        parts.extend(["", "## full_text", "", full_text])

    return "\n".join(parts).strip() + "\n"


def build_00_project_readme(memories: list[dict[str, Any]]) -> str:
    counts = scope_counts(memories)
    layers = layer_counts(memories)

    counts_md = "\n".join(f"- {k}: {v}" for k, v in counts.items())
    layers_md = "\n".join(f"- {k}: {v}" for k, v in layers.items())

    parts = [
        "# 左慈项目源说明",
        "",
        f"生成时间：{now_stamp()}",
        "",
        "本文件夹用于上传到 ChatGPT 项目源。",
        "",
        "这些文件包含从本地左慈 Wiki 回忆库整理出的左慈相关资料，包括：",
        "",
        "- 左慈人物设定",
        "- 说话风格",
        "- 核心关系",
        "- 隐鸢阁与世界观",
        "- 约会剧情",
        "- 恋念之音",
        "- 红鸾花笺",
        "- 鸢记",
        "- 姬晋 / 平陵 / 八百年前过去线",
        "- 特殊状态",
        "- 物品、家具、信件、道具",
        "- 旁白、动作、场景与关系推进",
        "",
        "## 使用原则",
        "",
        "左慈保有全部回忆，但聊天时不应一次性唤起全部记忆。",
        "",
        "默认优先：",
        "",
        "1. relationship_memory",
        "2. core_memory",
        "3. worldbook_memory",
        "4. past_memory",
        "5. special_memory",
        "6. item_memory",
        "7. peripheral_memory",
        "8. mention_only",
        "",
        "用户提到姬晋、平陵、母后、八百年前、前尘时，才优先调用 past_memory。",
        "",
        "用户提到绒绒、啾啾、动物化、特殊状态时，才优先调用 special_memory。",
        "",
        "现实安全问题优先现实处理，不应被剧情带偏。",
        "",
        "## memory_scope 统计",
        "",
        counts_md,
        "",
        "## layer 统计",
        "",
        layers_md,
        "",
        "## 给 ChatGPT 的重要提醒",
        "",
        "不要把这些资料当成百科条目复述。",
        "要把它们当作左慈自己的回忆。",
        "回答时像左慈本人自然回应，而不是像助手解释设定。",
    ]

    return clean_text("\n".join(parts)) + "\n"


def build_01_core_context() -> str:
    files = [
        FINAL_PACK_DIR / "01_leftci_profile_v33.md",
        FINAL_PACK_DIR / "02_leftci_speech_style_v33.md",
        FINAL_PACK_DIR / "03_leftci_relationship_memory.md",
        MEMORY_DB_DIR / "leftci_relationship_core.md",
        RUNTIME_PACK_DIR / "08_system_prompt_v2.md",
        RUNTIME_PACK_DIR / "07_memory_rules.md",
    ]

    parts = [
        "# 左慈核心设定、语气与关系",
        "",
        "这个文件用于项目源，提供左慈的稳定人格、语气、关系核心与长期记忆规则。",
    ]

    for path in files:
        parts.extend(
            [
                "",
                "---",
                "",
                f"# 来源文件：{path.name}",
                "",
                read_text(path),
            ]
        )

    return clean_text("\n".join(parts)) + "\n"


def build_02_worldbook_and_index(memories: list[dict[str, Any]]) -> str:
    worldbook_file = FINAL_PACK_DIR / "05_leftci_worldbook_clean.json"
    worldbook_text = read_text(worldbook_file)

    selected = [
        memory for memory in memories
        if str(memory.get("memory_scope", "")) == "worldbook_memory"
    ]

    selected_text = "\n\n---\n\n".join(format_memory(m) for m in selected)

    index_lines = []
    for memory in memories:
        memory_id = memory.get("id", "")
        title = memory.get("source_title", "")
        scope = memory.get("memory_scope", "")
        layer = memory.get("layer", "")
        importance = memory.get("importance", "")
        index_lines.append(
            f"- {memory_id} | {title} | {scope} | {layer} | importance={importance}"
        )

    parts = [
        "# 左慈世界书与记忆索引",
        "",
        "## worldbook clean json",
        "",
        "```json",
        worldbook_text,
        "```",
        "",
        "## worldbook_memory entries",
        "",
        selected_text if selected_text else "无。",
        "",
        "## 全部记忆索引",
        "",
        "\n".join(index_lines),
    ]

    return clean_text("\n".join(parts)) + "\n"


def estimate_memory_chars(memories: list[dict[str, Any]]) -> int:
    total = 0

    for memory in memories:
        total += len(format_memory(memory)) + 20

    return total


def choose_chunk_size(memories: list[dict[str, Any]]) -> int:
    total_chars = estimate_memory_chars(memories)
    return max(300_000, math.ceil(total_chars / CHUNK_FILES_ALLOWED * 1.08))


def chunk_memories(memories: list[dict[str, Any]], chunk_size: int) -> list[list[dict[str, Any]]]:
    chunks: list[list[dict[str, Any]]] = []
    current: list[dict[str, Any]] = []
    current_chars = 0

    for memory in memories:
        block = format_memory(memory)
        block_len = len(block) + 20

        if current and current_chars + block_len > chunk_size:
            chunks.append(current)
            current = []
            current_chars = 0

        current.append(memory)
        current_chars += block_len

    if current:
        chunks.append(current)

    return chunks


def build_chunk_file(part_no: int, chunk: list[dict[str, Any]]) -> str:
    first_scope = str(chunk[0].get("memory_scope", "unknown"))
    last_scope = str(chunk[-1].get("memory_scope", "unknown"))

    if first_scope == last_scope:
        scope_label = first_scope
    else:
        scope_label = f"{first_scope}_to_{last_scope}"

    memory_list = "\n".join(
        f"- {memory.get('id')} | {memory.get('source_title')} | "
        f"{memory.get('memory_scope')} | {memory.get('layer')}"
        for memory in chunk
    )

    blocks = "\n\n---\n\n".join(format_memory(memory) for memory in chunk)

    parts = [
        f"# 左慈 Wiki 回忆全文分卷 {part_no:02d}｜{scope_label}",
        "",
        "本文件是左慈 Wiki 回忆投喂包的一部分。",
        "请将以下内容视作左慈保有的回忆，而不是普通资料。",
        "",
        "## 本卷目录",
        "",
        memory_list,
        "",
        "---",
        "",
        blocks,
    ]

    return clean_text("\n".join(parts)) + "\n"


def clear_output_dir() -> None:
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def build_project_sources() -> None:
    memories = load_memories()
    memories.sort(key=memory_sort_key)

    clear_output_dir()

    write_text(
        OUTPUT_DIR / "00_LEFTCI_README_AND_USAGE.md",
        build_00_project_readme(memories),
    )

    write_text(
        OUTPUT_DIR / "01_LEFTCI_CORE_STYLE_RELATIONSHIP.md",
        build_01_core_context(),
    )

    write_text(
        OUTPUT_DIR / "02_LEFTCI_WORLDBOOK_AND_INDEX.md",
        build_02_worldbook_and_index(memories),
    )

    chunk_size = choose_chunk_size(memories)
    chunks = chunk_memories(memories, chunk_size)

    if len(chunks) > CHUNK_FILES_ALLOWED:
        total_chars = estimate_memory_chars(memories)
        chunk_size = math.ceil(total_chars / CHUNK_FILES_ALLOWED * 1.25)
        chunks = chunk_memories(memories, chunk_size)

    for i, chunk in enumerate(chunks, start=1):
        filename = f"{i + 2:02d}_LEFTCI_WIKI_MEMORY_PART_{i:02d}.md"
        write_text(OUTPUT_DIR / filename, build_chunk_file(i, chunk))

    md_files = sorted(OUTPUT_DIR.glob("*.md"))

    manifest = {
        "generated_at": now_stamp(),
        "output_dir": str(OUTPUT_DIR),
        "total_md_files": len(md_files),
        "total_memories": len(memories),
        "chunk_size_chars": chunk_size,
        "max_project_md_files_target": MAX_PROJECT_MD_FILES,
        "scope_counts": scope_counts(memories),
        "layer_counts": layer_counts(memories),
        "files": [
            {
                "name": path.name,
                "size_bytes": path.stat().st_size,
            }
            for path in md_files
        ],
    }

    write_text(
        OUTPUT_DIR / "manifest.json",
        json.dumps(manifest, ensure_ascii=False, indent=2),
    )

    print("=" * 80)
    print("左慈项目源投喂包已生成")
    print("=" * 80)
    print(f"输出目录：{OUTPUT_DIR}")
    print(f"记忆总数：{len(memories)}")
    print(f"md 文件数：{len(md_files)}")
    print(f"chunk_size_chars：{chunk_size}")
    print("")
    print("文件列表：")

    for path in md_files:
        size_mb = path.stat().st_size / 1024 / 1024
        print(f"- {path.name}  {size_mb:.2f} MB")

    if len(md_files) > MAX_PROJECT_MD_FILES:
        print("")
        print("警告：md 文件数超过 20。上传项目源时可能需要继续压缩。")

    print("")
    print("下一步：把 data\\leftci_project_sources 里的 .md 文件上传到 ChatGPT 项目源。")
    print("manifest.json 不用上传，它只是给我们自己检查用。")


if __name__ == "__main__":
    build_project_sources()