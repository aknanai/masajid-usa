// Masajid USA - Service Worker
// This enables offline support and faster loading for returning visitors

// Derive the base path dynamically (works on any subpath like /masajid-usa/)
const BASE_PATH = self.location.pathname.replace(/\/sw\.js$/, '') || '';

const CACHE_NAME = 'masajid-usa-v1';
const STATIC_CACHE = 'masajid-usa-static-v1';
const DATA_CACHE = 'masajid-usa-data-v1';
const EXTERNAL_CACHE = 'masajid-usa-external-v1';

// App shell assets to pre-cache on install
const PRECACHE_URLS = [
  BASE_PATH + '/',
  BASE_PATH + '/css/style.css',
  BASE_PATH + '/js/app.js',
  BASE_PATH + '/js/prayer-times.js',
  BASE_PATH + '/js/favorites.js',
  BASE_PATH + '/js/nearby-masajid.js',
  BASE_PATH + '/js/qibla.js',
  BASE_PATH + '/favicon.svg',
  BASE_PATH + '/manifest.json',
  BASE_PATH + '/icons/icon-192x192.png',
  BASE_PATH + '/icons/icon-512x512.png'
];

// Install event - precache app shell
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(STATIC_CACHE).then(cache => {
      return cache.addAll(PRECACHE_URLS);
    }).then(() => {
      return self.skipWaiting();
    })
  );
});

// Activate event - clean old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(name => {
          if (name !== STATIC_CACHE && name !== DATA_CACHE && name !== EXTERNAL_CACHE) {
            return caches.delete(name);
          }
        })
      );
    }).then(() => {
      return self.clients.claim();
    })
  );
});

// Helper: is this a navigation request for an HTML page?
function isNavigationRequest(request) {
  return request.mode === 'navigate' ||
    (request.method === 'GET' &&
     request.headers.get('Accept') &&
     request.headers.get('Accept').includes('text/html'));
}

// Helper: is this a data request?
function isDataRequest(url) {
  return url.pathname.includes('/data/') ||
         url.pathname.endsWith('.json');
}

// Helper: is this an external CDN resource?
function isExternalResource(url) {
  return url.origin !== self.location.origin;
}

// Helper: is this a static asset?
function isStaticAsset(url) {
  const extensions = ['.css', '.js', '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.webp', '.woff', '.woff2', '.ttf'];
  return extensions.some(ext => url.pathname.endsWith(ext));
}

// Helper: is this request within our app scope?
function isInScope(url) {
  return url.origin === self.location.origin &&
         url.pathname.startsWith(BASE_PATH + '/');
}

// Fetch event - smart caching strategy
self.addEventListener('fetch', event => {
  const request = event.request;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip requests outside our scope
  if (!isExternalResource(url) && !isInScope(url)) return;

  // Strategy 1: External CDN resources (stale-while-revalidate)
  if (isExternalResource(url)) {
    event.respondWith(
      caches.open(EXTERNAL_CACHE).then(cache => {
        return cache.match(request).then(cachedResponse => {
          const fetchPromise = fetch(request).then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              cache.put(request, networkResponse.clone());
            }
            return networkResponse;
          }).catch(() => cachedResponse);
          return cachedResponse || fetchPromise;
        });
      })
    );
    return;
  }

  // Strategy 2: Data requests (network-first, fallback to cache)
  if (isDataRequest(url)) {
    event.respondWith(
      caches.open(DATA_CACHE).then(cache => {
        return fetch(request).then(networkResponse => {
          if (networkResponse && networkResponse.status === 200) {
            cache.put(request, networkResponse.clone());
          }
          return networkResponse;
        }).catch(() => {
          return cache.match(request);
        });
      })
    );
    return;
  }

  // Strategy 3: Static assets (cache-first)
  if (isStaticAsset(url)) {
    event.respondWith(
      caches.match(request).then(cachedResponse => {
        if (cachedResponse) {
          // Update the cache in the background
          fetch(request).then(networkResponse => {
            if (networkResponse && networkResponse.status === 200) {
              caches.open(STATIC_CACHE).then(cache => cache.put(request, networkResponse));
            }
          }).catch(() => {});
          return cachedResponse;
        }
        return fetch(request).then(networkResponse => {
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(STATIC_CACHE).then(cache => cache.put(request, clone));
          }
          return networkResponse;
        });
      })
    );
    return;
  }

  // Strategy 4: Navigation/HTML requests (network-first, cache fallback)
  if (isNavigationRequest(request)) {
    event.respondWith(
      fetch(request).then(networkResponse => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(STATIC_CACHE).then(cache => cache.put(request, clone));
        }
        return networkResponse;
      }).catch(() => {
        // Try the cache for the exact URL first
        return caches.match(request).then(cachedResponse => {
          if (cachedResponse) return cachedResponse;
          // Fallback to cached root page
          return caches.match(BASE_PATH + '/');
        });
      })
    );
    return;
  }

  // Strategy 5: Everything else (network, no cache)
  event.respondWith(fetch(request).catch(() => {
    return caches.match(request);
  }));
});
