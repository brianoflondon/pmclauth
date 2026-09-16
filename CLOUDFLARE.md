# Cloudflare caching for `paintings.dhimmitude.org`

GitHub Pages (Fastly) already sets short TTLs. Cloudflare in front of it will **not** cache HTML by default (`cf-cache-status: DYNAMIC`). For a rarely changing static gallery, push caching into Cloudflare explicitly.

This repo also ships a **service worker** (`sw.js`) and **content-hash query strings** on CSS/JS/manifest so browsers and Cloudflare can keep assets for a long time and still bust cache when you publish changes (`python3 stamp_assets.py`).

## Recommended Cache Rules (Cloudflare dashboard)

Go to **Caching → Cache Rules** (or **Rules → Overview → Cache Rules**) for the zone that hosts `paintings.dhimmitude.org`.

Create **three rules**, in this order (first match can win depending on plan UI — put more specific first).

### Rule 1 — Images (highest impact)

| Field | Value |
|--------|--------|
| Rule name | `Gallery images long cache` |
| If | Hostname equals `paintings.dhimmitude.org` **AND** URI Path starts with `/images/` |
| Then | **Eligible for cache** |
| Edge TTL | Override — **1 month** (or 1 year) |
| Browser TTL | Override — **1 week** (optional; SW also caches images) |
| Origin Cache-Control | Ignore / bypass origin directives if your plan offers it |

### Rule 2 — Fingerprinted static assets

| Field | Value |
|--------|--------|
| Rule name | `Gallery versioned assets` |
| If | Hostname equals `paintings.dhimmitude.org` **AND** (URI Path ends with `.css` OR `.js` OR `.json` OR `.svg` OR `.ico` OR `.woff2`) |
| Then | **Eligible for cache** |
| Edge TTL | Override — **1 month** |
| Browser TTL | Respect origin **or** Override **1 day** |

Because `styles.css?v=…`, `app.js?v=…`, and `manifest.json?v=…` change the URL when content changes, long edge TTL is safe.

### Rule 3 — HTML / everything else on this host

| Field | Value |
|--------|--------|
| Rule name | `Gallery HTML cache everything` |
| If | Hostname equals `paintings.dhimmitude.org` |
| Then | **Cache eligibility: Cache Everything** |
| Edge TTL | Override — **4 hours** (or 1 hour if you deploy often) |
| Browser TTL | Override — **1 hour** *or* Respect origin |

This is the rule that turns `cf-cache-status: DYNAMIC` into `HIT` for `/`.

After the first warm requests you should see:

- `/` → `cf-cache-status: HIT` (or `MISS` then `HIT`)
- `/styles.css?v=…`, `/app.js?v=…` → `HIT`
- `/images/…` → `HIT`

## Optional but useful settings

1. **Caching → Configuration**
   - **Caching level**: Standard
   - **Browser Cache TTL**: Respect Existing Headers (rules above override where set)
   - **Always Online**: On
2. **Speed → Optimization**
   - **Auto Minify**: CSS/JS/HTML on (safe for this static site)
   - **Brotli**: On
   - **Early Hints**: On if available
3. **Network**
   - **HTTP/3 (with QUIC)**: On
4. **Purge**
   - After each deploy that changes HTML or unversioned files: **Caching → Configuration → Purge Everything** for this host, *or* purge `/` + `/index.html` + `/sw.js`.
   - Versioned `?v=` assets do not need purge.
5. **Favicon**
   - Repo now serves `/favicon.svg`. After deploy, purge any cached **404** for `/favicon.ico` if CF stored it.

## Deploy workflow (repo)

```bash
# After changing CSS/JS/manifest/images metadata:
python3 stamp_assets.py
git add -A && git commit -m "Bump asset cache fingerprints"
git push
# Then purge Cloudflare HTML + sw.js (or Purge Everything once)
```

## What Cloudflare cannot fix alone

- **Google Fonts** still load from `fonts.googleapis.com` / `fonts.gstatic.com` (third-party). First visit pays that cost; repeat visits use the browser font cache.
- **GitHub Pages origin** still sits behind Fastly; with CF edge cache hits, most visitors never reach Fastly.
- **Very large JPEGs** (multi‑MB) benefit more from image compression/WebP later; caching still removes repeat download cost.

## Quick verify

```bash
curl -sI https://paintings.dhimmitude.org/ | egrep -i 'cf-cache-status|cache-control|age|cf-ray'
curl -sI 'https://paintings.dhimmitude.org/styles.css' | egrep -i 'cf-cache-status|cache-control|age'
curl -sI 'https://paintings.dhimmitude.org/images/gerome-slave-market-1866.jpg' | egrep -i 'cf-cache-status|cache-control|age'
```

Second request to the same CF POP should show `cf-cache-status: HIT` and rising `age`.
