/* Service worker for paintings.dhimmitude.org
 *
 * Strategy:
 * - App shell (HTML/CSS/JS/manifest/favicon): stale-while-revalidate
 * - Images under /images/: cache-first (content almost never changes)
 * - Bump CACHE_VERSION (or run stamp_assets.py) after publishing content changes
 *   so clients drop old caches.
 */
const CACHE_VERSION = "20260916-ce86a839d167";
const SHELL_CACHE = `gallery-shell-${CACHE_VERSION}`;
const IMAGE_CACHE = `gallery-images-${CACHE_VERSION}`;

const PRECACHE_URLS = [
  "./",
  "./index.html",
  "./styles.css?v=13ca16b93e63",
  "./app.js?v=9396b7887666",
  "./manifest.json?v=ce86a839d167",
  "./favicon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches
      .open(SHELL_CACHE)
      .then((cache) => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== SHELL_CACHE && key !== IMAGE_CACHE)
            .map((key) => caches.delete(key))
        )
      )
      .then(() => self.clients.claim())
  );
});

function isSameOrigin(url) {
  return url.origin === self.location.origin;
}

function isImagePath(pathname) {
  return (
    pathname.startsWith("/images/") ||
    /\.(?:avif|css|gif|ico|jpe?g|js|json|png|svg|webp)$/i.test(pathname)
  );
}

async function staleWhileRevalidate(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  const networkPromise = fetch(request)
    .then((response) => {
      if (response && response.ok) {
        cache.put(request, response.clone());
      }
      return response;
    })
    .catch(() => cached);

  return cached || networkPromise;
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  const response = await fetch(request);
  if (response && response.ok) {
    cache.put(request, response.clone());
  }
  return response;
}

self.addEventListener("fetch", (event) => {
  const { request } = event;
  if (request.method !== "GET") return;

  const url = new URL(request.url);
  if (!isSameOrigin(url)) return;

  // Navigations / HTML documents
  if (request.mode === "navigate" || request.destination === "document") {
    event.respondWith(staleWhileRevalidate(request, SHELL_CACHE));
    return;
  }

  // Gallery images: long-lived cache-first
  if (url.pathname.startsWith("/images/")) {
    event.respondWith(cacheFirst(request, IMAGE_CACHE));
    return;
  }

  // Versioned shell assets and favicon
  if (isImagePath(url.pathname) || url.searchParams.has("v")) {
    const cacheName = url.pathname.startsWith("/images/")
      ? IMAGE_CACHE
      : SHELL_CACHE;
    event.respondWith(staleWhileRevalidate(request, cacheName));
  }
});
