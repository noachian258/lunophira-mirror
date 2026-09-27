#!/usr/bin/env python3
"""
Import a MediaWiki XML dump into the repository mirror.

Supported inputs:
- .xml
- .xml.gz
- .xml.bz2

Usage:
    python import_dump.py path/to/dump.xml.gz
"""

from __future__ import annotations

import bz2
import gzip
import json
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent
WIKI_DIR = ROOT / "wiki"
INDEX_PATH = ROOT / "index.json"
ALL_PAGES_PATH = ROOT / "all-pages.md"
WIKI_BASE = "https://lunophira.miraheze.org/wiki"

NAMESPACES = {
    0: "main",
    2: "user",
    4: "project",
    6: "file",
    8: "mediawiki",
    10: "template",
    14: "category",
    828: "module",
}

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
    return (name or "untitled") + ".wiki"


def source_url(title: str) -> str:
    return f"{WIKI_BASE}/{quote(title.replace(' ', '_'), safe='')}"


def open_dump(path: Path):
    name = path.name.lower()
    if name.endswith(".gz"):
        return gzip.open(path, "rb")
    if name.endswith(".bz2"):
        return bz2.open(path, "rb")
    return path.open("rb")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def child_text(parent: ET.Element, name: str, default: str = "") -> str:
    for child in parent:
        if local_name(child.tag) == name:
            return child.text or default
    return default


def last_revision(page: ET.Element):
    revisions = [c for c in page if local_name(c.tag) == "revision"]
    if not revisions:
        return None
    return revisions[-1]


def reset_output():
    if WIKI_DIR.exists():
        shutil.rmtree(WIKI_DIR)
    for dirname in NAMESPACES.values():
        (WIKI_DIR / dirname).mkdir(parents=True, exist_ok=True)


def main(path_str: str):
    path = Path(path_str)
    if not path.exists():
        raise SystemExit(f"Dump not found: {path}")

    reset_output()
    index = []
    main_articles = []

    with open_dump(path) as fh:
        context = ET.iterparse(fh, events=("end",))
        for _, elem in context:
            if local_name(elem.tag) != "page":
                continue

            title = child_text(elem, "title").strip()
            ns_text = child_text(elem, "ns", "0").strip()
            pageid_text = child_text(elem, "id", "").strip()

            try:
                namespace = int(ns_text)
            except ValueError:
                namespace = 0

            if namespace not in NAMESPACES:
                elem.clear()
                continue

            revision = last_revision(elem)
            if revision is None:
                elem.clear()
                continue

            revid = child_text(revision, "id", "").strip()
            timestamp = child_text(revision, "timestamp", "").strip()

            content = ""
            for child in revision:
                if local_name(child.tag) == "text":
                    content = child.text or ""
                    break

            dirname = NAMESPACES[namespace]
            rel = Path("wiki") / dirname / safe_filename(title)
            (ROOT / rel).write_text(content, encoding="utf-8")

            entry = {
                "title": title,
                "namespace": namespace,
                "namespace_name": dirname,
                "pageid": int(pageid_text) if pageid_text.isdigit() else None,
                "revid": int(revid) if revid.isdigit() else None,
                "timestamp": timestamp,
                "file": rel.as_posix(),
                "source": source_url(title),
            }
            index.append(entry)
            if namespace == 0:
                main_articles.append({**entry, "content": content})

            elem.clear()

    index.sort(key=lambda p: (p["namespace"], p["title"]))
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    main_articles.sort(key=lambda p: p["title"])
    with ALL_PAGES_PATH.open("w", encoding="utf-8") as output:
        output.write("# 琉诺菲拉 Wiki 正文镜像\n\n")
        output.write(
            "> 由 Miraheze MediaWiki XML dump 生成。"
            "原站是唯一正式版本；本文件仅用于搜索、备份和机器读取。\n\n"
        )
        output.write(f"当前汇总正文词条：**{len(main_articles)}**。\n")

        for page in main_articles:
            output.write("\n\n---\n\n")
            output.write(f"# {page['title']}\n\n")
            output.write(f"- 原页面：{page['source']}\n")
            if page["timestamp"]:
                output.write(f"- 原站版本时间：{page['timestamp']}\n")
            output.write("\n")
            output.write(page["content"].rstrip())
            output.write("\n")

    print(f"Imported {len(index)} pages; {len(main_articles)} main articles.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python import_dump.py <dump.xml|dump.xml.gz|dump.xml.bz2>")
    main(sys.argv[1])
