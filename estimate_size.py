# -*- coding: utf-8 -*-
"""统计抓取结果占用空间，方便估算文本库体积。"""

import json
from pathlib import Path

from config import OUTPUT_DIR


def human_mb(size_bytes):
    return round(size_bytes / (1024 * 1024), 2)


def estimate_size():
    output_dir = Path(OUTPUT_DIR)
    pages_json_dir = output_dir / "pages_json"
    pages_html_dir = output_dir / "pages_html"

    json_files = list(pages_json_dir.glob("*.json")) if pages_json_dir.exists() else []
    html_files = list(pages_html_dir.glob("*.html")) if pages_html_dir.exists() else []

    json_size = sum(path.stat().st_size for path in json_files)
    html_size = sum(path.stat().st_size for path in html_files)
    total_size = json_size + html_size

    result = {
        "output_dir": str(output_dir),
        "json_files_size_mb": human_mb(json_size),
        "html_files_size_mb": human_mb(html_size),
        "total_size_mb": human_mb(total_size),
        "page_count": len(json_files),
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    estimate_size()
