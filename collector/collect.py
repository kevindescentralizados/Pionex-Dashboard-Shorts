"""
collector/collect.py  —  Recolector principal del dashboard de Pionex Shorts.

Estrategia de datos (por orden de prioridad):
  1. API de Pionex (si hay PIONEX_KEY + PIONEX_SECRET) → posiciones nuevas
     desde la ultima ejecucion, acumuladas en store/positions.jsonl.
  2. CSV sembrados manualmente en la raiz → backfill historico completo.

Genera site/data.json que el dashboard lee cada 5 minutos.
"""
import os
import sys
import json
import glob
import time
from datetime import datetime, timezone

import pandas as pd
import numpy as np

# Hacer visible el raiz del repo para importar pionex_client
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

STORE     = os.path.join(ROOT, "store", "positions.jsonl")
SITE_DATA = os.path.join(ROOT, "site", "data.json")
LAST_UPD  = os.path.join(ROOT, "site", "last_update.txt")
REBALANCE_ENTRIES = 20


# ── utilidades ─────────────────────────────────────────────────────────────

def clean_symbol(sym: str) -> str:
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
    trips = []
    fills = fills.sort_values("t").copy()
    for symbol, grp in fills.groupby("symbol"):
        sells = grp[grp["side"].str.upper() == "SELL"].copy()
        buys  = grp[grp["side"].str.upper() == "BUY"].copy()
        buy_pool = list(buys.itertuples())
        used_buy_idx = set()
        for s_row in sells.itertuples():
            qty_to_cover = float(s_row.executed_qty)
            trip_buys = []
            for b in buy_pool:
                if b.Index in used_buy_idx:
                    continue
                if b.t < s_row.t:
                    continue
                trip_buys.append(b)
                used_buy_idx.add(b.Index)
                qty_to_cover -= float(b.executed_qty)
                if qty_to_cover <= 1e-9:
                    break
            sell_qty = float(s_row.executed_qty)
            sell_amt = float(s_row.amount)
            buy_amt  = sum(float(b.amount) for b in trip_buys)
            close_t  = trip_buys[-1].t if trip_buys else s_row.t
            trips.append(dict(
                close=close_t, symbol=symbol, first="SELL",
                n_ent=len(trip_buys), sell_qty=sell_qty,
                sell_amt=sell_amt, gross=round(sell_amt - buy_amt, 6),
            ))
    return trips


# ── fuente 1: API de Pionex ─────────────────────────────────────────────────

def _ms_of_last_record(records: list) -> int:
    """Devuelve el timestamp (ms) de la posicion mas reciente del store."""
    if not records:
        return 0
    dates = []
    for r in records:
        ct = r.get("close_time") or r.get("ct") or ""
        if ct:
            try:
                dates.append(int(pd.Timestamp(ct).timestamp() * 1000))
            except Exception:
                pass
    return max(dates) if dates else 0

def normalize_api_position(pos: dict) -> dict:
    """Convierte un registro crudo de la API al formato interno del store."""
    symbol  = pos.get("symbol", "")
    gross   = float(pos.get("pnl",        pos.get("profit", 0)) or 0)
    fee     = float(pos.get("fee",        pos.get("tradeFee", 0)) or 0)
    funding = float(pos.get("fundingFee", pos.get("funding_fee", 0)) or 0)
    net     = round(gross + fee + funding, 6)

    open_ts  = pos.get("openTime",  pos.get("open_time",  0))
    close_ts = pos.get("closeTime", pos.get("close_time", 0))

    def ts_to_str(ts):
        if isinstance(ts, (int, float)) and ts > 1e10:
            return datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        return str(ts)

    side = str(pos.get("positionSide", pos.get("position_side", "SHORT"))).upper()
    n_ent = pos.get("entryCount") or pos.get("n_entries") or None

    return dict(
        pos_id     = str(pos.get("positionId", pos.get("position_id", ""))),
        symbol     = symbol,
        activo     = clean_symbol(symbol),
        side       = side.lower(),
        open_time  = ts_to_str(open_ts),
        close_time = ts_to_str(close_ts),
        gross      = round(gross,   6),
        fee        = round(fee,     6),
        funding    = round(funding, 6),
        net        = net,
        capital    = float(pos.get("size", pos.get("capital", 0)) or 0) or None,
        n_entries  = int(n_ent) if n_ent is not None else None,
        avg_entry_px = float(pos.get("entryPrice", pos.get("avg_entry_px", 0)) or 0) or None,
        estado     = "OK",
        source     = "api",
    )

