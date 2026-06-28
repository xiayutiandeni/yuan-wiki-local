# -*- coding: utf-8 -*-
"""读取搜索结果中的页面标题，并抓取页面的 HTML、纯文本和元数据。"""

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
    """抓取单个页面时的自定义异常，用来携带状态码和响应预览。"""

    def __init__(self, message, status_code=None, response_text_preview=""):
        super().__init__(message)
        self.status_code = status_code
        self.response_text_preview = response_text_preview


def build_headers():
    """构造统一的 HTTP 请求头，适合 MediaWiki API 的公开请求。"""
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


def read_search_titles(search_file):
    """从搜索结果 JSON 中读取所有页面标题。"""
    with search_file.open("r", encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, dict):
        results = data.get("results", [])
    else:
        results = data

    titles = []
    for item in results:
        title = item.get("title") if isinstance(item, dict) else None
        if title:
            titles.append(title)

    return list(dict.fromkeys(titles))


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


def crawl_pages(search_file_name="search_leftci.json"):
    """抓取每个页面并保存成 JSON / HTML / 索引文件。"""
    os.makedirs("data", exist_ok=True)
    output_dir = Path(OUTPUT_DIR)
    pages_json_dir = output_dir / "pages_json"
    pages_html_dir = output_dir / "pages_html"
    pages_json_dir.mkdir(parents=True, exist_ok=True)
    pages_html_dir.mkdir(parents=True, exist_ok=True)

    search_file = output_dir / search_file_name
    if not search_file.exists():
        raise FileNotFoundError(f"找不到搜索结果文件：{search_file}")

    titles = read_search_titles(search_file)
    index = {"generated_at": datetime.now(timezone.utc).isoformat(), "pages": []}
    failed_pages = []
    success_count = 0
    skipped_count = 0
    failed_count = 0

    for title in tqdm(titles, desc="抓取页面", unit="页"):
        params = {
            "action": "parse",
            "page": title,
            "prop": "text|categories|links|externallinks|sections|displaytitle|iwlinks|properties",
            "format": "json",
            "redirects": 1,
        }

        file_stem = None
        try:
            parse_data = request_json(params)
            parse_data = parse_data.get("parse", {})
            pageid = parse_data.get("pageid")
            if pageid is None:
                raise RuntimeError("未返回 pageid")

            file_stem = safe_filename(title, pageid)
            json_path = pages_json_dir / f"{file_stem}.json"
            html_path = pages_html_dir / f"{file_stem}.html"

            if json_path.exists() and html_path.exists():
                skipped_count += 1
                print(f"跳过已存在的页面：{title}")
                continue

            html_text = parse_data.get("text", {}).get("*", "")
            text_content = extract_text(html_text)
            payload = {
                "source_title": title,
                "pageid": pageid,
                "title": parse_data.get("title", title),
                "displaytitle": parse_data.get("displaytitle", title),
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

            with html_path.open("w", encoding="utf-8") as handle:
                handle.write(html_text)

            index["pages"].append(
                {
                    "pageid": pageid,
                    "title": payload["title"],
                    "json_file": json_path.name,
                    "html_file": html_path.name,
                    "url": payload["url"],
                }
            )
            success_count += 1
            print(f"已保存页面：{title}")
        except PageRequestError as exc:
            failed_count += 1
            failed_pages.append(
                {
                    "title": title,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "status_code": exc.status_code,
                    "url": f"{API_URL}?action=parse&page={quote(title)}&prop=text|categories|links|externallinks|sections|displaytitle|iwlinks|properties&format=json&redirects=1",
                    "error_message": str(exc),
                    "response_text_preview": exc.response_text_preview,
                }
            )
            print(f"页面请求失败，已记录：{title}")
        except Exception as exc:
            failed_count += 1
            failed_pages.append(
                {
                    "title": title,
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "status_code": None,
                    "url": f"{API_URL}?action=parse&page={quote(title)}&prop=text|categories|links|externallinks|sections|displaytitle|iwlinks|properties&format=json&redirects=1",
                    "error_message": str(exc),
                    "response_text_preview": "",
                }
            )
            print(f"页面抓取失败，已记录：{title}")

    index_path = output_dir / "index.json"
    with index_path.open("w", encoding="utf-8") as handle:
        json.dump(index, handle, ensure_ascii=False, indent=2)

    failed_pages_path = output_dir / "failed_pages.json"
    if failed_pages:
        with failed_pages_path.open("w", encoding="utf-8") as handle:
            json.dump(failed_pages, handle, ensure_ascii=False, indent=2)
    else:
        with failed_pages_path.open("w", encoding="utf-8") as handle:
            json.dump([], handle, ensure_ascii=False, indent=2)

    print(f"总页面数: {len(titles)}")
    print(f"成功数量: {success_count}")
    print(f"跳过数量: {skipped_count}")
    print(f"失败数量: {failed_count}")
    print(f"JSON 文件夹路径: {pages_json_dir}")
    print(f"HTML 文件夹路径: {pages_html_dir}")
    print(f"failed_pages.json 路径: {failed_pages_path}")
    return index


if __name__ == "__main__":
    search_file_name = sys.argv[1] if len(sys.argv) > 1 else "search_leftci.json"
    crawl_pages(search_file_name)
