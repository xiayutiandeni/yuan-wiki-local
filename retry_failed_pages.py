# -*- coding: utf-8 -*-
"""重新尝试抓取 data/all_failed_pages.json 中失败的页面。"""

import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from config import API_URL, BASE_PAGE_URL, OUTPUT_DIR, REQUEST_DELAY_SECONDS, USER_AGENT


class PageRequestError(RuntimeError):
    def __init__(self, message, status_code=None, response_text_preview=""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text_preview = response_text_preview


def build_headers():
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": BASE_PAGE_URL,
    }


def request_json(params, max_retries=3):
    headers = build_headers()
    for attempt in range(1, max_retries + 1):
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            response = requests.get(API_URL, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            response_text_preview = ""
            if exc.response is not None:
                response_text_preview = exc.response.text[:200]
            if attempt == max_retries:
                raise PageRequestError(
                    f"页面请求失败：{exc}",
                    status_code=status_code,
                    response_text_preview=response_text_preview,
                ) from exc
            print(f"第 {attempt} 次页面请求失败，准备重试：{exc}")
        except requests.RequestException as exc:
            if attempt == max_retries:
                raise PageRequestError(f"页面请求失败：{exc}") from exc
            print(f"第 {attempt} 次页面请求失败，准备重试：{exc}")


def safe_filename(title, pageid):
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", title)
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    if not cleaned:
        cleaned = "page"
    return f"{pageid}_{cleaned}"


def extract_text(html_text):
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "lxml")
    return soup.get_text(separator="\n", strip=True)


def save_json(path, payload):
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def merge_failed_entries(failed_pages):
    merged = {}
    for entry in failed_pages:
        title = entry.get("title")
        if not title:
            continue
        merged[title] = entry
    return list(merged.values())


def load_json(path):
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as handle:
        try:
            return json.load(handle)
        except json.JSONDecodeError:
            return None


def normalize_title_for_matching(title):
    if title is None:
        return ""
    normalized = title.replace("\n", "").replace("\r", "").strip()
    normalized = re.sub(r"\s+", "", normalized)
    return normalized


def load_title_pageid_map(title_index_path):
    data = load_json(title_index_path) or {}
    titles = data.get("titles", []) if isinstance(data, dict) else data
    if not isinstance(titles, list):
        return {}, {}
    mapping = {}
    normalized_mapping = {}
    for item in titles:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        pageid = item.get("pageid")
        if title and pageid is not None:
            mapping[title] = pageid
            normalized_title = normalize_title_for_matching(title)
            if normalized_title:
                normalized_mapping[normalized_title] = pageid
    return mapping, normalized_mapping


def update_index(index_path, pages):
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pages": pages,
    }
    save_json(index_path, payload)
    return payload


