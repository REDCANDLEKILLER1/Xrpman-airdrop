#!/usr/bin/env python3
import csv, json, re, time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.xrpldata.com/api/v1"
OUT = Path("snapshot-output")
OUT.mkdir(exist_ok=True)

R9 = "r9nepSD5tvQUCA4qQAJJDAoBB3j1gf4ibL"
RDG = "rDg6Q7mTBsVo35cNf6vUSx8uEsDD8Hw7B2"
VILLAIN_ISSUER = "rwnWEMHD1CW7eZdWcZb1ssT4pPkZaP3qzy"
VILLAIN_ANCHOR = "000A1F40639335DD467D42C5FE4413986565CDAA061F874908CF040605ACCE6C"

collections = [
    {"name":"XRPMan Multiverse","issuer":R9,"taxon":0},
    {"name":"XRPMan: The OG Chronicles","issuer":R9,"taxon":1},
    {"name":"XRPMan: Born in the Swamp","issuer":R9,"taxon":21},
    {"name":"XRPL After Dark","issuer":R9,"taxon":589},
]

market_pages = {
    "Three Legends — Boo Edition":"https://ladycafe.io/collection/three-legends-boo-044d875b",
    "Three Legends — Spiffy Edition":"https://imcollectibles.io/collections/3-legends-redcandlekiller-mrzamn-spiffy-edition-777/",
}

def get_text(url, timeout=30):
    req = Request(url, headers={"User-Agent":"Mozilla/5.0 SkyFall-NFT-Snapshot/1.0","Accept":"application/json,text/html,*/*"})
    with urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")

def get_json(url):
    return json.loads(get_text(url))

def fetch_group(issuer, taxon):
    data = get_json(f"{API}/xls20-nfts/issuer/{issuer}/taxon/{taxon}")
    return data.get("data", {}).get("nfts", [])

def fetch_nft(token_id):
    data = get_json(f"{API}/xls20-nfts/nft/{token_id}")
    return data.get("data", {}).get("nft")

def resolve_villain():
    anchor = fetch_nft(VILLAIN_ANCHOR)
    if not anchor:
        raise RuntimeError("Could not resolve Villain anchor NFT")
    return int(anchor["Taxon"])

def resolve_market_page(name, url):
    result = {"name":name,"url":url,"addresses":[],"token_ids":[],"resolved":[]}
    try:
        html = get_text(url)
        result["addresses"] = sorted(set(re.findall(r"r[1-9A-HJ-NP-Za-km-z]{24,34}", html)))
        result["token_ids"] = sorted(set(re.findall(r"\b[0-9A-F]{64}\b", html)))
        combos = set()
        for token_id in result["token_ids"][:25]:
            try:
                nft = fetch_nft(token_id)
                if nft:
                    combos.add((nft.get("Issuer"), int(nft.get("Taxon"))))
                time.sleep(0.15)
            except Exception:
                pass
        result["resolved"] = [{"issuer":a,"taxon":t} for a,t in sorted(combos)]
    except Exception as e:
        result["error"] = str(e)
    return result

def main():
    diagnostics = []
    villain_taxon = resolve_villain()
    collections.insert(2, {"name":"XRPMan — Villain Collection #1","issuer":VILLAIN_ISSUER,"taxon":villain_taxon})

    for name, url in market_pages.items():
        d = resolve_market_page(name, url)
        diagnostics.append(d)
        if len(d.get("resolved", [])) == 1:
            collections.append({"name":name, **d["resolved"][0]})

    all_rows = []
    summaries = []
    for c in collections:
        nfts = fetch_group(c["issuer"], c["taxon"])
        owners = Counter(n.get("Owner") for n in nfts if n.get("Owner"))
        summaries.append({
            **c,
            "nfts":len(nfts),
            "unique_owners":len(owners),
        })
        for n in nfts:
            owner = n.get("Owner")
            if not owner: continue
            all_rows.append({
                "owner":owner,
                "collection":c["name"],
                "issuer":c["issuer"],
                "taxon":c["taxon"],
                "nftoken_id":n.get("NFTokenID", ""),
            })
        time.sleep(0.25)

    by_owner = defaultdict(lambda: {"total":0,"collections":Counter(),"tokens":[]})
    for row in all_rows:
        x = by_owner[row["owner"]]
        x["total"] += 1
        x["collections"][row["collection"]] += 1
        x["tokens"].append(row["nftoken_id"])

    holder_rows = []
    for owner, x in by_owner.items():
        holder_rows.append({
            "wallet":owner,
            "nft_count":x["total"],
            "collections":"; ".join(f"{k}:{v}" for k,v in sorted(x["collections"].items())),
            "is_known_dev_wallet": owner in {R9,RDG},
        })
    holder_rows.sort(key=lambda r:(-r["nft_count"], r["wallet"]))

    with open(OUT/"holders.csv", "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["wallet","nft_count","collections","is_known_dev_wallet"])
        w.writeheader(); w.writerows(holder_rows)
    with open(OUT/"nfts.csv", "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["owner","collection","issuer","taxon","nftoken_id"])
        w.writeheader(); w.writerows(all_rows)
    payload = {
        "status":"complete" if len(collections)==7 else "partial",
        "resolved_collections":summaries,
        "unresolved_marketplace_diagnostics":diagnostics,
        "unique_wallets_in_resolved_collections":len(holder_rows),
        "unique_external_wallets_excluding_known_dev_wallets":sum(1 for r in holder_rows if not r["is_known_dev_wallet"]),
        "total_current_nfts_in_resolved_collections":len(all_rows),
        "holders":holder_rows,
    }
    (OUT/"snapshot.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("SNAPSHOT_STATUS", payload["status"])
    print("RESOLVED_COLLECTIONS", len(collections))
    for s in summaries:
        print(f"COLLECTION | {s['name']} | issuer={s['issuer']} | taxon={s['taxon']} | nfts={s['nfts']} | owners={s['unique_owners']}")
    print("UNIQUE_WALLETS", payload["unique_wallets_in_resolved_collections"])
    print("EXTERNAL_WALLETS_EX_DEV", payload["unique_external_wallets_excluding_known_dev_wallets"])
    print("TOTAL_NFTS", payload["total_current_nfts_in_resolved_collections"])
    print("TOP_HOLDERS")
    for r in holder_rows[:100]:
        print(f"HOLDER | {r['wallet']} | {r['nft_count']} | {r['collections']} | dev={r['is_known_dev_wallet']}")
    print("DIAGNOSTICS", json.dumps(diagnostics, ensure_ascii=False))

if __name__ == "__main__":
    main()
