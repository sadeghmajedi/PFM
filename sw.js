// PFM Service Worker — پشتیبانی آفلاین
// Copyright (c) 2026 Seyed Sadegh Majedi. All rights reserved. See LICENSE.
var CACHE_NAME = 'pfm-cache-v1.34.0';
var SHARE_CACHE = 'pfm-share';   // v1.20.0: متن اشتراک‌گذاری‌شده (اندروید) تا صفحه آن را بخواند
var CACHE_FILES = [
  './',
  './index.html',
  './manifest.json',
  './icon-192.png',
  './icon-512.png',
  './icon-180.png',
  './icon-maskable-192.png',
  './icon-maskable-512.png'
];

self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function(cache) {
      return cache.addAll(CACHE_FILES);
    }).then(function() {
      return self.skipWaiting();
    })
  );
});

self.addEventListener('activate', function(event) {
  event.waitUntil(
    caches.keys().then(function(keys) {
      return Promise.all(
        keys.filter(function(key) { return key !== CACHE_NAME && key !== SHARE_CACHE; })
            .map(function(key) { return caches.delete(key); })
      );
    }).then(function() {
      return self.clients.claim();
    })
  );
});

// استراتژی: برای version.json همیشه شبکه (برای تشخیص آپدیت)
// برای بقیه فایل‌ها: شبکه اول، اگر نبود از کش (و کش را هم به‌روز کن)
self.addEventListener('fetch', function(event) {
  var url = event.request.url;

  // v1.20.0 — Web Share Target (اندروید): پیامکی که از اپ پیامک به PFM اشتراک‌گذاری شده.
  // همین‌جا جواب داده می‌شود و هرگز به شبکه نمی‌رود (متن پیامک بانک نباید به سرور برسد).
  if (event.request.method === 'POST' && new URL(url).pathname.slice(-13) === '/share-target') {
    event.respondWith(
      event.request.formData().then(function(fd) {
        var parts = [fd.get('title'), fd.get('text'), fd.get('url')].filter(function(x){ return x && String(x).trim(); });
        return caches.open(SHARE_CACHE).then(function(cache) {
          return cache.put('./__shared-sms', new Response(parts.join('\n'), { headers: { 'Content-Type': 'text/plain; charset=utf-8' } }));
        });
      }).catch(function() {}).then(function() {
        return Response.redirect(new URL('./?shared=1', self.registration.scope).href, 303);
      })
    );
    return;
  }

  // v1.23.0 — نرخ ارز: همیشه از شبکه و بدون کش (هر درخواست ?t= دارد و نباید کش را پر کند)
  if (url.indexOf('rates.json') !== -1) {
    event.respondWith(fetch(event.request, { cache: 'no-store' }));
    return;
  }

  if (url.indexOf('version.json') !== -1) {
    var bustedUrl = url.split('?')[0] + '?_sw=' + Date.now();
    event.respondWith(
      fetch(bustedUrl, { cache: 'no-store' }).catch(function() {
        return caches.match(event.request);
      })
    );
    return;
  }

  event.respondWith(
    fetch(event.request).then(function(response) {
      if (response && response.status === 200 && event.request.method === 'GET') {
        var responseClone = response.clone();
        caches.open(CACHE_NAME).then(function(cache) {
          cache.put(event.request, responseClone);
        });
      }
      return response;
    }).catch(function() {
      return caches.match(event.request).then(function(cached) {
        return cached || caches.match('./index.html');
      });
    })
  );
});
