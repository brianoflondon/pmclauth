#!/usr/bin/env python3
"""Fingerprint static assets and rewrite cache-busting references.

Run after changing styles.css, app.js, or manifest.json:

    python3 stamp_assets.py

If you replace image bytes in place without changing manifest.json, also bump
CACHE_VERSION via this script after a trivial manifest touch, or purge the
browser service worker caches. This script does not hash image binaries.

Updates:
  - index.html asset ?v= hashes
  - sw.js CACHE_VERSION + PRECACHE_URLS
  - app.js manifest.json?v= fetch URL
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent

ASSETS = {
    "styles.css": ROOT / "styles.css",
    "app.js": ROOT / "app.js",
    "manifest.json": ROOT / "manifest.json",
}


def short_hash(path: Path, length: int = 12) -> str:
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return digest[:length]


def combined_stamp(hashes: dict[str, str]) -> str:
    """Build CACHE_VERSION from all fingerprinted assets (not just manifest)."""
    material = "|".join(f"{name}:{hashes[name]}" for name in sorted(hashes))
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()[:12]
    day = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{day}-{digest}"


def main() -> None:
    hashes = {name: short_hash(path) for name, path in ASSETS.items()}

    index_path = ROOT / "index.html"
    index = index_path.read_text(encoding="utf-8")
    index = re.sub(
        r'href="styles\.css(?:\?v=[^"]*)?"',
        f'href="styles.css?v={hashes["styles.css"]}"',
        index,
    )
    index = re.sub(
        r'src="app\.js(?:\?v=[^"]*)?"',
        f'src="app.js?v={hashes["app.js"]}"',
        index,
    )
    index_path.write_text(index, encoding="utf-8")

    app_path = ROOT / "app.js"
    app = app_path.read_text(encoding="utf-8")
    app = re.sub(
        r'fetch\("manifest\.json(?:\?v=[^"]*)?"\)',
        f'fetch("manifest.json?v={hashes["manifest.json"]}")',
        app,
    )
    # Re-hash app.js after rewrite, then fix index again for app hash
    app_path.write_text(app, encoding="utf-8")
    hashes["app.js"] = short_hash(app_path)
    index = index_path.read_text(encoding="utf-8")
    index = re.sub(
        r'src="app\.js(?:\?v=[^"]*)?"',
        f'src="app.js?v={hashes["app.js"]}"',
        index,
    )
    index_path.write_text(index, encoding="utf-8")

    # Stamp after final hashes so CSS/JS-only changes also bump SW caches
    stamp = combined_stamp(hashes)

    sw_path = ROOT / "sw.js"
    sw = sw_path.read_text(encoding="utf-8")
    sw = re.sub(
        r'const CACHE_VERSION = "[^"]*";',
        f'const CACHE_VERSION = "{stamp}";',
        sw,
    )
    precache = f"""const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./styles.css?v={hashes["styles.css"]}",
  "./app.js?v={hashes["app.js"]}",
  "./manifest.json?v={hashes["manifest.json"]}",
  "./favicon.svg",
];"""
    sw = re.sub(
        r"const PRECACHE_URLS = \[[^\]]*?\];",
        precache,
        sw,
        count=1,
        flags=re.DOTALL,
    )
    sw_path.write_text(sw, encoding="utf-8")

    print("Asset fingerprints:")
    for name, value in hashes.items():
        print(f"  {name}: {value}")
    print(f"CACHE_VERSION: {stamp}")
    print("Updated index.html, app.js, sw.js")


if __name__ == "__main__":
    main()
