#!/usr/bin/env python3
"""
Download public-domain Orientalist paintings for the gallery site.

Sources prioritize Wikimedia Commons (original/high-res files via the MediaWiki API).
Images are saved under images/ and a manifest.json is written for the website.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent
IMAGES_DIR = ROOT / "images"
MANIFEST_PATH = ROOT / "manifest.json"
USER_AGENT = (
    "OrientalistGalleryBot/1.0 "
    "(educational; public-domain archive; contact: local)"
)
API_URL = "https://commons.wikimedia.org/w/api.php"
REQUEST_DELAY_SEC = 1.2  # be polite to Wikimedia (avoid 429)
MAX_RETRIES = 5
RETRY_BASE_SEC = 4.0
MAX_RETRY_AFTER_SEC = 90.0  # cap Retry-After so a single 429 cannot stall for minutes
IMAGE_MIMES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/gif",
    "image/webp",
    "image/tiff",
}

# ---------------------------------------------------------------------------
# Painting catalogue
# Each entry: id, artist, title, year, notes, commons_files (preferred order),
# optional extra_urls for non-Commons fallbacks.
# ---------------------------------------------------------------------------

PAINTINGS: list[dict] = [
    {
        "id": "ingres-odalisque-slave-1842",
        "artist": "Jean-Auguste-Dominique Ingres (with Jean-Paul Flandrin)",
        "title": "Odalisque with Slave",
        "year": "1839 / 1842",
        "location": "Walters Art Museum / Harvard Art Museums (Fogg)",
        "notes": "Related 1842 version and Fogg study; public domain.",
        "commons_files": [
            "Odalisque with slave, by Jean-Auguste-Dominique Ingres and Jean-Paul Flandrin.jpg",
            "Ingres Odalisque esclave Fogg Art.jpeg",
        ],
        "museum_url": "https://harvardartmuseums.org/art/299806",
    },
    {
        "id": "allan-slave-market-constantinople",
        "artist": "Sir William Allan",
        "title": "The Slave Market, Constantinople",
        "year": "1838",
        "location": "National Galleries of Scotland",
        "notes": "High-res from Art UK / National Galleries of Scotland.",
        "commons_files": [
            "William Allan (1782-1850) - The Slave Market, Constantinople - NG 2400 - National Galleries of Scotland.jpg",
        ],
        "museum_url": "https://www.nationalgalleries.org/art-and-artists/5659",
    },
    {
        "id": "roberts-slave-market-cairo",
        "artist": "David Roberts (lithograph by Louis Haghe)",
        "title": "A Slave Market in Cairo",
        "year": "c. 1839–1840s",
        "location": "Library of Congress / Wikimedia Commons",
        "notes": "PD lithograph after Roberts.",
        "commons_files": [
            "A slave market in Cairo-David Roberts.jpg",
        ],
        "museum_url": "https://www.loc.gov/pictures/resource/cph.3g04043",
    },
    {
        "id": "muller-slave-market-cairo",
        "artist": "William James Müller",
        "title": "Slave Market, Cairo",
        "year": "1841",
        "location": "Bury Art Museum / Guildhall (related versions)",
        "notes": "Wikimedia / Art UK versions exist.",
        "commons_files": [
            "William James Müller (1812-1845) - Slave Market, Cairo - 0085-1901 - Bury Art Museum.jpg",
        ],
        "museum_url": "https://artuk.org/discover/artworks/the-slave-market-at-cairo-egypt-51165",
    },
    {
        "id": "gerome-slave-market-1866",
        "artist": "Jean-Léon Gérôme",
        "title": "Slave Market (Le Marché d'esclaves)",
        "year": "1866",
        "location": "Clark Art Institute",
        "notes": "Multiple public-domain digital copies on Commons.",
        "commons_files": [
            "Jean-Léon Gérôme - Le Marché d'esclaves, 1866.jpg",
            "Gérôme, Le marché d'esclaves, 1866 (5613511883).jpg",
        ],
        "museum_url": "https://www.clarkart.edu",
    },
    {
        "id": "cermak-abduction-herzegovinian",
        "artist": "Jaroslav Čermák",
        "title": "The Abduction of a Herzegovinian Woman",
        "year": "1861",
        "location": "Dahesh Museum",
        "notes": "Also known as Herz.Woman in some catalogues.",
        "commons_files": [
            "Jaroslav Čermák - (Czech, 1830-1878) - The Abduction of a Herzegovenian Woman, 1861 - Oil on canvas, 98 1-2 x 75 in.jpg",
        ],
        "museum_url": "https://daheshmuseum.org/portfolio/jaroslav-cermakthe-abduction-of-a-herzegovenian-woman/",
    },
    {
        "id": "gyzis-slave-market",
        "artist": "Nikolaos Gyzis",
        "title": "The Slave Market",
        "year": "c. 1873–1875",
        "location": "National Gallery, Athens",
        "notes": "Public domain noted in secondary sources; try Commons then skip if missing.",
        "commons_files": [
            "Nikolaos Gyzis - The Slave Market.jpg",
            "Gyzis Slave Market.jpg",
            "Νικόλαος Γύζης - Το σκλαβοπάζαρο.jpg",
        ],
        "museum_url": "https://www.nationalgallery.gr/en/artwork/the-slave-market/",
        "search_terms": ["Gyzis Slave Market", "Gyzis σκλαβοπάζαρο"],
    },
    {
        "id": "vereshchagin-sale-child-slave",
        "artist": "Vasily Vereshchagin",
        "title": "The Sale of the Child Slave",
        "year": "1872",
        "location": "Tretyakov Gallery",
        "notes": "Also titled Selling a Child Slave.",
        "commons_files": [
            "Wassili Wassiljewitsch Wereschtschagin - The Sale of the Child Slave.jpg",
        ],
        "museum_url": "https://commons.wikimedia.org/wiki/File:Wassili_Wassiljewitsch_Wereschtschagin_-_The_Sale_of_the_Child_Slave.jpg",
    },
    {
        "id": "waterhouse-the-slave",
        "artist": "John William Waterhouse",
        "title": "The Slave",
        "year": "1872",
        "location": "Private collection",
        "notes": "Public domain reproduction on Commons.",
        "commons_files": [
            "John william waterhouse the slave.jpg",
        ],
        "museum_url": "https://commons.wikimedia.org/wiki/File:John_william_waterhouse_the_slave.jpg",
    },
    {
        "id": "gottlieb-cairo-slave-market",
        "artist": "Maurycy Gottlieb",
        "title": "Cairo Slave Market",
        "year": "1877",
        "location": "—",
        "notes": "Public domain on Wikimedia Commons.",
        "commons_files": [
            "Maurycy Gottlieb - Cairo Slave Market 1877.jpg",
        ],
        "museum_url": "https://commons.wikimedia.org/wiki/File:Maurycy_Gottlieb_-_Cairo_Slave_Market_1877.jpg",
    },
    {
        "id": "rosati-inspecting-new-arrivals",
        "artist": "Giulio Rosati",
        "title": "Inspection of New Arrivals (Picking the Favourite)",
        "year": "c. 1910 / before 1917",
        "location": "—",
        "notes": "Related Choosing/Picking the Favourite images also circulate as PD.",
        "commons_files": [
            "Inspecting New Arrivals by Giulio Rosati 2.jpg",
            "Inspecting New Arrivals by Giulio Rosati.jpg",
            "Giulio Rosati - Picking the Favourite.jpg",
        ],
        "museum_url": "https://commons.wikimedia.org/wiki/File:Inspecting_New_Arrivals_by_Giulio_Rosati_2.jpg",
    },
    {
        "id": "normand-bitter-draught",
        "artist": "Ernest Normand",
        "title": "The Bitter Draught of Slavery",
        "year": "1885",
        "location": "Cartwright Hall / Bradford Museums",
        "notes": "Wikimedia / Art UK.",
        "commons_files": [
            "Ernest Normand (1857-1923) - The Bitter Draught of Slavery - 1936-051 - Cartwright Hall Art Gallery.jpg",
        ],
        "museum_url": "https://artuk.org/discover/artworks/the-bitter-draught-of-slavery-23346",
    },
    {
        "id": "pilny-at-the-slave-market",
        "artist": "Otto Pilny",
        "title": "At the Slave Market",
        "year": "1916",
        "location": "—",
        "notes": "Artist died 1936; PD in many jurisdictions. See also related Pilny works.",
        "commons_files": [
            "Otto Pilny - At the slave market.jpeg",
            "The Slave Market by Otto Pilny.jpg",
            "Otto Pilny - The Slave Market.jpg",
        ],
        "museum_url": "https://commons.wikimedia.org/wiki/Category:Orientalist_paintings_by_Otto_Pilny",
    },
    # Harder-to-find: external links only (do not download third-party images)
    {
        "id": "crosio-beautiful-slave",
        "artist": "Luigi Crosio",
        "title": "The Beautiful Slave",
        "year": "1890",
        "location": "Art Renewal Center (view online)",
        "notes": (
            "Artist died 1915 (PD). No stable high-res Wikimedia original found; "
            "view the reproduction on Art Renewal Center (not mirrored here)."
        ),
        "commons_files": [],
        "search_terms": [],
        "museum_url": "https://www.artrenewal.org/artworks/the-beautiful-slave/luigi-crosio/38231",
        "external_links": [
            {
                "label": "Art Renewal Center",
                "url": "https://www.artrenewal.org/artworks/the-beautiful-slave/luigi-crosio/38231",
            },
        ],
        "skip_download": True,
        "hard_to_find": True,
    },
    {
        "id": "cercone-inspecting-slaves",
        "artist": "Ettore Cercone",
        "title": "Inspecting the Slaves / Examining Slaves",
        "year": "1890",
        "location": "Flickr (view online)",
        "notes": (
            "PD by date; no dedicated high-res Commons file found. "
            "View a public Flickr scan (not mirrored here)."
        ),
        "commons_files": [],
        "search_terms": [],
        "museum_url": "https://www.flickr.com/photos/amber-tree/15483321557",
        "external_links": [
            {
                "label": "Flickr",
                "url": "https://www.flickr.com/photos/amber-tree/15483321557",
            },
        ],
        "skip_download": True,
        "hard_to_find": True,
    },
    {
        "id": "ansen-hofmann-white-slaves",
        "artist": "Eduard Ansen-Hofmann (E. Anson-Hoffman)",
        "title": "Auction / Bidding scene (Торги) — related Orientalist market work",
        "year": "c. late 19th c.",
        "location": "Private collection (Commons scan)",
        "notes": (
            "Exact ‘White Slaves in the Desert’ / ‘White Slave Girl’ titles are scarce "
            "as clean museum files; this is a confirmed Ansen-Hofmann Orientalist market "
            "scene on Wikimedia Commons (PD)."
        ),
        "commons_files": [
            "Eduard Ansen-Hofmann, 1820-1904. Торги. 90 х 124 см. Частная коллекция (33703806928).jpg",
            "Eduard Ansen-Hofmann - White Slaves in the Desert.jpg",
            "Ansen-Hofmann The White Slave Girl.jpg",
        ],
        "search_terms": [
            'intitle:"Ansen-Hofmann"',
            'intitle:"Ansen Hofmann"',
        ],
        "museum_url": None,
        "hard_to_find": True,
    },
]


# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------


def _request(url: str, timeout: int = 60) -> bytes:
    """GET url with retries on 429 / transient errors."""
    last_err: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            last_err = e
            if e.code in (429, 503, 502, 500):
                # Honour Retry-After when present, but cap it
                retry_after = e.headers.get("Retry-After") if e.headers else None
                if retry_after and str(retry_after).isdigit():
                    wait = min(float(retry_after) + 1.0, MAX_RETRY_AFTER_SEC)
                else:
                    wait = min(RETRY_BASE_SEC * (2 ** attempt), MAX_RETRY_AFTER_SEC)
                print(
                    f"  · HTTP {e.code}, waiting {wait:.0f}s "
                    f"(attempt {attempt + 1}/{MAX_RETRIES})",
                    flush=True,
                )
                time.sleep(wait)
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            last_err = e
            wait = RETRY_BASE_SEC * (2 ** attempt)
            print(f"  · network error ({e}), waiting {wait:.0f}s (attempt {attempt + 1}/{MAX_RETRIES})")
            time.sleep(wait)
    raise last_err  # type: ignore[misc]


def _api_get(params: dict) -> dict:
    params = {**params, "format": "json"}
    query = urllib.parse.urlencode(params)
    url = f"{API_URL}?{query}"
    data = _request(url)
    return json.loads(data.decode("utf-8"))


# ---------------------------------------------------------------------------
# Wikimedia Commons resolution
# ---------------------------------------------------------------------------


def commons_file_info(filename: str) -> dict | None:
    """Return {url, width, height, mime, descriptionurl} for a Commons file, or None."""
    # MediaWiki expects title with File: prefix; spaces OK when encoded
    title = filename if filename.startswith("File:") else f"File:{filename}"
    data = _api_get(
        {
            "action": "query",
            "titles": title,
            "prop": "imageinfo",
            "iiprop": "url|size|mime|extmetadata",
            "iiurlwidth": 2400,  # also request a large thumbnail as fallback
        }
    )
    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if page.get("missing") is not None or "imageinfo" not in page:
            return None
        info = page["imageinfo"][0]
        return {
            "url": info.get("url"),
            "thumburl": info.get("thumburl"),
            "width": info.get("width"),
            "height": info.get("height"),
            "mime": info.get("mime"),
            "descriptionurl": info.get("descriptionurl"),
            "size": info.get("size"),
        }
    return None


def commons_search_file(search: str, limit: int = 5) -> list[str]:
    """Search Commons for files; return list of File: titles."""
    data = _api_get(
        {
            "action": "query",
            "list": "search",
            "srsearch": search,
            "srnamespace": 6,  # File namespace
            "srlimit": limit,
        }
    )
    results = data.get("query", {}).get("search", [])
    return [r["title"] for r in results]


def extension_for_mime(mime: str | None, url: str) -> str:
    if mime:
        mapping = {
            "image/jpeg": ".jpg",
            "image/jpg": ".jpg",
            "image/png": ".png",
            "image/gif": ".gif",
            "image/webp": ".webp",
            "image/tiff": ".tif",
        }
        if mime in mapping:
            return mapping[mime]
    path = urllib.parse.urlparse(url).path
    m = re.search(r"\.(jpe?g|png|gif|webp|tif{1,2})$", path, re.I)
    if m:
        ext = m.group(1).lower()
        if ext == "jpeg":
            return ".jpg"
        if ext == "tiff":
            return ".tif"
        return f".{ext}"
    return ".jpg"


def safe_filename(painting_id: str, ext: str) -> str:
    return f"{painting_id}{ext}"


def download_binary(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    data = _request(url, timeout=120)
    dest.write_bytes(data)


# ---------------------------------------------------------------------------
# Resolve + download one painting
# ---------------------------------------------------------------------------


def _clean_url(url: str | None) -> str | None:
    if not url:
        return url
    # Drop tracking query params Wikimedia sometimes appends
    parsed = urllib.parse.urlparse(url)
    return urllib.parse.urlunparse(parsed._replace(query="", fragment=""))


def _is_image(info: dict | None) -> bool:
    if not info or not info.get("url"):
        return False
    mime = (info.get("mime") or "").lower()
    if mime in IMAGE_MIMES:
        return True
    # Reject PDFs, HTML, etc. even if the title looks like an image
    if mime.startswith("image/"):
        return True
    return False


def _info_to_resolved(
    info: dict,
    *,
    source: str,
    commons_title: str,
    search_hit: str | None = None,
) -> dict:
    out = {
        "source": source,
        "commons_title": commons_title,
        "file_url": _clean_url(info["url"]),
        "thumb_url": _clean_url(info.get("thumburl")),
        "width": info.get("width"),
        "height": info.get("height"),
        "mime": info.get("mime"),
        "page_url": info.get("descriptionurl"),
    }
    if search_hit:
        out["search_hit"] = search_hit
    return out


def resolve_painting(p: dict) -> dict | None:
    """Find the best Commons image for a painting (prefer larger pixel width)."""
    candidates: list[dict] = []

    for name in p.get("commons_files") or []:
        time.sleep(REQUEST_DELAY_SEC)
        try:
            info = commons_file_info(name)
        except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
            print(f"  · lookup failed for {name!r}: {e}", flush=True)
            continue
        if _is_image(info):
            title = name if name.startswith("File:") else f"File:{name}"
            candidates.append(
                _info_to_resolved(info, source="wikimedia", commons_title=title)
            )
            # Prefer an explicit catalogue hit; stop after first good named file
            # unless later named files are larger (still collect a few).
            if len(candidates) >= 2:
                break

    if not candidates:
        for term in p.get("search_terms") or []:
            # Bias search toward image files (MediaWiki file-type filter)
            time.sleep(REQUEST_DELAY_SEC)
            try:
                titles = commons_search_file(f"{term} filetype:bitmap")
                if not titles:
                    titles = commons_search_file(term)
            except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
                print(f"  · search failed for {term!r}: {e}", flush=True)
                continue
            for title in titles:
                time.sleep(REQUEST_DELAY_SEC)
                bare = title[5:] if title.startswith("File:") else title
                # Skip obvious non-images by extension
                if re.search(r"\.(pdf|djvu|svg|webm|ogv|stl)$", bare, re.I):
                    continue
                try:
                    info = commons_file_info(bare)
                except (urllib.error.HTTPError, urllib.error.URLError, OSError) as e:
                    print(f"  · lookup failed for {title!r}: {e}", flush=True)
                    continue
                if _is_image(info):
                    candidates.append(
                        _info_to_resolved(
                            info,
                            source="wikimedia-search",
                            commons_title=title,
                            search_hit=term,
                        )
                    )
            if candidates:
                break

    if not candidates:
        return None

    # Largest width wins (then height)
    candidates.sort(
        key=lambda c: (c.get("width") or 0, c.get("height") or 0),
        reverse=True,
    )
    return candidates[0]


ENTRY_META_KEYS = (
    "id",
    "artist",
    "title",
    "year",
    "location",
    "notes",
    "museum_url",
    "hard_to_find",
    "external_links",
    "skip_download",
)


def _base_entry(p: dict) -> dict:
    return {k: p.get(k) for k in ENTRY_META_KEYS}


def process_all(force: bool = False) -> list[dict]:
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    manifest: list[dict] = []
    ok = 0
    fail = 0
    external_only = 0

    print(f"Downloading into {IMAGES_DIR}\n")

    for i, p in enumerate(PAINTINGS, 1):
        label = f"[{i}/{len(PAINTINGS)}] {p['artist']} — {p['title']}"
        print(label)

        # Manual exception: link out only, never download third-party host images
        if p.get("skip_download"):
            links = p.get("external_links") or []
            print(f"  · external only ({len(links)} link(s), not downloaded)")
            entry = {
                **_base_entry(p),
                "local_file": None,
                "status": "external",
            }
            manifest.append(entry)
            external_only += 1
            continue

        # Skip re-download if a local file already exists for this id
        existing = list(IMAGES_DIR.glob(f"{p['id']}.*"))
        existing = [f for f in existing if f.suffix.lower() in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".tif"}]
        if existing and not force:
            local = existing[0]
            print(f"  · already present: {local.name}")
            entry = {
                **_base_entry(p),
                "local_file": f"images/{local.name}",
                "status": "cached",
            }
            # try to enrich from previous manifest if available
            if MANIFEST_PATH.exists():
                try:
                    prev = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
                    old = next((x for x in prev if x.get("id") == p["id"]), None)
                    if old:
                        for key in ("source", "commons_title", "file_url", "page_url",
                                    "width", "height", "mime"):
                            if key in old:
                                entry[key] = old[key]
                except (json.JSONDecodeError, OSError):
                    pass
            manifest.append(entry)
            ok += 1
            continue

        resolved = resolve_painting(p)
        if not resolved:
            print("  ✗ no public Commons file found")
            entry = {
                **_base_entry(p),
                "local_file": None,
                "status": "missing",
            }
            manifest.append(entry)
            fail += 1
            continue

        ext = extension_for_mime(resolved.get("mime"), resolved["file_url"])
        dest_name = safe_filename(p["id"], ext)
        dest = IMAGES_DIR / dest_name
        try:
            print(f"  → {resolved.get('commons_title')}")
            print(f"  ↓ {resolved['file_url'][:90]}…")
            download_binary(resolved["file_url"], dest)
            size_kb = dest.stat().st_size / 1024
            print(f"  ✓ saved {dest.name} ({size_kb:.0f} KB)")
            entry = {
                **_base_entry(p),
                "local_file": f"images/{dest_name}",
                "status": "downloaded",
                **resolved,
            }
            manifest.append(entry)
            ok += 1
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            print(f"  ✗ download failed: {e}")
            entry = {
                **_base_entry(p),
                "local_file": None,
                "status": "error",
                "error": str(e),
                **{k: resolved.get(k) for k in ("commons_title", "file_url", "page_url")},
            }
            manifest.append(entry)
            fail += 1

        time.sleep(REQUEST_DELAY_SEC)

    MANIFEST_PATH.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        f"\nDone. {ok} downloaded/cached, {external_only} external-only, "
        f"{fail} missing/failed."
    )
    print(f"Manifest written to {MANIFEST_PATH}")
    return manifest


def main() -> int:
    force = "--force" in sys.argv
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python3 download_images.py [--force]")
        print("  --force   re-download even if local files exist")
        return 0
    process_all(force=force)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
