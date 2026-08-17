#!/usr/bin/env python3
import re
from urllib.request import Request, urlopen
from urllib.parse import quote

HEADERS={"User-Agent":"Mozilla/5.0 SkyFall-NFT-Resolver/1.0","Accept":"application/json,text/html,*/*"}
BASE="https://ladycafe.io"
SLUG="three-legends-boo-044d875b"

def text(url, timeout=25):
    req=Request(url,headers=HEADERS)
    with urlopen(req,timeout=timeout) as r:
        return r.read().decode("utf-8","replace")

def show(label,url):
    try:
        raw=text(url)
        print("FETCH",label,url,"bytes",len(raw),"body",raw[:30000].replace("\n"," "))
        return raw
    except Exception as e:
        print("ERR",label,url,repr(e)); return ""

for q in ["three legends","boo","redcandlekiller","mr zamn"]:
    show("SEARCH",f"{BASE}/api/search?q={quote(q)}")
for u in [f"{BASE}/api/collections/published",f"{BASE}/api/collections/paginated?page=1&limit=100",f"{BASE}/api/collections",f"{BASE}/api/nfts/paginated?page=1&limit=100"]:
    show("API",u)
chunk=show("DETAIL_JS",f"{BASE}/assets/collection-detail--E0sPwKc.js")
if chunk:
    for m in sorted(set(re.findall(r'["\'`]([^"\'`]*?/api/[^"\'`]+)["\'`]',chunk))): print("DETAIL_API_REF",m[:1000])
    for needle in ["/api/collections/","queryKey","collectionId","slug"]:
        start=0
        for _ in range(12):
            i=chunk.find(needle,start)
            if i<0: break
            print("DETAIL_CTX",chunk[max(0,i-700):i+1400].replace("\n"," "))
            start=i+len(needle)
for ident in [SLUG,"044d875b"]:
    for path in [f"/api/collections/{ident}",f"/api/collections/slug/{ident}",f"/api/collections/{ident}/nfts",f"/api/nfts?collectionId={quote(ident)}"]:
        show("DETAIL_TRY",BASE+path)