def fetch_from_api(existing_records: list) -> list:
    """
    Llama a la API de Pionex y devuelve posiciones nuevas (short cerradas)
    desde el ultimo registro guardado.
    """
    api_key    = os.environ.get("PIONEX_KEY", "")
    api_secret = os.environ.get("PIONEX_SECRET", "")
    if not api_key or not api_secret:
        print("[collect] Sin credenciales de API → omitiendo paso de API.")
        return []

    try:
        from pionex_client import PionexClient
    except ImportError:
        print("[collect] pionex_client no encontrado.")
        return []

    client   = PionexClient(api_key, api_secret)
    start_ms = _ms_of_last_record(existing_records)
    # Pedir desde 1 dia antes del ultimo registro para no perder nada
    if start_ms:
        start_ms = start_ms - 86_400_000

    print(f"[collect] Consultando API desde {datetime.fromtimestamp(start_ms/1000, tz=timezone.utc) if start_ms else 'el principio'}...")

    try:
        raw_positions = client.get_all_closed_positions(start_ms=start_ms or None, side="SHORT")
    except Exception as e:
        print(f"[collect] Error en API de posiciones: {e}")
        return []

    print(f"[collect] API devolvio {len(raw_positions)} posiciones short cerradas.")

    # Deduplicar contra store existente
    existing_ids = {r.get("pos_id") for r in existing_records}
    new_recs = []
    for pos in raw_positions:
        norm = normalize_api_position(pos)
        if norm["pos_id"] and norm["pos_id"] in existing_ids:
            continue
        new_recs.append(norm)

    print(f"[collect] {len(new_recs)} posiciones nuevas de la API (no existian en store).")
    return new_recs


