# -*- coding: utf-8 -*-
"""根据全站标题索引抓取每个普通页面的正文、HTML 和元数据。"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

from config import API_URL, BASE_PAGE_URL, OUTPUT_DIR, REQUEST_DELAY_SECONDS, USER_AGENT


class PageRequestError(RuntimeError):
    """抓取单页时的自定义异常。"""

    def __init__(self, message, status_code=None, response_text_preview=""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text_preview = response_text_preview


def build_headers():
    """构造统一的 HTTP 请求头。"""
    return {
        "User-Agent": USER_AGENT,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Referer": BASE_PAGE_URL,
    }


def request_json(params, max_retries=3):
    """对 MediaWiki API 做带重试的请求。"""
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
    """把标题转成对 Windows 文件系统友好的文件名。"""
    cleaned = re.sub(r"[\\/:*?\"<>|]+", "_", title)
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("._")
    if not cleaned:
        cleaned = "page"
    return f"{pageid}_{cleaned}"


def extract_text(html_text):
    """从 HTML 中提取纯文本。"""
    if not html_text:
        return ""
    soup = BeautifulSoup(html_text, "lxml")
    return soup.get_text(separator="\n", strip=True)


def load_titles(input_file, start=None, limit=None):
    """从 all_titles.json 读取标题列表，并根据 start/limit 做切片。"""
    with input_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    titles = data.get("titles", []) if isinstance(data, dict) else []
    if not isinstance(titles, list):
        return [], 0, 0, 0, None

    if start is None:
        start = 0

    all_titles_len = len(titles)
    end = all_titles_len if limit is None else min(start + limit, all_titles_len)
    selected_titles = titles[start:end] if start < all_titles_len else []
    return selected_titles, all_titles_len, start, limit, end


def save_json(path, payload):
    """把内容保存为 JSON 文件。"""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def update_index(index_path, pages):
    """更新总索引文件。"""
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pages": pages,
    }
    save_json(index_path, payload)
    return payload


def merge_failed_entries(failed_pages):
    """按 title 去重失败条目，保留最后一次失败记录。"""
    merged = {}
    for entry in failed_pages:
        title = entry.get("title")
        if not title:
            continue
        merged[title] = entry
    return list(merged.values())


def update_failed_pages(failed_path, failed_pages):
    """更新失败页记录文件。"""
    failed_pages = merge_failed_entries(failed_pages)
    save_json(failed_path, failed_pages)


def crawl_all_pages(limit=None, resume=False, start=None):
    """按全站标题列表抓取每个页面正文。"""
    os.makedirs("data", exist_ok=True)
    output_dir = Path(OUTPUT_DIR)
    pages_json_dir = output_dir / "all_pages_json"
    pages_html_dir = output_dir / "all_pages_html"
    pages_json_dir.mkdir(parents=True, exist_ok=True)
    pages_html_dir.mkdir(parents=True, exist_ok=True)

    input_file = output_dir / "all_titles.json"
    if not input_file.exists():
        raise FileNotFoundError(f"找不到标题索引文件：{input_file}")

    index_path = output_dir / "all_pages_index.json"
    failed_path = output_dir / "all_failed_pages.json"
    current_failed_path = output_dir / "current_failed_pages.json"

    if index_path.exists() and resume:
        with index_path.open("r", encoding="utf-8") as handle:
            index_data = json.load(handle)
        existing_pages = index_data.get("pages", [])
    else:
        existing_pages = []

    if failed_path.exists():
        with failed_path.open("r", encoding="utf-8") as handle:
            try:
                failed_pages = json.load(handle)
            except json.JSONDecodeError:
                failed_pages = []
    else:
        failed_pages = []

    failed_pages = merge_failed_entries(failed_pages)
    current_failed_list = []
    save_json(current_failed_path, current_failed_list)

    selected_titles, all_titles_len, start, limit, end = load_titles(input_file, start=start, limit=limit)
    selected_titles_count = len(selected_titles)

    print(f"all_titles_len: {all_titles_len}")
    print(f"start: {start}")
    print(f"limit: {limit}")
    print(f"end: {end}")
    print(f"selected_titles_count: {selected_titles_count}")
    if selected_titles_count > 0:
        first_selected_title = selected_titles[0].get("title") if isinstance(selected_titles[0], dict) else None
        last_selected_title = selected_titles[-1].get("title") if isinstance(selected_titles[-1], dict) else None
    else:
        first_selected_title = None
        last_selected_title = None
    print(f"first_selected_title: {first_selected_title}")
    print(f"last_selected_title: {last_selected_title}")

    if selected_titles_count == 0:
        if start >= all_titles_len:
            print("原因: start >= all_titles_len")
        else:
            print("原因: selected_titles_count = 0")
        print(f"总标题数: 0")
        print(f"本次尝试数: 0")
        print(f"成功数: 0")
        print(f"跳过数: 0")
        print(f"本轮失败数: 0")
        return

    success_count = 0
    skipped_count = 0
    failed_count = 0
    attempt_count = 0
    pages = list(existing_pages)
    failed_list = list(failed_pages)
    total_titles = selected_titles_count

    for item in tqdm(selected_titles, desc="抓取全站页面", unit="页"):
        title = item.get("title")
        if not title:
            continue

        source_pageid = item.get("pageid")
        attempt_count += 1
        current_delay = REQUEST_DELAY_SECONDS
        try:
            # 先检查是否已经存在，避免重复抓取。使用来源 pageid 作为文件名的一部分优先项
            file_stem = safe_filename(title, source_pageid or 0)
            json_path = pages_json_dir / f"{file_stem}.json"
            html_path = pages_html_dir / f"{file_stem}.html"
            if json_path.exists() and html_path.exists():
                skipped_count += 1
                print(f"跳过已存在：{title}")
                continue

            params = {
                "action": "parse",
                "page": title,
                "prop": "text|categories|links|externallinks|sections|displaytitle|iwlinks|properties",
                "format": "json",
                "redirects": 1,
            }

            data = request_json(params)

            # 如果 API 返回 error，视为失败
            if isinstance(data, dict) and "error" in data:
                raise PageRequestError(f"API 返回错误：{data.get('error')}", status_code=None, response_text_preview=str(data)[:200])

            # 如果没有 parse 字段，视为失败
            if not isinstance(data, dict) or "parse" not in data:
                raise PageRequestError("API 未返回 parse 字段")

            parse_data = data.get("parse", {}) or {}
            parse_pageid = parse_data.get("pageid")
            missing_pageid = parse_pageid is None
            fallback_pageid = source_pageid if missing_pageid and source_pageid else None

            html_text = parse_data.get("text", {}).get("*", "")
            text_content = extract_text(html_text)

            # 如果既没有 html 内容，也无法提取到文本，则视作失败
            if not html_text and not text_content:
                raise RuntimeError("无法提取 HTML 或 文本")

            final_title = parse_data.get("title") or title

            payload = {
                "source_title": title,
                "pageid": parse_pageid,
                "fallback_pageid": fallback_pageid,
                "missing_pageid": bool(missing_pageid),
                "title": final_title,
                "displaytitle": parse_data.get("displaytitle", final_title),
                "url": f"{BASE_PAGE_URL}{quote(title.replace(' ', '_'), safe='/:_')}",
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "categories": parse_data.get("categories", []),
                "links": parse_data.get("links", []),
                "externallinks": parse_data.get("externallinks", []),
                "sections": parse_data.get("sections", []),
                "properties": parse_data.get("properties", []),
                "html_file": html_path.name,
                "html": html_text,
                "text": text_content,
            }

            with json_path.open("w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False, indent=2)
            if html_text:
                with html_path.open("w", encoding="utf-8") as handle:
                    handle.write(html_text)

            pages.append(
                {
                    "source_title": title,
                    "pageid": parse_pageid,
                    "fallback_pageid": fallback_pageid,
                    "title": payload["title"],
                    "json_file": json_path.name,
                    "html_file": html_path.name,
                    "url": payload["url"],
                }
            )
            success_count += 1
            update_index(index_path, pages)
            print(f"已保存页面：{title}")
        except PageRequestError as exc:
            failed_count += 1
            failure_entry = {
                "title": title,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "status_code": exc.status_code,
                "error_message": str(exc),
                "response_text_preview": getattr(exc, "response_text_preview", ""),
            }
            failed_list.append(failure_entry)
            current_failed_list.append(failure_entry)
            save_json(current_failed_path, current_failed_list)
            update_failed_pages(failed_path, failed_list)
            print(f"页面失败，已记录：{title}")

            # 遇到 567/403/429/5xx 时，等待更久，避免继续刷爆服务端。
            if exc.status_code in {567, 403, 429} or (exc.status_code is not None and 500 <= exc.status_code < 600):
                current_delay = REQUEST_DELAY_SECONDS * 4
            time.sleep(current_delay)
        except Exception as exc:
            failed_count += 1
            failure_entry = {
                "title": title,
                "failed_at": datetime.now(timezone.utc).isoformat(),
                "status_code": None,
                "error_message": str(exc),
                "response_text_preview": "",
            }
            failed_list.append(failure_entry)
            current_failed_list.append(failure_entry)
            save_json(current_failed_path, current_failed_list)
            update_failed_pages(failed_path, failed_list)
            print(f"页面抓取异常，已记录：{title}")

    total_json_size = sum(path.stat().st_size for path in pages_json_dir.glob("*.json")) if pages_json_dir.exists() else 0
    total_html_size = sum(path.stat().st_size for path in pages_html_dir.glob("*.html")) if pages_html_dir.exists() else 0

    print(f"总标题数: {total_titles}")
    print(f"本次尝试数: {attempt_count}")
    print(f"成功数: {success_count}")
    print(f"跳过数: {skipped_count}")
    print(f"本轮失败数: {failed_count}")
    print(f"JSON 文件夹大小: {total_json_size} bytes")
    print(f"HTML 文件夹大小: {total_html_size} bytes")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="抓取全站页面正文")
    parser.add_argument("--start", type=int, default=None, help="从第几个标题开始抓取（从0开始计数）")
    parser.add_argument("--limit", type=int, default=None, help="抓取多少条标题用于测试")
    parser.add_argument("--resume", action="store_true", help="继续上次没抓完的任务")
    args = parser.parse_args()
    crawl_all_pages(limit=args.limit, resume=args.resume, start=args.start)
