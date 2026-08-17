#!/usr/bin/env python3
import csv
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.request import Request, urlopen

RPC_URL = "https://xrplcluster.com"
OUT = Path("snapshot-output")
HOLDERS_CSV = OUT / "holders.csv"

TOKEN_ISSUER = "rpCB8upQziQR6P5YbHnZZAqqTMePQ8pCTR"
TOKEN_CURRENCY = "245852504D414E00000000000000000000000000"


def rpc(method, params, timeout=45):
    payload = json.dumps({"method": method, "params": [params]}).encode("utf-8")
    req = Request(
        RPC_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SkyFall-Trustline-Intersection/1.0",
        },
        method="POST",
    )
    with urlopen(req, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8", "replace"))
    result = body.get("result", {})
    if result.get("status") == "error" or result.get("error"):
        raise RuntimeError(f"XRPL RPC error: {result.get('error')} {result.get('error_message', '')}".strip())
    return result


def decimal_or_zero(value):
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(0)


def fetch_issuer_lines():
    lines = []
    marker = None
    while True:
        params = {
            "account": TOKEN_ISSUER,
            "ledger_index": "validated",
            "limit": 400,
        }
        if marker is not None:
            params["marker"] = marker
        result = rpc("account_lines", params)
        lines.extend(result.get("lines", []))
        marker = result.get("marker")
        if not marker:
            break
    return lines


def main():
    if not HOLDERS_CSV.exists():
        raise SystemExit(f"Missing {HOLDERS_CSV}; run nft_snapshot.py first")

    with HOLDERS_CSV.open(newline="", encoding="utf-8") as f:
        holders = list(csv.DictReader(f))

    candidates = [
        row for row in holders
        if row.get("is_known_dev_wallet", "").lower() != "true"
        and row.get("is_collection_issuer", "").lower() != "true"
    ]

    all_lines = fetch_issuer_lines()
    target_lines = {
        line.get("account"): line
        for line in all_lines
        if line.get("currency") == TOKEN_CURRENCY and line.get("account")
    }

    rows = []
    with_trustline = 0
    without_trustline = 0
    total_nfts_with_trustline = 0
    total_nfts_without_trustline = 0

    for holder in candidates:
        wallet = holder["wallet"]
        nft_count = int(holder.get("nft_count") or 0)
        line = target_lines.get(wallet)
        has = line is not None
        if has:
            with_trustline += 1
            total_nfts_with_trustline += nft_count
        else:
            without_trustline += 1
            total_nfts_without_trustline += nft_count

        issuer_view_balance = decimal_or_zero(line.get("balance")) if line else Decimal(0)
        # account_lines is queried from the issuer's perspective, so the peer's
        # token balance is normally the sign-inverse of the issuer-side balance.
        holder_balance = -issuer_view_balance if line else Decimal(0)
        holder_limit = decimal_or_zero(line.get("limit_peer")) if line else Decimal(0)
        frozen_by_issuer = bool(line.get("freeze")) if line else False
        frozen_by_holder = bool(line.get("freeze_peer")) if line else False

        rows.append({
            "wallet": wallet,
            "nft_count": nft_count,
            "collections": holder.get("collections", ""),
            "has_xrpman_trustline": "YES" if has else "NO",
            "xrpman_balance": format(holder_balance, "f") if has else "",
            "holder_trust_limit": format(holder_limit, "f") if has else "",
            "issuer_freeze": "YES" if frozen_by_issuer else "NO",
            "holder_freeze": "YES" if frozen_by_holder else "NO",
        })

    rows.sort(key=lambda r: (r["has_xrpman_trustline"] != "YES", -r["nft_count"], r["wallet"]))

    fieldnames = [
        "wallet", "nft_count", "collections", "has_xrpman_trustline",
        "xrpman_balance", "holder_trust_limit", "issuer_freeze", "holder_freeze",
    ]
    with (OUT / "nft_holders_xrpman_trustlines.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    summary = {
        "token_issuer": TOKEN_ISSUER,
        "token_currency_hex": TOKEN_CURRENCY,
        "candidate_wallets": len(candidates),
        "with_trustline": with_trustline,
        "without_trustline": without_trustline,
        "percent_with_trustline": round((with_trustline / len(candidates) * 100), 2) if candidates else 0,
        "nfts_held_by_wallets_with_trustline": total_nfts_with_trustline,
        "nfts_held_by_wallets_without_trustline": total_nfts_without_trustline,
        "total_issuer_account_lines": len(all_lines),
        "total_xrpman_trustlines_on_issuer": len(target_lines),
    }
    (OUT / "trustline_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print("TRUSTLINE_INTERSECTION_COMPLETE")
    for key, value in summary.items():
        print(f"{key.upper()} {value}")
    print("TOP_WITH_TRUSTLINE")
    for row in [r for r in rows if r["has_xrpman_trustline"] == "YES"][:40]:
        print(f"YES | {row['wallet']} | nfts={row['nft_count']} | balance={row['xrpman_balance']} | {row['collections']}")
    print("TOP_WITHOUT_TRUSTLINE")
    for row in [r for r in rows if r["has_xrpman_trustline"] == "NO"][:40]:
        print(f"NO | {row['wallet']} | nfts={row['nft_count']} | {row['collections']}")


if __name__ == "__main__":
    main()
