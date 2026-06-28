# -*- coding: utf-8 -*-
"""使用 MediaWiki API 搜索公开页面，并把结果保存为 JSON。"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from tqdm import tqdm

from config import (
    API_URL,
    MAX_SEARCH_RESULTS,
    OUTPUT_DIR,
    REQUEST_DELAY_SECONDS,
    USER_AGENT,
)


class SearchRequestError(RuntimeError):
    """自定义异常，用来携带 HTTP 状态码、URL 和错误内容。"""

    def __init__(self, message, status_code=None, url=None, response_text_preview=None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url
        self.response_text_preview = response_text_preview


def request_json(params, max_retries=3):
    """带重试和睡眠的请求函数，适合新手理解的简单封装。"""
    headers = {"User-Agent": USER_AGENT}

    for attempt in range(1, max_retries + 1):
        time.sleep(REQUEST_DELAY_SECONDS)
        try:
            response = requests.get(API_URL, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as exc:
            status_code = getattr(exc.response, "status_code", None)
            url = getattr(getattr(exc.response, "request", None), "url", None) or API_URL
            response_text_preview = ""
            if exc.response is not None:
                response_text_preview = exc.response.text[:200].replace("\n", " ")
            if attempt == max_retries:
                raise SearchRequestError(
                    f"请求失败：{exc}",
                    status_code=status_code,
                    url=url,
                    response_text_preview=response_text_preview,
                ) from exc
            print(f"第 {attempt} 次请求失败，准备重试：{exc}")
        except requests.RequestException as exc:
            if attempt == max_retries:
                raise SearchRequestError(f"请求失败：{exc}", status_code=None, url=API_URL) from exc
            print(f"第 {attempt} 次请求失败，准备重试：{exc}")


def save_results(output_file, keyword, results, status="ok"):
    """把当前已经抓到的结果保存到 JSON 文件。"""
    payload = {
        "keyword": keyword,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_saved": len(results),
        "results": [
            {
                "title": item.get("title"),
                "pageid": item.get("pageid"),
                "snippet": item.get("snippet"),
                "timestamp": item.get("timestamp"),
                "size": item.get("size"),
                "wordcount": item.get("wordcount"),
            }
            for item in results
        ],
        "status": status,
    }

    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    return payload


def save_error(output_file, keyword, error_info):
    """把请求失败信息保存到单独的错误文件。"""
    payload = {
        "keyword": keyword,
        "failed_at": datetime.now(timezone.utc).isoformat(),
        "status_code": error_info.get("status_code"),
        "url": error_info.get("url"),
        "error_message": error_info.get("error_message"),
        "response_text_preview": error_info.get("response_text_preview"),
    }

    with output_file.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)

    return payload


def should_stop_for_pagination_error(status_code, message=""):
    """判断是否是服务器拒绝继续分页的情况。"""
    if status_code in {567, 403, 429}:
        return True
    if status_code is not None and 500 <= status_code < 600:
        return True
    if status_code is None and "567" in message:
        return True
    return False


def crawl_search(keyword="左慈"):
    """按关键词搜索页面，并处理 MediaWiki 的 continue 分页。"""
    os.makedirs("data", exist_ok=True)

    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / "search_leftci.json"
    error_file = output_dir / "search_error.json"

    params = {
        "action": "query",
        "list": "search",
        "srsearch": keyword,
        "format": "json",
        "srlimit": min(20, max(1, MAX_SEARCH_RESULTS)),
    }

    all_results = []
    continuation = None
    error_info = None
    status = "ok"

    try:
        with tqdm(desc="搜索页面", unit="页") as pbar:
            while True:
                if len(all_results) >= MAX_SEARCH_RESULTS:
                    break

                current_params = dict(params)
                if continuation:
                    current_params.update(continuation)

                data = request_json(current_params)
                query = data.get("query", {})
                search_results = query.get("search", [])

                remaining_slots = MAX_SEARCH_RESULTS - len(all_results)
                if remaining_slots <= 0:
                    break
                if len(search_results) > remaining_slots:
                    search_results = search_results[:remaining_slots]

                if search_results:
                    all_results.extend(search_results)
                    pbar.update(len(search_results))
                    save_results(output_file, keyword, all_results, status="ok")

                if "continue" in data and len(all_results) < MAX_SEARCH_RESULTS:
                    continuation = data["continue"]
                else:
                    break

        if not all_results:
            status = "empty_or_failed"
    except SearchRequestError as exc:
        error_info = {
            "status_code": exc.status_code,
            "url": exc.url,
            "error_message": str(exc),
            "response_text_preview": exc.response_text_preview,
        }
        status = "empty_or_failed"
    except Exception as exc:
        error_info = {
            "status_code": None,
            "url": API_URL,
            "error_message": str(exc),
            "response_text_preview": "",
        }
        status = "empty_or_failed"
    finally:
        payload = save_results(output_file, keyword, all_results, status=status)
        if error_info:
            save_error(error_file, keyword, error_info)
        print(f"data/search_leftci.json 已写入: {output_file.exists()}")
        print(f"保存数量 total_saved: {payload['total_saved']}")
        if error_info:
            print(f"data/search_error.json 已写入: {error_file.exists()}")
        else:
            print("data/search_error.json 已写入: False")

        return payload


if __name__ == "__main__":
    keyword = sys.argv[1] if len(sys.argv) > 1 else "左慈"
    crawl_search(keyword)
