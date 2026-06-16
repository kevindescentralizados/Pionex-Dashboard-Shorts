"""
collector/collect.py
Recolector principal para el dashboard de Pionex Shorts.
Lee los CSV de posiciones y fills desde la raiz del repo,
reconstruye las operaciones y genera site/data.json.
"""
import os
import sys
import json
import glob
import math
from datetime import datetime, timezone

import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STORE = os.path.join(ROOT, "store", "positions.jsonl")
SITE_DATA = os.path.join(ROOT, "site", "data.json")
LAST_UPDATE = os.path.join(ROOT, "site", "last_update.txt")
REBALANCE_ENTRIES = 20


# ── helpers ────────────────────────────────────────────────────────────────

def clean_symbol(sym: str) -> str:
    """BTCUSDT -> BTC, ETHUSDT_PERP -> ETH, etc."""
    for suffix in ("USDT_PERP", "USDT", "_PERP"):
        if sym.upper().endswith(suffix):
            return sym[: -len(suffix)]
    return sym


def load_jsonl(path: str) -> list:
    if not os.path.exists(path):
        return []
    recs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return recs


def save_jsonl(path: str, records: list):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def reconstruct_round_trips(fills: pd.DataFrame) -> list:
    """
    A partir de un DataFrame de fills (t, symbol, side, executed_qty,
    amount, price, fee, tax_id) reconstruye round-trips short:
    venta inicial + recompras = una posicion.
    Devuelve lista de dicts con close, symbol, first, n_ent,
    sell_qty, sell_amt, gross.
    """
    trips = []
    fills = fills.sort_values("t").copy()

    for symbol, grp in fills.groupby("symbol"):
        sells = grp[grp["side"].str.upper() == "SELL"].copy()
        buys = grp[grp["side"].str.upper() == "BUY"].copy()

        buy_pool = list(buys.itertuples())
        used_buy_idx = set()

        for s_row in sells.itertuples():
            qty_to_cover = float(s_row.executed_qty)
            trip_buys = []
            for b in buy_pool:
                if b.Index in used_buy_idx:
                    continue
                if b.t < s_row.t:
                    continue  # buy must come after sell (short)
                trip_buys.append(b)
                used_buy_idx.add(b.Index)
                qty_to_cover -= float(b.executed_qty)
                if qty_to_cover <= 1e-9:
                    break

            sell_qty = float(s_row.executed_qty)
            sell_amt = float(s_row.amount)
            buy_amt = sum(float(b.amount) for b in trip_buys)
            gross = sell_amt - buy_amt

            close_t = trip_buys[-1].t if trip_buys else s_row.t

            trips.append(dict(
                close=close_t,
                symbol=symbol,
                first="SELL",
                n_ent=len(trip_buys),
                sell_qty=sell_qty,
                sell_amt=sell_amt,
                gross=round(gross, 6),
            ))

    return trips


# ── ingest desde CSV ────────────────────────────────────────────────────────

def _detect(files, must_have):
    for fp in files:
        try:
            cols = pd.read_csv(fp, nrows=1).columns
            if all(c in cols for c in must_have):
                return fp
        except Exception:
            continue
    return None