def retry_failed_pages(limit=None):
    output_dir = Path(OUTPUT_DIR)
    pages_json_dir = output_dir / "all_pages_json"
    pages_html_dir = output_dir / "all_pages_html"
    pages_json_dir.mkdir(parents=True, exist_ok=True)
    pages_html_dir.mkdir(parents=True, exist_ok=True)

    failed_path = output_dir / "all_failed_pages.json"
    index_path = output_dir / "all_pages_index.json"

    failed_entries = load_json(failed_path) or []
    failed_entries = merge_failed_entries(failed_entries)

    title_index_path = output_dir / "all_titles.json"
    title_pageid_map, normalized_title_pageid_map = load_title_pageid_map(title_index_path)
    unresolved_failed_path = output_dir / "unresolved_failed_pages.json"
    existing_unresolved = merge_failed_entries(load_json(unresolved_failed_path) or [])

    retry_entries = merge_failed_entries(failed_entries + existing_unresolved)
    original_failure_count = len(retry_entries)

    index_data = load_json(index_path) or {}
    pages = index_data.get("pages", [])
    existing_titles = {page.get("source_title") for page in pages if page.get("source_title")}

    if not failed_entries:
        print("未发现 data/all_failed_pages.json 中的失败标题。")
        return

    total = 0
    success_count = 0
    skipped_count = 0
    unresolved_count = 0
    still_failed = []
    unresolved_failed = []
    session = requests.Session()

    for entry in retry_entries:
        if limit is not None and total >= limit:
            break
        total += 1

        title = entry.get("title")
        if not title:
            continue

        if title in existing_titles:
            skipped_count += 1
            print(f"已存在成功页面，跳过：{title}")
            continue

        pageid_source = entry.get("pageid")
        title_pageid = title_pageid_map.get(title)
        if title_pageid is None:
            normalized_title = normalize_title_for_matching(title)
            title_pageid = normalized_title_pageid_map.get(normalized_title)
        fallback_pageid = title_pageid or entry.get("fallback_pageid") or pageid_source
        try:
            params = {
                "action": "parse",
                "format": "json",
                "prop": "text|categories|links|externallinks|sections|displaytitle|iwlinks|properties",
            }
            use_pageid = title_pageid is not None
            request_mode = "pageid" if use_pageid else "page"
            if use_pageid:
                params["pageid"] = title_pageid
            else:
                params["page"] = title
            actual_request_url = session.prepare_request(requests.Request("GET", API_URL, params=params)).url
            print(f"title={title}")
            print(f"matched_pageid={title_pageid}")
            print(f"request_mode={request_mode}")
            print(f"request_url={actual_request_url}")
            data = request_json(params)
            if isinstance(data, dict) and "error" in data:
                error = data.get("error") or {}
                code = error.get("code")
                if code == "missingtitle" and title_pageid is None:
                    unresolved_entry = {
                        "title": title,
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                        "reason": "missingtitle_not_found_in_all_titles",
                        "status_code": None,
                        "error_message": str(error),
                        "response_text_preview": str(data)[:200],
                    }
                    unresolved_failed.append(unresolved_entry)
                    unresolved_count += 1
                    print(f"missingtitle 且无 pageid 匹配，移入 unresolved: {title}")
                    continue
                if title_pageid is not None:
                    unresolved_entry = {
                        "title": title,
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                        "reason": "pageid_request_failed",
                        "status_code": None,
                        "error_message": str(error),
                        "response_text_preview": str(data)[:200],
                    }
                    unresolved_failed.append(unresolved_entry)
                    unresolved_count += 1
                    print(f"pageid 请求失败，移入 unresolved: {title}")
                    continue
                raise PageRequestError(f"API 返回错误：{data.get('error')}", status_code=None, response_text_preview=str(data)[:200])
            if not isinstance(data, dict) or "parse" not in data:
                if title_pageid is not None:
                    unresolved_entry = {
                        "title": title,
                        "failed_at": datetime.now(timezone.utc).isoformat(),
                        "reason": "pageid_request_failed",
                        "status_code": None,
                        "error_message": "API 未返回 parse 字段",
                        "response_text_preview": "",
                    }
                    unresolved_failed.append(unresolved_entry)
                    unresolved_count += 1
                    print(f"pageid 请求未返回 parse，移入 unresolved: {title}")
                    continue
                raise PageRequestError("API 未返回 parse 字段")

            parse_data = data.get("parse", {}) or {}
            parse_pageid = parse_data.get("pageid")
            pageid_for_payload = parse_pageid if parse_pageid is not None else fallback_pageid
            missing_pageid = parse_pageid is None
            final_title = parse_data.get("title") or title

            html_text = parse_data.get("text", {}).get("*", "")
            text_content = extract_text(html_text)
            if not html_text and not text_content:
                raise RuntimeError("无法提取 HTML 或 文本")

            is_redirect = "redirectMsg" in html_text if html_text else False
            payload = {
                "source_title": title,
                "pageid": pageid_for_payload,
                "title": final_title,
                "displaytitle": parse_data.get("displaytitle", final_title),
                "url": f"{BASE_PAGE_URL}{quote(title.replace(' ', '_'), safe='/:_')}",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "categories": parse_data.get("categories", []),
                "links": parse_data.get("links", []),
                "externallinks": parse_data.get("externallinks", []),
                "sections": parse_data.get("sections", []),
                "properties": parse_data.get("properties", []),
                "html_file": safe_filename(title, fallback_pageid or 0) + ".html",
                "html": html_text,
                "text": text_content,
                "missing_pageid": bool(missing_pageid),
                "is_redirect": is_redirect,
                "possibly_broken_redirect": is_redirect,
            }

            filename_stem = safe_filename(title, fallback_pageid or 0)
            json_path = pages_json_dir / f"{filename_stem}.json"
            html_path = pages_html_dir / f"{filename_stem}.html"
            with json_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            if html_text:
                with html_path.open("w", encoding="utf-8") as handle:
                    handle.write(html_text)

            pages.append(
                {
                    "source_title": title,
                    "pageid": pageid_for_payload,
                    "title": payload["title"],
                    "json_file": json_path.name,
                    "html_file": html_path.name,
                    "url": payload["url"],
                }
            )
            existing_titles.add(title)
            success_count += 1
            print(f"重试成功：{title}")
        except Exception as exc:
            if title_pageid is not None:
                unresolved_entry = {
                    "title": title,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "reason": "pageid_request_failed",
                    "status_code": getattr(exc, "status_code", None),
                    "error_message": str(exc),
                    "response_text_preview": getattr(exc, "response_text_preview", ""),
                }
                unresolved_failed.append(unresolved_entry)
                unresolved_count += 1
                print(f"pageid 请求失败，移入 unresolved：{title} -> {exc}")
            else:
                still_failed.append({
                    "title": title,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "status_code": getattr(exc, "status_code", None),
                    "error_message": str(exc),
                    "response_text_preview": getattr(exc, "response_text_preview", ""),
                })
                print(f"重试失败：{title} -> {exc}")

    update_index(index_path, pages)
    save_json(failed_path, merge_failed_entries(still_failed))
    save_json(unresolved_failed_path, merge_failed_entries(unresolved_failed))

    print(f"原失败数: {original_failure_count}")
    print(f"已成功补回: {success_count}")
    print(f"移入 unresolved: {unresolved_count}")
    print(f"仍需重试: {len(still_failed)}")


if __name__ == "__main__":
    retry_failed_pages()
