"""
Semilla: ingiere tus exportaciones CSV de Pionex (que ya tienes) y deja toda la
historia guardada en store/positions.jsonl. Esto preserva TODO el histórico,
incluido lo que supera el límite de ~3 meses de la API.

Coloca en la carpeta seed/:
  - el export de POSICIONES (columnas: position_id, symbol, position_side,
    open_time, close_time, pnl, fee, funding_fee)   p.ej. position_futures.csv
  - el export de EJECUCIONES/fills (columnas: date(UTC+0), executed_qty, amount,
    price, side, symbol, ... tax_id)                p.ej. raw-trading-details.csv

Uso:  python collector/seed_from_csv.py
Reproduce exactamente las cifras validadas contra el extracto.
"""
import os
import glob
import sys
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from compute import clean_symbol, reconstruct_round_trips, save_jsonl, load_jsonl  # noqa

REBALANCE_ENTRIES = 20
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED_DIR = os.path.join(HERE, "seed")
STORE = os.path.join(HERE, "store", "positions.jsonl")


def _detect(files, must_have):
    for fp in files:
        try:
            cols = pd.read_csv(fp, nrows=1).columns
            if all(c in cols for c in must_have):
                return fp
        except Exception:
            continue
    return None


def run(seed_dir=SEED_DIR, store=STORE):
    files = glob.glob(os.path.join(seed_dir, "*.csv"))
    pos_fp = _detect(files, ["position_side", "pnl", "funding_fee"])
    fills_fp = _detect(files, ["executed_qty", "side", "tax_id"])
    if not pos_fp or not fills_fp:
        print(f"[seed] No encuentro los CSV en {seed_dir}. "
              f"posiciones={pos_fp} fills={fills_fp}")
        return []

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

    trips = reconstruct_round_trips(raw[["t", "symbol", "side", "executed_qty",
                                         "amount", "price", "fee", "tax_id"]])
    T = pd.DataFrame(trips)
    T["close"] = pd.to_datetime(T["close"])

    used, recs = set(), []
    for _, r in pos.iterrows():
        cand = T[(T["symbol"] == r["symbol"]) & (T["first"] == "SELL")]
        cand = cand[~cand.index.isin(used)]
        if len(cand) == 0:
            cand = T[(T["symbol"] == r["symbol"])]
            cand = cand[~cand.index.isin(used)]
        cap = n = avgpx = None
        err = np.nan
        if len(cand):
            j = (cand["close"] - r["ct"]).abs().idxmin()
            used.add(j); t = T.loc[j]
            cap = float(t["sell_amt"]); n = int(t["n_ent"])
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
        gross = float(r["pnl"]); fee = float(r["fee"]); fund = float(r["funding_fee"])
        recs.append(dict(
            pos_id=r["position_id"], symbol=r["symbol"], activo=clean_symbol(r["symbol"]),
            side="short",
            open_time=r["ot"].strftime("%Y-%m-%d %H:%M:%S"),
            close_time=r["ct"].strftime("%Y-%m-%d %H:%M:%S"),
            gross=round(gross, 6), fee=round(fee, 6), funding=round(fund, 6),
            net=round(gross + fee + fund, 6),
            capital=(round(cap, 6) if cap is not None else None),
            n_entries=n,
            avg_entry_px=(round(avgpx, 10) if avgpx is not None else None),
            estado=estado, source="seed",
        ))

    # fusionar con lo ya existente (los de la API no se tocan)
    existing = [p for p in load_jsonl(store) if p.get("source") != "seed"]
    save_jsonl(store, recs + existing)
    print(f"[seed] {len(recs)} posiciones short sembradas desde:")
    print(f"        posiciones: {os.path.basename(pos_fp)}")
    print(f"        fills:      {os.path.basename(fills_fp)}")
    return recs


if __name__ == "__main__":
    run()
