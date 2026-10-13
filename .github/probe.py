import re, os, io, requests, hashlib
from urllib.parse import urljoin
from PIL import Image
UA={"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36","Accept-Language":"ko-KR,ko;q=0.9"}
os.makedirs("probe/img",exist_ok=True)
out=open("probe/index.tsv","w")
for line in open(".github/pages.txt",encoding="utf-8"):
    line=line.strip()
    if not line or line.startswith("#"): continue
    tag,url=line.split(None,1)
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
        if u in seen or re.search(r'logo|icon|banner|btn|sprite|favicon|thumb_s|profile|ad[_/]',u,re.I): continue
        seen.append(u)
        try:
            ir=requests.get(u,headers={**UA,"Referer":url},timeout=25)
            im=Image.open(io.BytesIO(ir.content)); w,h=im.size
        except Exception: continue
        if w<700 or h<380: continue
        name=f"{tag}_{hashlib.md5(u.encode()).hexdigest()[:6]}.jpg"
        im=im.convert("RGB"); im.thumbnail((2000,2000)); im.save("probe/img/"+name,quality=88)
        out.write(f"{tag}\t{name}\t{w}x{h}\t{u}\t{url}\n"); n+=1
        if n>=4: break
    if n==0: out.write(f"{tag}\tNONE\t{url}\t{r.status_code} {len(html)}\n")
out.close()
