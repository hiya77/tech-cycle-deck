import re, os, io, json, requests, hashlib
from urllib.parse import urljoin, quote
from PIL import Image
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36","Accept-Language":"ko-KR,ko;q=0.9"}
WUA={"User-Agent":"tech-cycle-deck-probe/1.0 (class presentation; github actions)"}
os.makedirs("probe/img",exist_ok=True)
out=open("probe/index.tsv","w")
def save(tag,u,ref,extra=""):
    try:
        ir=requests.get(u,headers={**(WUA if 'wikimedia' in u else UA),"Referer":ref},timeout=30)
        im=Image.open(io.BytesIO(ir.content)); w,h=im.size
    except Exception: return False
    if w<900 or h<500: return False
    name=f"{tag}_{hashlib.md5(u.encode()).hexdigest()[:6]}.jpg"
    im=im.convert("RGB"); im.thumbnail((2000,2000)); im.save("probe/img/"+name,quality=88)
    out.write(f"{tag}\t{name}\t{w}x{h}\t{u}\t{ref}\t{extra}\n"); return True
for line in open(".github/pages.txt",encoding="utf-8"):
    line=line.strip()
    if not line or line.startswith("#"): continue
    tag,url=line.split(None,1)
    if url.startswith("commons:"):
        q=url[8:]
        api="https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit=10&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=1800&gsrsearch="+quote(q)
        try: data=requests.get(api,headers=WUA,timeout=30).json()
        except Exception as e: out.write(f"{tag}\tFAILAPI\t{q}\t{e}\n"); continue
        n=0
        for p in (data.get("query",{}).get("pages",{}) or {}).values():
            ii=(p.get("imageinfo") or [{}])[0]; md=ii.get("extmetadata",{})
            lic=md.get("LicenseShortName",{}).get("value",""); art=re.sub("<[^>]+>","",md.get("Artist",{}).get("value",""))[:80]
            u=ii.get("thumburl") or ii.get("url")
            if not u or not re.search(r'\.(jpe?g|png)$',ii.get("url",""),re.I): continue
            if save(tag,u,ii.get("descriptionurl",""),f"{p.get('title')} | {lic} | {art}"): n+=1
            if n>=6: break
        if n==0: out.write(f"{tag}\tNONE\t{url}\n")
        continue
    if re.search(r'\.(jpe?g|png|webp)$',url,re.I):
        if not save(tag,url,url): out.write(f"{tag}\tNONE\t{url}\n")
        continue
    try:
        r=requests.get(url,headers=UA,timeout=25); html=r.text
    except Exception as e:
        out.write(f"{tag}\tFAILPAGE\t{url}\t{e}\n"); continue
    cands=re.findall(r'<meta[^>]+(?:property|name)=["\'](?:og:image|twitter:image)["\'][^>]+content=["\']([^"\']+)',html)
    cands+=re.findall(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:property|name)=["\']og:image',html)
    cands+=re.findall(r'(?:src|data-src|data-original|href)=["\']([^"\']+\.(?:jpe?g|png|webp)(?:\?[^"\']*)?)["\']',html,re.I)
    seen=[];n=0
    for c in cands:
        u=urljoin(url,c.replace("&amp;","&"))
        if u in seen or re.search(r'logo|icon|banner|btn|sprite|favicon|thumb_s|profile|ad[_/]|default_image|BN_728',u,re.I): continue
        seen.append(u)
        if save(tag,u,url): n+=1
        if n>=8: break
    if n==0: out.write(f"{tag}\tNONE\t{url}\t{r.status_code} {len(html)}\n")
out.close()
