# -*- coding: utf-8 -*-
"""从 MediaWiki API 获取代号鸢 BWiki 主命名空间的所有普通页面标题。"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from config import API_URL, OUTPUT_DIR, REQUEST_DELAY_SECONDS, USER_AGENT


class AllPagesRequestError(RuntimeError):
    """抓取 allpages 时的自定义异常。"""

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
        "Referer": "https://wiki.biligame.com/yuan/",
    }


def request_allpages(params, max_retries=3):
    """请求 allpages 接口，并在失败时抛出自定义异常。"""
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
                raise AllPagesRequestError(
                    f"allpages 请求失败：{exc}",
                    status_code=status_code,
                    response_text_preview=response_text_preview,
                ) from exc
            print(f"第 {attempt} 次请求失败，准备重试：{exc}")
        except requests.RequestException as exc:
            if attempt == max_retries:
                raise AllPagesRequestError(f"allpages 请求失败：{exc}") from exc
            print(f"第 {attempt} 次请求失败，准备重试：{exc}")


def save_json(path, payload):
    """把内容保存为 JSON 文件。"""
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


def save_all_titles(output_file, checkpoint_file, titles, continuation=None):
    """保存标题列表和断点信息。"""
    payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_saved": len(titles),
        "namespace": 0,
        "source": "allpages",
        "titles": titles,
    }
    save_json(output_file, payload)

    checkpoint_payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_saved": len(titles),
        "namespace": 0,
        "continue": continuation,
    }
    save_json(checkpoint_file, checkpoint_payload)
    return payload


def load_existing_state(output_file, checkpoint_file):
    """从已有文件里恢复标题和 continue 参数。"""
    titles = []
    continuation = None

    if output_file.exists():
        with output_file.open("r", encoding="utf-8") as handle:
            try:
                data = json.load(handle)
                if isinstance(data, dict):
                    titles = data.get("titles", []) or []
            except json.JSONDecodeError:
                titles = []

    if checkpoint_file.exists():
        with checkpoint_file.open("r", encoding="utf-8") as handle:
            try:
                data = json.load(handle)
                continuation = data.get("continue")
            except json.JSONDecodeError:
                continuation = None

    return titles, continuation


def crawl_all_titles():
    """抓取所有主命名空间页面标题，并边抓边保存。"""
    os.makedirs("data", exist_ok=True)
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / "all_titles.json"
    checkpoint_file = output_dir / "all_titles_checkpoint.json"
    error_file = output_dir / "all_titles_error.json"

    titles, continuation = load_existing_state(output_file, checkpoint_file)
    error_info = None

    params = {
        "action": "query",
        "list": "allpages",
        "apnamespace": 0,
        "format": "json",
        "aplimit": "max",
    }

    try:
        while True:
            current_params = dict(params)
            if continuation:
                current_params.update(continuation)

            data = request_allpages(current_params)
            query = data.get("query", {})
            pages = query.get("allpages", [])
            if pages:
                for item in pages:
                    titles.append(
                        {
                            "pageid": item.get("pageid"),
                            "ns": item.get("ns"),
                            "title": item.get("title"),
                        }
                    )
                save_all_titles(output_file, checkpoint_file, titles, continuation=continuation)
                print(f"已保存标题数: {len(titles)}")

            if "continue" in data:
                continuation = data["continue"]
            else:
                break

    except AllPagesRequestError as exc:
        error_info = {
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "status_code": exc.status_code,
            "error_message": str(exc),
            "response_text_preview": exc.response_text_preview,
        }
        save_all_titles(output_file, checkpoint_file, titles, continuation=continuation)
        with error_file.open("w", encoding="utf-8") as handle:
            json.dump(error_info, handle, ensure_ascii=False, indent=2)
        print("遇到分页限制，已保存当前结果")
    except Exception as exc:
        error_info = {
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "status_code": None,
            "error_message": str(exc),
            "response_text_preview": "",
        }
        save_all_titles(output_file, checkpoint_file, titles, continuation=continuation)
        with error_file.open("w", encoding="utf-8") as handle:
            json.dump(error_info, handle, ensure_ascii=False, indent=2)
        print("抓取过程出现异常，已保存当前结果")

    final_payload = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "total_saved": len(titles),
        "namespace": 0,
        "source": "allpages",
        "titles": titles,
    }
    save_json(output_file, final_payload)

    print(f"已保存标题数: {len(titles)}")
    print(f"all_titles.json 路径: {output_file}")
    print(f"checkpoint 路径: {checkpoint_file}")
    if error_file.exists():
        print(f"error 文件路径: {error_file}")
    return final_payload


if __name__ == "__main__":
    crawl_all_titles()