def seed_from_csv(root: str = ROOT) -> list:
    """Lee los CSV de la raiz y devuelve lista de registros de posiciones."""
    files = glob.glob(os.path.join(root, "*.csv"))

    pos_fp = _detect(files, ["position_side", "pnl", "funding_fee"])
    fills_fp = _detect(files, ["executed_qty", "side", "tax_id"])

    if not pos_fp or not fills_fp:
        print(f"[collect] CSV no encontrados en {root}. pos={pos_fp} fills={fills_fp}")
        return []

    print(f"[collect] Posiciones: {os.path.basename(pos_fp)}")
    print(f"[collect] Fills:      {os.path.basename(fills_fp)}")

    pos = pd.read_csv(pos_fp)
    pos = pos[pos["position_side"] == "short"].copy().reset_index(drop=True)
    pos["acct"] = pos["position_id"].str.split("_").str[0]
    pos["ot"] = pd.to_datetime(pos["open_time"])
    pos["ct"] = pd.to_datetime(pos["close_time"])

    raw = pd.read_csv(fills_fp)
    raw = raw.rename(columns={"date(UTC+0)": "date"})
    if "state" in raw.columns:
        raw = raw[raw["state"] == "FILLED"]
    if "market_type" in raw.columns:
        raw = raw[raw["market_type"] == "Futures USDT"]
    raw["t"] = pd.to_datetime(raw["date"])
    for c in ("executed_qty", "amount", "price"):
        raw[c] = pd.to_numeric(raw[c])
    if "fee" not in raw.columns:
        raw["fee"] = 0.0

    trips = reconstruct_round_trips(
        raw[["t", "symbol", "side", "executed_qty", "amount", "price", "fee", "tax_id"]]
    )
    T = pd.DataFrame(trips) if trips else pd.DataFrame(
        columns=["close","symbol","first","n_ent","sell_qty","sell_amt","gross"]
    )
    if not T.empty:
        T["close"] = pd.to_datetime(T["close"])

    used, recs = set(), []
    for _, r in pos.iterrows():
        cap = n = avgpx = None
        err = np.nan

        if not T.empty:
            cand = T[(T["symbol"] == r["symbol"]) & (T["first"] == "SELL")]
            cand = cand[~cand.index.isin(used)]
            if cand.empty:
                cand = T[(T["symbol"] == r["symbol"])]
                cand = cand[~cand.index.isin(used)]

            if not cand.empty:
                j = (cand["close"] - r["ct"]).abs().idxmin()
                used.add(j)
                t = T.loc[j]
                cap = float(t["sell_amt"])
                n = int(t["n_ent"])
                avgpx = float(t["sell_amt"] / t["sell_qty"]) if t["sell_qty"] else None
                err = abs(float(t["gross"]) - float(r["pnl"]))

        rebalance = (r["acct"] == "43112881807336") or (n is not None and n >= REBALANCE_ENTRIES)

        if cap is None or np.isnan(err):
            estado = "Revisar"
        elif rebalance:
            estado = "Rebalanceo"
        elif err > 5:
            estado = "Revisar"
        else:
            estado = "OK"

        gross = float(r["pnl"])
        fee = float(r["fee"])
        fund = float(r["funding_fee"])
        recs.append(dict(
            pos_id=r["position_id"],
            symbol=r["symbol"],
            activo=clean_symbol(r["symbol"]),
            side="short",
            open_time=r["ot"].strftime("%Y-%m-%d %H:%M:%S"),
            close_time=r["ct"].strftime("%Y-%m-%d %H:%M:%S"),
            gross=round(gross, 6),
            fee=round(fee, 6),
            funding=round(fund, 6),
            net=round(gross + fee + fund, 6),
            capital=(round(cap, 6) if cap is not None else None),
            n_entries=n,
            avg_entry_px=(round(avgpx, 10) if avgpx is not None else None),
            estado=estado,
            source="seed",
        ))

    # Fusionar con store existente (no sobreescribir fuente API)
    existing = [p for p in load_jsonl(STORE) if p.get("source") != "seed"]
    all_recs = recs + existing
    save_jsonl(STORE, all_recs)
    print(f"[collect] {len(recs)} posiciones sembradas, {len(existing)} existentes conservadas.")
    return all_recs


# ── build data.json ─────────────────────────────────────────────────────────