# ── fuente 2: CSV sembrado manualmente ─────────────────────────────────────

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
    files    = glob.glob(os.path.join(root, "*.csv"))
    pos_fp   = _detect(files, ["position_side", "pnl", "funding_fee"])
    fills_fp = _detect(files, ["executed_qty",  "side", "tax_id"])

    if not pos_fp or not fills_fp:
        print(f"[collect] CSV no encontrados en {root}.")
        return []

    print(f"[collect] CSV posiciones : {os.path.basename(pos_fp)}")
    print(f"[collect] CSV fills      : {os.path.basename(fills_fp)}")

    pos = pd.read_csv(pos_fp)
    pos = pos[pos["position_side"] == "short"].copy().reset_index(drop=True)
    pos["acct"] = pos["position_id"].str.split("_").str[0]
    pos["ot"]   = pd.to_datetime(pos["open_time"])
    pos["ct"]   = pd.to_datetime(pos["close_time"])

    raw = pd.read_csv(fills_fp).rename(columns={"date(UTC+0)": "date"})
    if "state"       in raw.columns: raw = raw[raw["state"]       == "FILLED"]
    if "market_type" in raw.columns: raw = raw[raw["market_type"] == "Futures USDT"]
    raw["t"] = pd.to_datetime(raw["date"])
    for c in ("executed_qty", "amount", "price"):
        raw[c] = pd.to_numeric(raw[c])
    if "fee" not in raw.columns:
        raw["fee"] = 0.0

    trips = reconstruct_round_trips(
        raw[["t","symbol","side","executed_qty","amount","price","fee","tax_id"]]
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
                t   = T.loc[j]
                cap = float(t["sell_amt"])
                n   = int(t["n_ent"])
                avgpx = float(t["sell_amt"]/t["sell_qty"]) if t["sell_qty"] else None
                err = abs(float(t["gross"]) - float(r["pnl"]))

        rebalance = (r["acct"] == "43112881807336") or (n is not None and n >= REBALANCE_ENTRIES)
        if   cap is None or np.isnan(err): estado = "Revisar"
        elif rebalance:                    estado = "Rebalanceo"
        elif err > 5:                      estado = "Revisar"
        else:                              estado = "OK"

        gross   = float(r["pnl"])
        fee     = float(r["fee"])
        fund    = float(r["funding_fee"])
        recs.append(dict(
            pos_id=r["position_id"], symbol=r["symbol"], activo=clean_symbol(r["symbol"]),
            side="short",
            open_time=r["ot"].strftime("%Y-%m-%d %H:%M:%S"),
            close_time=r["ct"].strftime("%Y-%m-%d %H:%M:%S"),
            gross=round(gross,6), fee=round(fee,6), funding=round(fund,6),
            net=round(gross+fee+fund,6),
            capital=(round(cap,6) if cap is not None else None),
            n_entries=n,
            avg_entry_px=(round(avgpx,10) if avgpx is not None else None),
            estado=estado, source="seed",
        ))

    print(f"[collect] {len(recs)} posiciones sembradas desde CSV.")
    return recs


# ── build data.json ─────────────────────────────────────────────────────────

def build_data_json(records: list) -> dict:
    if not records:
        return {"empty": True}

    df = pd.DataFrame(records)
    df["ct"]      = pd.to_datetime(df["close_time"])
    df["date"]    = df["ct"].dt.strftime("%Y-%m-%d")
    df["net"]     = pd.to_numeric(df["net"])
    df["gross"]   = pd.to_numeric(df["gross"])
    df["fee"]     = pd.to_numeric(df["fee"])
    df["funding"] = pd.to_numeric(df["funding"])

    total_net   = df["net"].sum()
    total_gross = df["gross"].sum()
    total_fee   = df["fee"].sum()
    total_fund  = df["funding"].sum()
    wins        = int((df["net"] > 0).sum())
    losses      = int((df["net"] <= 0).sum())
    n_ops       = len(df)
    win_rate    = round(wins / n_ops * 100, 2) if n_ops else 0

    has_cap = df[df["capital"].notna() & (df["capital"] > 0)].copy()
    avg_pct = 0.0
    if len(has_cap):
        has_cap["pct"] = has_cap["net"] / has_cap["capital"] * 100
        avg_pct = round(has_cap["pct"].mean(), 4)

    daily  = df.groupby("date").agg(
        net   =("net",  "sum"),
        gross =("gross","sum"),
        fee   =("fee",  "sum"),
        nops  =("net",  "count"),
        wins  =("net",  lambda x: int((x > 0).sum())),
    ).reset_index()

    ndays     = len(daily)
    avg_daily = round(total_net / ndays, 4) if ndays else 0
    best_row  = daily.loc[daily["net"].idxmax()]
    worst_row = daily.loc[daily["net"].idxmin()]

    days_out = []
    for _, day_row in daily.sort_values("date").iterrows():
        day_ops_df = df[df["date"] == day_row["date"]].copy()
        day_cap    = day_ops_df["capital"].dropna()
        day_pct    = round(day_row["net"] / day_cap.sum() * 100, 2) if day_cap.sum() > 0 else None
        ops_out = []
        for _, op in day_ops_df.sort_values("ct").iterrows():
            op_cap = op["capital"] if pd.notna(op.get("capital")) and op["capital"] > 0 else None
            op_pct = round(op["net"] / op_cap * 100, 2) if op_cap else None
            ops_out.append(dict(
                activo=op["activo"], est=op["estado"],
                n=int(op["n_entries"]) if pd.notna(op.get("n_entries")) else None,
                net=round(float(op["net"]),2), pct=op_pct,
            ))
        days_out.append(dict(
            date=day_row["date"], net=round(float(day_row["net"]),2),
            pct=day_pct, nops=int(day_row["nops"]), wins=int(day_row["wins"]),
            ops=ops_out,
        ))

    return dict(
        empty=False,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        kpi=dict(
            total_net=round(float(total_net),2), total_gross=round(float(total_gross),2),
            total_fee=round(float(total_fee),2), total_fund=round(float(total_fund),2),
            win_rate=win_rate, wins=wins, losses=losses, n_ops=n_ops,
            avg_pct=avg_pct, avg_daily=avg_daily, ndays=ndays,
            best=dict(date=str(best_row["date"]),  net=round(float(best_row["net"]),2)),
            worst=dict(date=str(worst_row["date"]),net=round(float(worst_row["net"]),2)),
        ),
        days=days_out,
    )


# ── main ────────────────────────────────────────────────────────────────────

# ── fuente 3: positions.jsonl en root (CSV exportado de Pionex) ──────────────

def load_pioneer_csv(path: str) -> list:
    """Lee el positions.jsonl del root, que en realidad es un CSV de Pionex
    con columnas: position_id, symbol, position_side, open_time, close_time, pnl, fee, funding_fee"""
    if not os.path.exists(path):
        return []
    try:
        df = pd.read_csv(path)
        df.columns = [c.strip().strip('"') for c in df.columns]
        required = {"position_id", "symbol", "pnl", "fee", "funding_fee"}
        if not required.issubset(set(df.columns)):
            print(f"[collect] positions.jsonl del root no tiene columnas esperadas: {list(df.columns)}")
            return []
        recs = []
        for _, row in df.iterrows():
            gross  = float(row.get("pnl", 0) or 0)
            fee    = float(row.get("fee", 0) or 0)
            funding = float(row.get("funding_fee", 0) or 0)
            net    = round(gross + fee + funding, 6)
            sym    = str(row.get("symbol", "")).strip()
            recs.append({
                "pos_id":     str(row.get("position_id", "")).strip(),
                "symbol":     sym,
                "activo":     clean_symbol(sym),
                "side":       str(row.get("position_side", "short")).strip(),
                "open_time":  str(row.get("open_time", "")).strip(),
                "close_time": str(row.get("close_time", "")).strip(),
                "gross":      round(gross, 6),
                "fee":        round(fee, 6),
                "funding":    round(funding, 6),
                "net":        net,
                "capital":    float(row.get("capital", 0) or 0),
                "n_entries":  int(float(row.get("n_entries", 1) or 1)),
                "avg_entry_px": float(row.get("avg_entry_px", 0) or 0),
                "pct":        float(row.get("pct", 0) or 0),
                "estado":     str(row.get("estado", "OK") or "OK"),
                "source":     "pioneer_csv",
            })
        print(f"[collect] Pioneer CSV: {len(recs)} registros cargados desde {os.path.basename(path)}.")
        return recs
    except Exception as e:
        print(f"[collect] Error leyendo Pioneer CSV: {e}")
        return []


def main():
    print("[collect] ── Iniciando recoleccion ──")

    # 1. Cargar store existente
    existing = load_jsonl(STORE)
    print(f"[collect] Store existente: {len(existing)} registros.")

    # 2. Intentar actualizar desde la API (posiciones nuevas)
    api_recs = fetch_from_api(existing)

    # 3. Sembrar desde CSV (backfill historico)
    csv_recs = seed_from_csv(ROOT)

    # 3b. Cargar positions.jsonl del root (CSV de Pionex exportado)
    pioneer_recs = load_pioneer_csv(os.path.join(ROOT, "positions.jsonl"))

    # 4. Combinar: CSV como base historica, API sobre escribe/añade lo nuevo
    #    - CSV seed source="seed", API source="api"
    #    - Deduplicar por pos_id
    all_by_id = {}
    for r in csv_recs + pioneer_recs:
        pid = r.get("pos_id","")
        if pid:
            all_by_id[pid] = r
    for r in api_recs:
        pid = r.get("pos_id","")
        if pid:
            all_by_id[pid] = r   # API tiene prioridad
    # Registros sin pos_id (no deberia pasar pero por si acaso)
    no_id = [r for r in csv_recs + pioneer_recs + api_recs if not r.get("pos_id")]
    all_records = list(all_by_id.values()) + no_id

    if not all_records:
        # Ultimo recurso: usar lo que habia en el store
        all_records = existing

    # 5. Guardar store actualizado
    save_jsonl(STORE, all_records)
    print(f"[collect] Store guardado: {len(all_records)} registros totales.")

    # 6. Generar site/data.json
    data = build_data_json(all_records)
    os.makedirs(os.path.dirname(SITE_DATA), exist_ok=True)
    with open(SITE_DATA, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",",":"))
    print(f"[collect] site/data.json generado ({os.path.getsize(SITE_DATA):,} bytes)")

    ts = data.get("generated_at","")
    with open(LAST_UPD, "w") as f:
        f.write(ts)
    print(f"[collect] Timestamp: {ts}")
    print("[collect] ── Completado ──")


if __name__ == "__main__":
    main()
