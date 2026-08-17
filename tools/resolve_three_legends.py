#!/usr/bin/env python3
import re
from urllib.request import Request, urlopen
from urllib.parse import quote, urljoin

HEADERS={"User-Agent":"Mozilla/5.0 SkyFall-NFT-Resolver/1.0","Accept":"application/json,text/html,*/*"}
TERMS=("three legends","3 legends","spiffy","boo edition","redcandlekiller","mr zamn","mrzamn","three-legends-boo-044d875b")
ISSUERS=["rDg6Q7mTBsVo35cNf6vUSx8uEsDD8Hw7B2","r9nepSD5tvQUCA4qQAJJDAoBB3j1gf4ibL"]
MARKETS={
"boo":"https://ladycafe.io/collection/three-legends-boo-044d875b",
"spiffy":"https://imcollectibles.io/collections/3-legends-redcandlekiller-mrzamn-spiffy-edition-777/",
}

def text(url, timeout=25):
    req=Request(url,headers=HEADERS)
    with urlopen(req,timeout=timeout) as r:
        return r.read().decode("utf-8","replace")

def dump_hits(label, raw, max_hits=20):
    low=raw.lower(); hits=[]
    for term in TERMS:
        pos=0
        while True:
            i=low.find(term,pos)
            if i<0: break
            hits.append(raw[max(0,i-500):min(len(raw),i+1100)].replace("\n"," "))
            pos=i+len(term)
            if len(hits)>=max_hits: break
        if len(hits)>=max_hits: break
    print(f"HITS {label} count={len(hits)}")
    for h in hits: print("CTX",h[:1600])

for issuer in ISSUERS:
    url=f"https://api.xrpldata.com/api/v1/xls20-nfts/issuer/{issuer}"
    try:
        raw=text(url)
        print("FETCH",url,"bytes",len(raw),"head",raw[:250].replace("\n"," "))
        dump_hits("issuer:"+issuer, raw)
    except Exception as e: print("ERR",url,repr(e))

for label,url in MARKETS.items():
    try:
        raw=text(url)
        print("MARKET",label,"bytes",len(raw),"url",url)
        dump_hits("market:"+label,raw)
        scripts=[urljoin(url,s) for s in re.findall(r'<script[^>]+src=["\']([^"\']+)',raw,re.I)]
        print("SCRIPTS",label,len(scripts))
        for s in scripts: print("SCRIPT",label,s)
        if label=="boo":
            for s in scripts:
                if s.startswith("data:") or "googletag" in s or "google" in s: continue
                try:
                    js=text(s)
                    print("JS",s,"bytes",len(js))
                    low=js.lower()
                    if any(k in low for k in ("three-legends-boo","supabase","collection","xrpl","nft")):
                        dump_hits("boo-js:"+s,js,30)
                        for pat in [r'https?://[^"\'`\\ ]+', r'["\']([^"\']*(?:api|supabase|collection|nft|xrpl)[^"\']*)["\']']:
                            vals=set(re.findall(pat,js,re.I))
                            for v in sorted(vals):
                                if isinstance(v,tuple): v=v[0]
                                if len(v)<700 and any(k in v.lower() for k in ("api","supabase","collection","nft","xrpl")):
                                    print("JSREF",v[:700])
                except Exception as e: print("JSERR",s,repr(e))
    except Exception as e: print("ERR market",label,repr(e))

for q in ["three legends","spiffy","boo","redcandlekiller","mrzamn"]:
    for param in ["search","q","name"]:
        url=f"https://api.xrpl.to/v1/nft/collections?{param}={quote(q)}&limit=100&page=1"
        try:
            raw=text(url)
            if any(t in raw.lower() for t in ("spiffy","three legends","redcandlekiller","boo edition","mrzamn")):
                print("CATALOG_MATCH",url,raw[:12000])
        except Exception: pass
