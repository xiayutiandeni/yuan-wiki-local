import json
import re
from pathlib import Path

titles_path = Path("data/all_titles.json")
json_dir = Path("data/all_pages_json")
index_paths = [
    Path("data/all_pages_index.json"),
    Path("data/index.json"),
]

def norm_title(s):
    if s is None:
        return ""
    s = str(s)
    s = s.replace("\r", "").replace("\n", "")
    s = re.sub(r"\s+", "", s)
    return s.strip()

def to_int(v):
    try:
        if v is None or v == "":
            return None
        return int(v)
    except Exception:
        return None

data = json.load(open(titles_path, encoding="utf-8"))
titles = data.get("titles", [])

saved_titles = set()
saved_pageids = set()
json_file_count = 0
bad_json_count = 0

# 1. 从所有已保存 JSON 文件里读取 pageid/title
for p in json_dir.glob("*.json"):
    json_file_count += 1

    # 从文件名开头提取 pageid，比如 1811_肝胆相照.json
    m = re.match(r"^(\d+)_", p.name)
    if m:
        saved_pageids.add(int(m.group(1)))

    try:
        item = json.load(open(p, encoding="utf-8"))
    except Exception:
        bad_json_count += 1
        continue

    for key in ["source_title", "title", "displaytitle"]:
        value = item.get(key)
        if value:
            saved_titles.add(norm_title(value))

    for key in ["pageid", "fallback_pageid"]:
        pageid = to_int(item.get(key))
        if pageid is not None:
            saved_pageids.add(pageid)

# 2. 从 index 文件里补充读取
for index_path in index_paths:
    if not index_path.exists() or index_path.stat().st_size == 0:
        continue
    try:
        idx = json.load(open(index_path, encoding="utf-8"))
    except Exception:
        continue

    if isinstance(idx, dict):
        candidates = []
        for value in idx.values():
            if isinstance(value, list):
                candidates.extend(value)
            elif isinstance(value, dict):
                candidates.append(value)
    elif isinstance(idx, list):
        candidates = idx
    else:
        candidates = []

    for item in candidates:
        if not isinstance(item, dict):
            continue

        for key in ["source_title", "title", "displaytitle"]:
            value = item.get(key)
            if value:
                saved_titles.add(norm_title(value))

        for key in ["pageid", "fallback_pageid"]:
            pageid = to_int(item.get(key))
            if pageid is not None:
                saved_pageids.add(pageid)

missing = []
for i, item in enumerate(titles):
    title = item.get("title")
    pageid = to_int(item.get("pageid"))

    title_ok = norm_title(title) in saved_titles
    pageid_ok = pageid is not None and pageid in saved_pageids

    if not title_ok and not pageid_ok:
        missing.append((i, pageid, title))

print("all_titles 总数:", len(titles))
print("本地 JSON 文件数:", json_file_count)
print("坏 JSON 文件数:", bad_json_count)
print("已保存标题数:", len(saved_titles))
print("已保存 pageid 数:", len(saved_pageids))
print("未保存数量:", len(missing))

if missing:
    print("第一个未保存:")
    print(missing[0])
    print("前30个未保存:")
    for row in missing[:30]:
        print(row)
else:
    print("全部标题都已保存。")
