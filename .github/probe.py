import re, os, time, io, json, requests, hashlib
from urllib.parse import urljoin, quote
from PIL import Image
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36","Accept-Language":"ko-KR,ko;q=0.9"}
WUA={"User-Agent":"tech-cycle-deck-probe/1.0 (class presentation; github actions)"}
os.makedirs("probe/img",exist_ok=True)
out=open("probe/index.tsv","w")
def save(tag,u,ref,extra=""):
    try:
        time.sleep(0.5); ir=requests.get(u,headers={**(WUA if 'wikimedia' in u else UA),"Referer":ref},timeout=40)
        if ir.status_code!=200: out.write(f"{tag}\tHTTP{ir.status_code}\t{u}\n"); return False
        im=Image.open(io.BytesIO(ir.content)); w,h=im.size
    except Exception: return False
    if w<MINW or h<500: return False
    name=f"{tag}_{hashlib.md5(u.encode()).hexdigest()[:6]}.jpg"
    im=im.convert("RGB"); im.thumbnail((2000,2000)); im.save("probe/img/"+name,quality=88)
    out.write(f"{tag}\t{name}\t{w}x{h}\t{u}\t{ref}\t{extra}\n"); return True
MINW=900
for line in open(".github/pages.txt",encoding="utf-8"):
    line=line.strip()
    if not line or line.startswith("#"): continue
    tag,url=line.split(None,1)
    if tag=='MINW': MINW=int(url); continue
    if url.startswith("ov:") or url.startswith("us:"):
        q=url[3:]
        if url.startswith("ov:"):
            api="https://api.openverse.org/v1/images/?page_size=12&size=large&q="+quote(q)
        else:
            api="https://unsplash.com/napi/search/photos?per_page=12&query="+quote(q)
        try:
            time.sleep(4); rr=requests.get(api,headers=UA,timeout=60); data=rr.json()
        except Exception as e:
            out.write(f"{tag}\tFAILAPI\t{q}\t{rr.status_code if 'rr' in dir() else ''} {str(e)[:80]} {rr.text[:120] if 'rr' in dir() else ''}\n"); continue
        n=0
        for it in data.get("results",[]):
            if url.startswith("ov:"):
                u=it.get("url"); ref=it.get("foreign_landing_url",""); extra=f"{it.get('title','')} | {it.get('license','')} {it.get('license_version','')} | {it.get('creator','')} | {it.get('source','')}"
            else:
                u=(it.get("urls") or {}).get("regular","").replace("w=1080","w=1800"); ref=(it.get("links") or {}).get("html",""); extra=f"{it.get('alt_description','')} | Unsplash | {(it.get('user') or {}).get('name','')} | premium={it.get('premium')} plus={it.get('plus')}"
            if not u: continue
            if save(tag,u,ref,extra.replace("\t"," ").replace("\n"," ")): n+=1
            if n>=6: break
        if n==0: out.write(f"{tag}\tNONE\t{url}\t{str(data)[:150]}\n")
        continue
    if url.startswith("commons:"):
        q=url[8:]
        api="https://commons.wikimedia.org/w/api.php?action=query&format=json&generator=search&gsrnamespace=6&gsrlimit=10&prop=imageinfo&iiprop=url|size|extmetadata&iiurlwidth=1920&gsrsearch="+quote(q)
        try:
            rr=requests.get(api,headers=WUA,timeout=30); data=rr.json()
        except Exception as e: out.write(f"{tag}\tFAILAPI\t{q}\t{rr.status_code} {rr.text[:150]}\n"); continue
        n=0
        for p in (data.get("query",{}).get("pages",{}) or {}).values():
            ii=(p.get("imageinfo") or [{}])[0]; md=ii.get("extmetadata",{})
            lic=md.get("LicenseShortName",{}).get("value",""); art=re.sub("<[^>]+>","",md.get("Artist",{}).get("value",""))[:80]
            u=ii.get("thumburl") or ii.get("url")
            if not u or not re.search(r'\.(jpe?g|png)$',ii.get("url",""),re.I): continue
            ok=save(tag,u,ii.get("descriptionurl",""),f"{p.get('title')} | {lic} | {art}")
            if not ok and ii.get("size",0)<12e6: ok=save(tag,ii.get("url"),ii.get("descriptionurl",""),f"{p.get('title')} | {lic} | {art}")
            if not ok: out.write(f"{tag}\tSKIP\t{u}\n")
            if ok: n+=1
            if n>=6: break
        if n==0: out.write(f"{tag}\tNONE\t{url}\t{str(data)[:200]}\n")
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
