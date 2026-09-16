/* Service worker for paintings.dhimmitude.org
 *
 * Strategy:
 * - App shell (HTML/CSS/JS/manifest/favicon): stale-while-revalidate
 * - Gallery images (…/images/…): cache-first (content almost never changes)
 * - Bump CACHE_VERSION (or run stamp_assets.py) after publishing content changes
 *   so clients drop old caches.
 */
const CACHE_VERSION = "20260916-2eece7a53342";
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

/** True for gallery image paths at site root or under a GH Pages subpath. */
function isGalleryImagePath(pathname) {
  return (
    pathname === "/images" ||
    pathname.startsWith("/images/") ||
    pathname.includes("/images/")
  );
}

function isStaticAssetPath(pathname) {
  return /\.(?:avif|css|gif|ico|jpe?g|js|json|png|svg|webp)$/i.test(pathname);
}

function offlineFallback(request) {
  const accepts = request.headers.get("accept") || "";
  if (request.mode === "navigate" || accepts.includes("text/html")) {
    return new Response(
      "<!DOCTYPE html><title>Offline</title><p>Offline — reload when you are back online.</p>",
      {
        status: 503,
        statusText: "Service Unavailable",
        headers: { "Content-Type": "text/html; charset=utf-8" },
      }
    );
  }
  return new Response("Offline", {
    status: 503,
    statusText: "Service Unavailable",
    headers: { "Content-Type": "text/plain; charset=utf-8" },
  });
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
    .catch(() => null);

  const response = cached || (await networkPromise);
  return response || offlineFallback(request);
}

async function cacheFirst(request, cacheName) {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response && response.ok) {
      cache.put(request, response.clone());
    }
    return response || offlineFallback(request);
  } catch {
    return offlineFallback(request);
  }
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

  // Gallery images: long-lived cache-first (root or project-pages subpath)
  if (isGalleryImagePath(url.pathname)) {
    event.respondWith(cacheFirst(request, IMAGE_CACHE));
    return;
  }

  // Versioned shell assets and favicon
  if (isStaticAssetPath(url.pathname) || url.searchParams.has("v")) {
    event.respondWith(staleWhileRevalidate(request, SHELL_CACHE));
  }
});
