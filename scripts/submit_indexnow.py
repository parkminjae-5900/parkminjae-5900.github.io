#!/usr/bin/env python3
"""Submit only changed dahamsangjo.co.kr HTML URLs to IndexNow."""

from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
HOST = "www.dahamsangjo.co.kr"
BASE_URL = f"https://{HOST}/"
INDEXNOW_ENDPOINT = "https://api.indexnow.org/indexnow"
KEY = "9e01cf3d3deaa796b8c16a871bf6820f"
KEY_FILE = ROOT / f"{KEY}.txt"
SEED_FILE = ROOT / ".github" / "indexnow-seed.txt"
MAX_URLS = 10_000


def path_to_url(path: str) -> str | None:
    clean = pathlib.PurePosixPath(path.strip())
    if clean.is_absolute() or ".." in clean.parts or clean.suffix.lower() != ".html":
        return None
    value = clean.as_posix()
    if value == "index.html":
        return BASE_URL
    return urllib.parse.urljoin(BASE_URL, urllib.parse.quote(value, safe="/-._~"))


def validate_url(value: str) -> str:
    parsed = urllib.parse.urlparse(value.strip())
    if parsed.scheme != "https" or parsed.netloc != HOST or parsed.fragment:
        raise ValueError(f"URL must be an HTTPS URL on {HOST}: {value}")
    return urllib.parse.urlunparse(parsed)


def changed_lines(from_ref: str, to_ref: str) -> list[str]:
    command = [
        "git",
        "diff",
        "--name-status",
        "--find-renames",
        from_ref,
        to_ref,
        "--",
        "*.html",
        "**/*.html",
        str(SEED_FILE.relative_to(ROOT)),
    ]
    result = subprocess.run(command, cwd=ROOT, check=True, text=True, capture_output=True)
    return [line for line in result.stdout.splitlines() if line.strip()]


def collect_urls(lines: list[str]) -> list[str]:
    urls: set[str] = set()
    seed_changed = False

    for line in lines:
        parts = line.split("\t")
        status = parts[0]
        paths = parts[1:]
        if status.startswith("R") or status.startswith("C"):
            selected = paths[:2]
        else:
            selected = paths[:1]
        for path in selected:
            if path == str(SEED_FILE.relative_to(ROOT)):
                seed_changed = True
                continue
            url = path_to_url(path)
            if url:
                urls.add(validate_url(url))

    if seed_changed:
        for raw in SEED_FILE.read_text(encoding="utf-8").splitlines():
            value = raw.strip()
            if value and not value.startswith("#"):
                urls.add(validate_url(value))

    ordered = sorted(urls)
    if len(ordered) > MAX_URLS:
        raise ValueError(f"IndexNow batch exceeds {MAX_URLS} URLs")
    return ordered


def build_payload(urls: list[str]) -> dict[str, object]:
    if KEY_FILE.read_text(encoding="utf-8").strip() != KEY:
        raise ValueError("IndexNow key file content mismatch")
    return {
        "host": HOST,
        "key": KEY,
        "keyLocation": f"{BASE_URL}{KEY}.txt",
        "urlList": urls,
    }


def submit(payload: dict[str, object]) -> int:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        INDEXNOW_ENDPOINT,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    for attempt in range(2):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                if response.status not in (200, 202):
                    raise RuntimeError(f"unexpected IndexNow status {response.status}")
                return response.status
        except (urllib.error.URLError, TimeoutError):
            if attempt:
                raise
            time.sleep(2)
    raise RuntimeError("IndexNow submission failed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--from-ref", required=True)
    parser.add_argument("--to-ref", required=True)
    parser.add_argument("--submit", action="store_true")
    args = parser.parse_args()

    lines = changed_lines(args.from_ref, args.to_ref)
    urls = collect_urls(lines)
    payload = build_payload(urls)
    print(json.dumps({"urlCount": len(urls), "urls": urls}, ensure_ascii=False))
    if args.submit and urls:
        print(json.dumps({"status": submit(payload), "submitted": len(urls)}))


if __name__ == "__main__":
    main()
