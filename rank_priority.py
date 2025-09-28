

from pathlib import Path
import pandas as pd
import numpy as np

OUT = Path("outputs")

def safe_div(a, b, default=np.nan):
    b = np.where(b==0, np.nan, b)
    return np.divide(a, b)

def stock_vor(row):
    # unit_margin unknown for union; approximate by revenue/clicks if available; else fallback 30
    # Prefer using suggested retail - cost, but not in union; keep simple/consistent
    unit_margin = 30.0
    velocity = row.get("velocity_score", np.nan)
    days_left = row.get("days_to_stockout", np.nan)
    if pd.isna(velocity) or pd.isna(days_left):
        return 0.0
    expected_offline_days = max(0.0, 7.0 - float(days_left))
    return float(velocity) * unit_margin * expected_offline_days

def price_vor(row):
    our = row.get("our_price", np.nan)
    gap = row.get("price_gap", np.nan)
    if pd.isna(our) or pd.isna(gap) or our <= 0:
        return 0.0
    severity = float(gap) / float(our)
    return severity * 10000.0

def ads_vor(row):
    spend = row.get("ad_spend", 0.0) or 0.0
    cr = row.get("conversion_rate", np.nan)
    if pd.isna(cr):
        return 0.0
    target = 0.05
    penalty = max(0.0, 1.0 - min(cr/target, 1.0))
    return float(spend) * penalty

def urgency_factor(row):
    t = row.get("type", "")
    if t == "stockout":
        d = row.get("days_to_stockout", np.nan)
        if pd.isna(d) or d <= 0:
            return 1.0
        return 1.0 / float(max(d, 1.0))
    return 1.0

def main():
    raw = pd.read_csv(OUT/"insights_raw.csv")
    df = raw.copy()

    # Compute Value at Risk by pillar
    df["value_at_risk"] = 0.0
    df.loc[df["type"]=="stockout","value_at_risk"]      = df.loc[df["type"]=="stockout"].apply(stock_vor, axis=1)
    df.loc[df["type"]=="price_undercut","value_at_risk"]= df.loc[df["type"]=="price_undercut"].apply(price_vor, axis=1)
    df.loc[df["type"]=="ad_performance","value_at_risk"]= df.loc[df["type"]=="ad_performance"].apply(ads_vor, axis=1)
    df.loc[df["type"]=="content_gap","value_at_risk"]   = 100.0

    # Urgency factor
    df["urgency_factor"] = df.apply(urgency_factor, axis=1)

    # Final score
    df["priority_score"] = df["value_at_risk"] * df["urgency_factor"]

    # Sort and write
    order_cols = [
        "date","sku","retailer","units_shipped","units_returned",
        "current_fba_inventory","velocity_score","days_to_stockout","type",
        "platform","our_price","competitor_price","price_gap",
        "week_ending","channel","impressions","clicks","conversions",
        "ad_spend","revenue","search_rank_avg","competitor_price_index",
        "conversion_rate","value_at_risk","urgency_factor","priority_score"
    ]
    for c in order_cols:
        if c not in df.columns:
            df[c] = ""

    df = df.sort_values("priority_score", ascending=False)
    df.to_csv(OUT/"actionable_insights.csv", index=False, columns=order_cols)
    print("Wrote: outputs/actionable_insights.csv (ranked)")

if __name__ == "__main__":
    main()
