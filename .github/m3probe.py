import json, os, re, requests
from PIL import Image
from io import BytesIO
OUT = "probe/m3"; os.makedirs(OUT, exist_ok=True)
H = {"User-Agent": "tech-cycle-deck-probe/1.0 (class presentation; github actions)"}
API = "https://commons.wikimedia.org/w/api.php"
Q = [
  'incategory:"Tesla Model 3" 2017',
  'Tesla Model 3 unveiling 2016',
  'Tesla Model 3 handover event 2017',
  'Tesla Model 3 first deliveries July 2017',
  'Tesla Model 3 2017 red',
  'Tesla Model 3 2017 front',
  'Tesla Model 3 Fremont factory',
  'Tesla Model 3 production line',
  'Tesla Model 3 release candidate',
  'Tesla Model 3 prototype 2016',
]
seen, meta = set(), []
for q in Q:
    r = requests.get(API, headers=H, params={"action": "query", "format": "json", "generator": "search", "gsrsearch": q, "gsrnamespace": 6, "gsrlimit": 12,
        "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1800}, timeout=30).json()
    for p in sorted((r.get("query") or {}).get("pages", {}).values(), key=lambda x: x.get("index", 0)):
        t = p["title"]
        if t in seen or not re.search(r"\.(jpe?g|png)$", t, re.I): continue
        seen.add(t); ii = p["imageinfo"][0]; em = ii.get("extmetadata", {})
        g = lambda k: re.sub("<[^>]+>", "", (em.get(k) or {}).get("value", ""))[:200]
        if ii["width"] < 1200: continue
        k = f"{len(meta):03d}"
        try:
            im = Image.open(BytesIO(requests.get(ii["thumburl"], headers=H, timeout=60).content)).convert("RGB")
            im.save(f"{OUT}/{k}.jpg", quality=86)
            im.thumbnail((360, 240)); im.save(f"{OUT}/t{k}.jpg", quality=80)
        except Exception as e:
            print("fail", t, e); continue
        meta.append({"k": k, "q": q, "title": t, "w": ii["width"], "h": ii["height"], "page": ii["descriptionurl"], "src": ii["thumburl"],
            "artist": g("Artist"), "license": g("LicenseShortName"), "date": g("DateTimeOriginal"), "desc": g("ImageDescription")})
        if len(meta) >= 70: break
json.dump(meta, open(f"{OUT}/meta.json", "w"), ensure_ascii=False, indent=1)
print(len(meta))
