#!/usr/bin/env python3
import json, re
from urllib.request import Request, urlopen
from urllib.parse import quote

HEADERS={"User-Agent":"Mozilla/5.0 SkyFall-NFT-Resolver/1.0","Accept":"application/json,text/html,*/*"}
TERMS=("three legends","3 legends","spiffy","boo edition","redcandlekiller","mr zamn","mrzamn")
ISSUERS=["rDg6Q7mTBsVo35cNf6vUSx8uEsDD8Hw7B2","r9nepSD5tvQUCA4qQAJJDAoBB3j1gf4ibL"]
MARKETS={
"boo":"https://ladycafe.io/collection/three-legends-boo-044d875b",
"spiffy":"https://imcollectibles.io/collections/3-legends-redcandlekiller-mrzamn-spiffy-edition-777/",
}

def text(url, timeout=30):
    req=Request(url,headers=HEADERS)
    with urlopen(req,timeout=timeout) as r:
        return r.read().decode("utf-8","replace")

def dump_hits(label, raw):
    low=raw.lower()
    hits=[]
    for term in TERMS:
        pos=0
        while True:
            i=low.find(term,pos)
            if i<0: break
            hits.append(raw[max(0,i-500):min(len(raw),i+900)].replace("\n"," "))
            pos=i+len(term)
            if len(hits)>=20: break
        if len(hits)>=20: break
    print(f"HITS {label} count={len(hits)}")
    for h in hits:
        print("CTX",h[:1400])

# 1) Inspect issuer-level XRPLData payloads for any Three Legends metadata/name/URI.
for issuer in ISSUERS:
    for url in [
        f"https://api.xrpldata.com/api/v1/xls20-nfts/issuer/{issuer}",
        f"https://api.xrpl.to/v1/nft/issuer/{issuer}?page=1&limit=500",
    ]:
        try:
            raw=text(url)
            print("FETCH",url,"bytes",len(raw),"head",raw[:250].replace("\n"," "))
            dump_hits("issuer:"+issuer, raw)
        except Exception as e:
            print("ERR",url,repr(e))

# 2) Inspect marketplace HTML and script/API references near collection names.
for label,url in MARKETS.items():
    try:
        raw=text(url)
        print("MARKET",label,"bytes",len(raw),"url",url)
        dump_hits("market:"+label,raw)
        # Print likely API/backend URLs and script sources, deduped.
        urls=set(re.findall(r'https?://[^"\'<>\\ ]+',raw))
        rel=set(re.findall(r'["\']([^"\']*(?:api|backend|collection|nft)[^"\']*)["\']',raw,re.I))
        for u in sorted(urls):
            if any(k in u.lower() for k in ("api","backend","nft","collection")):
                print("URL",label,u[:1000])
        for u in sorted(rel):
            if len(u)<500:
                print("REL",label,u)
    except Exception as e:
        print("ERR market",label,repr(e))

# 3) Search XRPL.to collection catalogue with likely query parameter variants.
for q in ["three legends","spiffy","boo","redcandlekiller","mrzamn"]:
    for param in ["search","q","name"]:
        url=f"https://api.xrpl.to/v1/nft/collections?{param}={quote(q)}&limit=100&page=1"
        try:
            raw=text(url)
            if any(t in raw.lower() for t in ("spiffy","three legends","redcandlekiller","boo edition","mrzamn")):
                print("CATALOG_MATCH",url,raw[:12000])
        except Exception as e:
            pass
