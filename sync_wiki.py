#!/usr/bin/env python3
"""
Mirror public Lunophira Miraheze pages into this GitHub repository.

Source of truth:
    https://lunophira.miraheze.org/wiki/

The script mirrors selected MediaWiki namespaces as raw wikitext and creates:
- index.json: machine-readable page index
- all-pages.md: all main-namespace articles concatenated for search/AI reading

It does not edit the Miraheze wiki.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API = "https://lunophira.miraheze.org/w/api.php"
WIKI_BASE = "https://lunophira.miraheze.org/wiki"

NAMESPACES = {
    0: "main",
    10: "template",
    14: "category",
    828: "module",
}

ROOT = Path(__file__).resolve().parent
WIKI_DIR = ROOT / "wiki"
INDEX_PATH = ROOT / "index.json"
ALL_PAGES_PATH = ROOT / "all-pages.md"

session = requests.Session()
retry = Retry(
    total=5,
    connect=5,
    read=5,
    status=5,
    backoff_factor=1.0,
    status_forcelist=(429, 500, 502, 503, 504),
    allowed_methods=frozenset(["GET"]),
)
session.mount("https://", HTTPAdapter(max_retries=retry))
session.headers.update(
    {
        "User-Agent": (
            "LunophiraMirror/1.0 "
            "(https://github.com/noachian258/lunophira-mirror; "
            "public archival mirror)"
        ),
        "Accept": "application/json,text/plain,*/*",
    }
)


def api_get(params: dict) -> dict:
    response = session.get(API, params=params, timeout=45)
    if response.ok:
        return response.json()

    # Miraheze currently returns 403 to some datacenter networks, including
    # GitHub-hosted runners. Fall back to Jina Reader as a read-only proxy.
    if response.status_code == 403:
        prepared = requests.Request("GET", API, params=params).prepare()
        proxy_url = "https://r.jina.ai/" + prepared.url
        proxy = session.get(
            proxy_url,
            timeout=90,
            headers={
                "Accept": "text/plain,application/json,*/*",
                "X-Return-Format": "text",
            },
        )
        proxy.raise_for_status()
        text = proxy.text.strip()

        # JSON endpoints are normally returned verbatim. Be tolerant of a
        # Markdown wrapper if the proxy adds one.
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            first = text.find("{")
            last = text.rfind("}")
            if first != -1 and last > first:
                return json.loads(text[first : last + 1])
            raise RuntimeError(
                "Miraheze returned HTTP 403 and the fallback reader did not "
                "return parseable MediaWiki API JSON."
            )

    response.raise_for_status()
    return response.json()


def all_titles(namespace: int) -> list[str]:
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "list": "allpages",
        "apnamespace": namespace,
        "aplimit": "max",
    }
    titles: list[str] = []

    while True:
        data = api_get(params)
        titles.extend(page["title"] for page in data["query"]["allpages"])

        continuation = data.get("continue")
        if not continuation:
            break
        params.update(continuation)

    return titles


def chunks(values: list[str], size: int = 50):
    for start in range(0, len(values), size):
        yield values[start : start + size]


def fetch_pages(titles: list[str]) -> list[dict]:
    results: list[dict] = []

    for batch in chunks(titles):
        params = {
            "action": "query",
            "format": "json",
            "formatversion": "2",
            "prop": "revisions",
            "titles": "|".join(batch),
            "rvprop": "ids|timestamp|content",
            "rvslots": "main",
        }
        data = api_get(params)

        for page in data["query"]["pages"]:
            if page.get("missing"):
                continue

            revisions = page.get("revisions", [])
            if not revisions:
                continue

            revision = revisions[0]
            slot = revision["slots"]["main"]
            results.append(
                {
                    "title": page["title"],
                    "pageid": page.get("pageid"),
                    "revid": revision.get("revid"),
                    "timestamp": revision["timestamp"],
                    "content": slot.get("content", ""),
                }
            )

        # Be polite to the origin even though requests are batched.
        time.sleep(0.05)

    return results


_TRANSLATION = str.maketrans(
    {
        "/": "／",
        "\\": "＼",
        ":": "：",
        "*": "＊",
        "?": "？",
        '"': "＂",
        "<": "＜",
        ">": "＞",
        "|": "｜",
    }
)


def safe_filename(title: str) -> str:
    name = title.translate(_TRANSLATION).strip().rstrip(".")
    if not name:
        name = "untitled"
    return name + ".wiki"


def source_url(title: str) -> str:
    return f"{WIKI_BASE}/{quote(title.replace(' ', '_'), safe='')}"


def reset_output() -> None:
    if WIKI_DIR.exists():
        shutil.rmtree(WIKI_DIR)

    for dirname in NAMESPACES.values():
        (WIKI_DIR / dirname).mkdir(parents=True, exist_ok=True)


def main() -> None:
    reset_output()
    index: list[dict] = []
    main_articles: list[dict] = []

    for namespace, dirname in NAMESPACES.items():
        titles = all_titles(namespace)
        print(f"Namespace {namespace} ({dirname}): {len(titles)} pages")

        pages = fetch_pages(titles)
        pages.sort(key=lambda p: p["title"])

        for page in pages:
            filename = safe_filename(page["title"])
            relative_path = Path("wiki") / dirname / filename
            absolute_path = ROOT / relative_path
            absolute_path.write_text(page["content"], encoding="utf-8")

            entry = {
                "title": page["title"],
                "namespace": namespace,
                "namespace_name": dirname,
                "pageid": page["pageid"],
                "revid": page["revid"],
                "timestamp": page["timestamp"],
                "file": relative_path.as_posix(),
                "source": source_url(page["title"]),
            }
            index.append(entry)

            if namespace == 0:
                main_articles.append({**entry, "content": page["content"]})

    index.sort(key=lambda p: (p["namespace"], p["title"]))
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    main_articles.sort(key=lambda p: p["title"])
    with ALL_PAGES_PATH.open("w", encoding="utf-8") as output:
        output.write("# 琉诺菲拉 Wiki 正文镜像\n\n")
        output.write(
            "> 自动同步自 [lunophira.miraheze.org]"
            "(https://lunophira.miraheze.org/wiki/)。"
            "Miraheze 原站是唯一正式版本；本文件仅用于搜索、备份和机器读取。\n\n"
        )
        output.write(f"当前汇总正文词条：**{len(main_articles)}**。\n")

        for page in main_articles:
            output.write("\n\n---\n\n")
            output.write(f"# {page['title']}\n\n")
            output.write(f"- 原页面：{page['source']}\n")
            output.write(f"- 原站版本时间：{page['timestamp']}\n\n")
            output.write(page["content"].rstrip())
            output.write("\n")

    print(
        f"Done: {len(index)} total pages; "
        f"{len(main_articles)} main-namespace articles."
    )


if __name__ == "__main__":
    main()
