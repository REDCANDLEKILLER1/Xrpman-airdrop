#!/usr/bin/env python3
import csv, json, time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.request import Request, urlopen

API = "https://api.xrpldata.com/api/v1"
OUT = Path("snapshot-output")
OUT.mkdir(exist_ok=True)

R9 = "r9nepSD5tvQUCA4qQAJJDAoBB3j1gf4ibL"
RDG = "rDg6Q7mTBsVo35cNf6vUSx8uEsDD8Hw7B2"

COLLECTIONS = [
    {"name":"XRPMan Multiverse","issuer":R9,"taxon":0},
    {"name":"XRPMan: The OG Chronicles","issuer":R9,"taxon":1},
    {"name":"XRPMan — Villain Collection #1","issuer":"rwnWEMHD1CW7eZdWcZb1ssT4pPkZaP3qzy","taxon":1},
    {"name":"Three Legends — Boo Edition","issuer":"rhygvDyyaNSfPdsN8UzGTENBYXJyxy4eKw","taxon":1717047013},
    {"name":"Three Legends — Spiffy Edition","issuer":"rpGdCA9tSVuDvJSKHgQnBrqLahUrBpcyH2","taxon":777},
    {"name":"XRPMan: Born in the Swamp","issuer":R9,"taxon":21},
    {"name":"XRPL After Dark","issuer":R9,"taxon":589},
]
KNOWN_DEV_WALLETS = {R9, RDG}
COLLECTION_ISSUERS = {c["issuer"] for c in COLLECTIONS}

def get_json(url, timeout=30):
    req = Request(url, headers={"User-Agent":"Mozilla/5.0 SkyFall-NFT-Snapshot/1.1","Accept":"application/json"})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def fetch_group(issuer, taxon):
    data = get_json(f"{API}/xls20-nfts/issuer/{issuer}/taxon/{taxon}")
    return data.get("data", {}).get("nfts", [])

def main():
    all_rows = []
    summaries = []
    for c in COLLECTIONS:
        nfts = fetch_group(c["issuer"], c["taxon"])
        owners = Counter(n.get("Owner") for n in nfts if n.get("Owner"))
        summaries.append({**c, "nfts":len(nfts), "unique_owners":len(owners)})
        for n in nfts:
            owner = n.get("Owner")
            if not owner:
                continue
            all_rows.append({
                "owner":owner,
                "collection":c["name"],
                "issuer":c["issuer"],
                "taxon":c["taxon"],
                "nftoken_id":n.get("NFTokenID", ""),
            })
        time.sleep(0.20)

    by_owner = defaultdict(lambda: {"total":0,"collections":Counter()})
    for row in all_rows:
        x = by_owner[row["owner"]]
        x["total"] += 1
        x["collections"][row["collection"]] += 1

    holder_rows = []
    for owner, x in by_owner.items():
        holder_rows.append({
            "wallet":owner,
            "nft_count":x["total"],
            "collections":"; ".join(f"{k}:{v}" for k,v in sorted(x["collections"].items())),
            "is_known_dev_wallet": owner in KNOWN_DEV_WALLETS,
            "is_collection_issuer": owner in COLLECTION_ISSUERS,
        })
    holder_rows.sort(key=lambda r:(-r["nft_count"], r["wallet"]))

    with open(OUT/"holders.csv", "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["wallet","nft_count","collections","is_known_dev_wallet","is_collection_issuer"])
        w.writeheader(); w.writerows(holder_rows)
    with open(OUT/"nfts.csv", "w", newline="", encoding="utf-8") as f:
        w=csv.DictWriter(f, fieldnames=["owner","collection","issuer","taxon","nftoken_id"])
        w.writeheader(); w.writerows(all_rows)

    payload = {
        "status":"complete",
        "snapshot_scope":"7 official XRPMan NFT collections from xrpman.xyz/media",
        "resolved_collections":summaries,
        "unique_wallets":len(holder_rows),
        "unique_external_wallets_excluding_known_dev_wallets":sum(1 for r in holder_rows if not r["is_known_dev_wallet"]),
        "unique_airdrop_candidates_excluding_dev_and_collection_issuer_wallets":sum(1 for r in holder_rows if not r["is_known_dev_wallet"] and not r["is_collection_issuer"]),
        "total_current_nfts":len(all_rows),
        "holders":holder_rows,
    }
    (OUT/"snapshot.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print("SNAPSHOT_STATUS complete")
    print("RESOLVED_COLLECTIONS", len(COLLECTIONS))
    for s in summaries:
        print(f"COLLECTION | {s['name']} | issuer={s['issuer']} | taxon={s['taxon']} | nfts={s['nfts']} | owners={s['unique_owners']}")
    print("UNIQUE_WALLETS", payload["unique_wallets"])
    print("EXTERNAL_WALLETS_EX_DEV", payload["unique_external_wallets_excluding_known_dev_wallets"])
    print("AIRDROP_CANDIDATES_EX_DEV_AND_ISSUERS", payload["unique_airdrop_candidates_excluding_dev_and_collection_issuer_wallets"])
    print("TOTAL_NFTS", payload["total_current_nfts"])
    print("TOP_HOLDERS")
    for r in holder_rows[:120]:
        print(f"HOLDER | {r['wallet']} | {r['nft_count']} | {r['collections']} | dev={r['is_known_dev_wallet']} | issuer={r['is_collection_issuer']}")

if __name__ == "__main__":
    main()
