# v1.23.0 — نرخ خرید دلار و درهم در بازار آزاد برای PFM.
# هر چند ساعت با GitHub Actions اجرا می‌شود و rates.json کنار index.html را به‌روز می‌کند؛
# اپ همان فایل را از همان دامنه (sadeghmajedi.github.io) می‌خواند، پس CORS و فیلتر منبع روی گوشی مطرح نیست.
# منبع اول: bonbast.com (نرخ خرید usd2/aed2، تومان). منبع دوم: tgju.org (قیمت بازار، ریال؛ خرید/فروش جدا ندارد).
import json, re, sys, urllib.request, urllib.parse, http.cookiejar, datetime, os

UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36'}
jar = http.cookiejar.CookieJar()
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

def get(url, data=None, headers=None):
    h = dict(UA); h.update(headers or {})
    with op.open(urllib.request.Request(url, data=data, headers=h), timeout=25) as r:
        return r.read().decode('utf-8', 'replace')

def num(x):
    return float(str(x).replace(',', '').strip())

def bonbast():
    html = get('https://bonbast.com/')
    m = re.search(r'param["\']?\s*[:=]\s*["\']([^"\']+)', html)
    if not m:
        raise RuntimeError('bonbast: token not found')
    body = urllib.parse.urlencode({'param': m.group(1)}).encode()
    d = json.loads(get('https://bonbast.com/json', body, {
        'Referer': 'https://bonbast.com/', 'X-Requested-With': 'XMLHttpRequest',
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8'}))
    # usd2/aed2 = خرید (تومان) → ریال
    return {'src': 'bonbast', 'kind': 'buy', 'usd': round(num(d['usd2']) * 10), 'aed': round(num(d['aed2']) * 10),
            'srcTime': d.get('last_modified', '')}

def tgju():
    d = json.loads(get('https://call1.tgju.org/ajax.json'))['current']
    return {'src': 'tgju', 'kind': 'market', 'usd': round(num(d['price_dollar_rl']['p'])), 'aed': round(num(d['price_aed']['p'])),
            'srcTime': d['price_dollar_rl'].get('t', '')}

def sane(r):
    u, a = r['usd'], r['aed']
    return 100000 <= u <= 1000000000 and 10000 <= a <= 500000000 and 2.5 <= u / a <= 5

res = None
for fn in (bonbast, tgju):
    try:
        r = fn()
        if sane(r):
            res = r
            break
        print('insane values from', fn.__name__, r)
    except Exception as e:
        print('source failed:', fn.__name__, repr(e)[:200])

if not res:
    print('::warning::no rate source answered; rates.json unchanged')
    sys.exit(0)

path = 'rates.json'
old = {}
if os.path.exists(path):
    try:
        old = json.load(open(path, encoding='utf-8'))
    except Exception:
        old = {}
# نرخ ثابت (تعطیلی بازار): هر ۱۲ ساعت یک بار زمان فایل تازه می‌شود تا اپ آن را «کهنه» نشان ندهد
def age_hours(ts):
    try:
        t = datetime.datetime.strptime(ts, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
        return (datetime.datetime.now(datetime.timezone.utc) - t).total_seconds() / 3600
    except Exception:
        return 1e9
if old.get('usd') == res['usd'] and old.get('aed') == res['aed'] and old.get('src') == res['src'] and age_hours(old.get('updated', '')) < 12:
    print('unchanged', res)
    sys.exit(0)

res = {'v': 1, 'updated': datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'), **res}
with open(path, 'w', encoding='utf-8') as f:
    json.dump(res, f, ensure_ascii=False, indent=1)
    f.write('\n')
print('updated', res)