def build_data_json(records: list) -> dict:
    """Construye la estructura de data.json a partir de la lista de posiciones."""
    if not records:
        return {"empty": True}

    df = pd.DataFrame(records)
    df["ct"] = pd.to_datetime(df["close_time"])
    df["date"] = df["ct"].dt.strftime("%Y-%m-%d")
    df["net"] = pd.to_numeric(df["net"])
    df["gross"] = pd.to_numeric(df["gross"])
    df["fee"] = pd.to_numeric(df["fee"])
    df["funding"] = pd.to_numeric(df["funding"])

    # KPIs globales
    total_net = df["net"].sum()
    total_gross = df["gross"].sum()
    total_fee = df["fee"].sum()
    total_fund = df["funding"].sum()
    wins = int((df["net"] > 0).sum())
    losses = int((df["net"] <= 0).sum())
    n_ops = len(df)
    win_rate = round(wins / n_ops * 100, 2) if n_ops else 0

    # Rentabilidad media por op (solo las que tienen capital)
    has_cap = df[df["capital"].notna() & (df["capital"] > 0)].copy()
    if len(has_cap):
        has_cap["pct"] = has_cap["net"] / has_cap["capital"] * 100
        avg_pct = round(has_cap["pct"].mean(), 4)
    else:
        avg_pct = 0.0

    # Dias operados
    daily = df.groupby("date").agg(
        net=("net", "sum"),
        gross=("gross", "sum"),
        fee=("fee", "sum"),
        nops=("net", "count"),
        wins=("net", lambda x: int((x > 0).sum())),
    ).reset_index()

    ndays = len(daily)
    avg_daily = round(total_net / ndays, 4) if ndays else 0

    best_row = daily.loc[daily["net"].idxmax()]
    worst_row = daily.loc[daily["net"].idxmin()]

    # Construccion de dias con ops
    days_out = []
    for _, day_row in daily.sort_values("date").iterrows():
        day_ops_df = df[df["date"] == day_row["date"]].copy()
        # pct diario (capital total del dia)
        day_cap = day_ops_df["capital"].dropna()
        day_pct = round(day_row["net"] / day_cap.sum() * 100, 2) if day_cap.sum() > 0 else None

        ops_out = []
        for _, op in day_ops_df.sort_values("ct").iterrows():
            op_cap = op["capital"] if pd.notna(op["capital"]) and op["capital"] > 0 else None
            op_pct = round(op["net"] / op_cap * 100, 2) if op_cap else None
            ops_out.append(dict(
                activo=op["activo"],
                est=op["estado"],
                n=int(op["n_entries"]) if pd.notna(op.get("n_entries")) else None,
                net=round(float(op["net"]), 2),
                pct=op_pct,
            ))

        days_out.append(dict(
            date=day_row["date"],
            net=round(float(day_row["net"]), 2),
            pct=day_pct,
            nops=int(day_row["nops"]),
            wins=int(day_row["wins"]),
            ops=ops_out,
        ))

    return dict(
        empty=False,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        kpi=dict(
            total_net=round(float(total_net), 2),
            total_gross=round(float(total_gross), 2),
            total_fee=round(float(total_fee), 2),
            total_fund=round(float(total_fund), 2),
            win_rate=win_rate,
            wins=wins,
            losses=losses,
            n_ops=n_ops,
            avg_pct=avg_pct,
            avg_daily=avg_daily,
            ndays=ndays,
            best=dict(date=str(best_row["date"]), net=round(float(best_row["net"]), 2)),
            worst=dict(date=str(worst_row["date"]), net=round(float(worst_row["net"]), 2)),
        ),
        days=days_out,
    )


# ── main ────────────────────────────────────────────────────────────────────

def main():
    print("[collect] Iniciando recoleccion...")

    # 1. Sembrar/actualizar desde CSV
    records = seed_from_csv(ROOT)

    if not records:
        # Intentar cargar lo que haya en el store
        records = load_jsonl(STORE)
        if not records:
            print("[collect] Sin datos. Asegurate de tener los CSV en la raiz del repo.")
            data = {"empty": True}
        else:
            data = build_data_json(records)
    else:
        data = build_data_json(records)

    # 2. Guardar site/data.json
    os.makedirs(os.path.dirname(SITE_DATA), exist_ok=True)
    with open(SITE_DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    print(f"[collect] site/data.json generado ({os.path.getsize(SITE_DATA):,} bytes)")

    # 3. Guardar timestamp
    ts = data.get("generated_at", "")
    with open(LAST_UPDATE, "w") as f:
        f.write(ts)
    print(f"[collect] Timestamp: {ts}")


if __name__ == "__main__":
    main()
