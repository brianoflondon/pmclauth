# Orientalist Paintings — Public Domain Gallery

A small static site that downloads and displays 19th- and early-20th-century Orientalist paintings from **public-domain / open** sources (mainly [Wikimedia Commons](https://commons.wikimedia.org/)).

## What’s included

| File | Purpose |
|------|---------|
| `download_images.py` | Fetches high-res files via the Wikimedia Commons API and writes `manifest.json` |
| `images/` | Downloaded image files (created by the script) |
| `manifest.json` | Metadata + local paths used by the gallery |
| `index.html`, `styles.css`, `app.js` | Static gallery UI (GitHub Pages ready) |

## Setup

Requires **Python 3.9+** (stdlib only — no pip packages).

```bash
# Download (or re-download) images
python3 download_images.py

# Force re-download even if files already exist
python3 download_images.py --force
```

The script is polite to Wikimedia (short delay between requests) and skips files that are already on disk unless you pass `--force`.

### Preview locally

GitHub Pages and modern browsers need HTTP for `fetch("manifest.json")`. From this folder:

```bash
python3 -m http.server 8000
```

Open http://localhost:8000

## Deploy on GitHub Pages

1. Create a repo and push this folder (include `images/`, `manifest.json`, and the HTML/CSS/JS files).
2. On GitHub: **Settings → Pages → Build and deployment**
3. Source: **Deploy from a branch**
4. Branch: `main` (or `master`), folder: **/ (root)**
5. Save. The site will be at `https://<user>.github.io/<repo>/`

**Note:** Large images can make the repo heavy. If needed, use [Git LFS](https://git-lfs.github.com/) for `images/*`, or host images on Commons/CDN and point `local_file` at absolute URLs.

### Optional: ignore huge binaries during development

If you only want the script and site code in git until you’re ready to publish:

```gitignore
# example — remove these lines before publishing the gallery images
# images/
# manifest.json
```

## Licence / reuse

- **Artworks:** Most are public domain because the artists died long enough ago (typically life + 70 years). Always check the specific Wikimedia or museum page for the file you use.
- **This site’s code:** free to reuse and adapt.
- The download script sends a descriptive User-Agent; do not use it to hammer Wikimedia.

## Paintings catalogue

Confirmed Commons-oriented sources include works by Ingres, Allan, Roberts, Müller, Gérôme, Čermák, Gyzis, Vereshchagin, Waterhouse, Gottlieb, Rosati, Normand, and Pilny. A few titles (Crosio, Cercone, Ansen-Hofmann) are harder to find in high-res open form; the script tries Commons filenames and search, then marks them missing if nothing turns up.

Hard-to-find items appear in the gallery as “Image not found” with notes so the catalogue stays complete.
