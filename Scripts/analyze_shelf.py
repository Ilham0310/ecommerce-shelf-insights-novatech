
from pathlib import Path
import json
import pandas as pd

RAW = Path(".")
OUT = Path("outputs")
OUT.mkdir(exist_ok=True)

def load_csv(name: str) -> pd.DataFrame:
    return pd.read_csv(RAW / name)

def load_json(name: str) -> dict:
    with open(RAW / name) as f:
        return json.load(f)

# ---------- Pillar 1: Stock ----------
def detect_stock_issues(inv: pd.DataFrame, catalog: pd.DataFrame) -> pd.DataFrame:
    df = inv.copy()
    df["velocity_score"] = df["velocity_score"].fillna(0)
    df["current_fba_inventory"] = df["current_fba_inventory"].fillna(0)
    df["days_to_stockout"] = (
        df["current_fba_inventory"] / df["velocity_score"].replace(0, pd.NA)
    )
    # Join margin estimate from catalog (suggested_retail - cost_basis)
    cat = catalog[["item_code", "suggested_retail", "cost_basis"]].rename(
        columns={"item_code":"sku"}
    )
    df = df.merge(cat, on="sku", how="left")
    df["unit_margin_est"] = (df["suggested_retail"] - df["cost_basis"]).clip(lower=0)
    # Keep rows at risk: inventory <= 5 and velocity >= 2
    at_risk = df.loc[
        (df["current_fba_inventory"] <= 5) & (df["velocity_score"] >= 2)
    ].copy()
    at_risk["type"] = "stockout"
    # Normalize columns for union
    norm_cols = {
        "date":"date", "sku":"sku", "retailer":"retailer",
        "units_shipped":"units_shipped", "units_returned":"units_returned",
        "current_fba_inventory":"current_fba_inventory", "velocity_score":"velocity_score",
        "days_to_stockout":"days_to_stockout", "type":"type",
        # price / ads fields absent in stock pillar -> fill later
    }
    at_risk = at_risk[list(norm_cols.keys())].rename(columns=norm_cols)
    return at_risk

# ---------- Pillar 2: Price ----------
def detect_price_issues(snapshot: dict) -> pd.DataFrame:
    records = []
    # Amazon
    for p in snapshot.get("platforms", {}).get("amazon", {}).get("products", []):
        asin = p.get("asin")
        our_price = p.get("list_price") or p.get("current_price")
        buy_box_winner = p.get("buy_box_winner")
        competitor_price = p.get("buy_box_price") if buy_box_winner != "NovaTech Official" else None
        if asin and our_price and competitor_price and competitor_price < our_price:
            records.append({
                "sku": asin,
                "platform": "amazon",
                "our_price": our_price,
                "competitor_price": competitor_price,
                "price_gap": round(our_price - competitor_price, 2),
                "type": "price_undercut"
            })
    # Walmart
    for p in snapshot.get("platforms", {}).get("walmart", {}).get("products", []):
        wid = p.get("walmart_id")
        our_price = p.get("online_price")
        competitor_price = p.get("lowest_competitor_price")
        if wid and our_price and competitor_price and competitor_price < our_price:
            records.append({
                "sku": wid,
                "platform": "walmart",
                "our_price": our_price,
                "competitor_price": competitor_price,
                "price_gap": round(our_price - competitor_price, 2),
                "type": "price_undercut"
            })
    return pd.DataFrame(records)

# ---------- Pillar 3: Ads ----------
def detect_ad_issues(perf: pd.DataFrame) -> pd.DataFrame:
    df = perf.copy().rename(columns={"identifier":"sku"})
    df["conversion_rate"] = df["conversions"] / df["clicks"].replace(0, 1)
    median_spend = df["ad_spend"].median()
    hit = df.loc[(df["ad_spend"] > median_spend) & (df["conversion_rate"] < 0.05)].copy()
    hit["type"] = "ad_performance"
    # Normalize to common schema
    keep = [
        "sku","week_ending","channel","impressions","clicks","conversions",
        "ad_spend","revenue","search_rank_avg","competitor_price_index",
        "conversion_rate","type"
    ]
    return hit[keep]

# ---------- Pillar 4: Content ----------
def detect_content_issues(catalog: pd.DataFrame) -> pd.DataFrame:
    df = catalog.copy()
    df["missing_description"] = (
        df["product_description"].isna() | (df["product_description"].str.strip()=="")
    )
    miss = df.loc[df["missing_description"]].copy()
    miss["type"] = "content_gap"
    # Normalize minimal fields
    out = miss.rename(columns={"item_code":"sku"})[["sku","type"]]
    return out

# ---------- Union & save ----------
def main():
    inv = load_csv("inventory_movements.csv")
    catalog = load_csv("internal_catalog_dump.csv")
    perf = load_csv("performance_metrics.csv")
    snap = load_json("marketplace_snapshot.json")

    stock_df = detect_stock_issues(inv, catalog)
    price_df = detect_price_issues(snap)
    ad_df = detect_ad_issues(perf)
    content_df = detect_content_issues(catalog)

    # Save pillar outputs
    if not stock_df.empty:   stock_df.to_csv(OUT/"stock_issues.csv", index=False)
    if not price_df.empty:   price_df.to_csv(OUT/"price_issues.csv", index=False)
    if not ad_df.empty:      ad_df.to_csv(OUT/"ad_issues.csv", index=False)
    if not content_df.empty: content_df.to_csv(OUT/"content_issues.csv", index=False)

    # Build normalized union with all requested columns
    cols = [
        "date","sku","retailer","units_shipped","units_returned",
        "current_fba_inventory","velocity_score","days_to_stockout","type",
        "platform","our_price","competitor_price","price_gap",
        "week_ending","channel","impressions","clicks","conversions",
        "ad_spend","revenue","search_rank_avg","competitor_price_index","conversion_rate"
    ]
    frames = []
    for df in (stock_df, price_df, ad_df, content_df):
        if df is None or df.empty: continue
        tmp = pd.DataFrame(columns=cols)
        # Align columns by name overlap
        for c in set(df.columns).intersection(cols):
            tmp[c] = df[c]
        frames.append(tmp)

    if frames:
        unified = pd.concat(frames, ignore_index=True)
        unified.to_csv(OUT/"insights_raw.csv", index=False)
        print("Wrote: outputs/insights_raw.csv")
    else:
        print("No insights detected. Check inputs.")

if __name__ == "__main__":
    main()
