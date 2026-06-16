"""
pionex_client.py
Cliente para la API REST de Pionex.

IMPORTANTE sobre Futuros:
  La Futures API de Pionex es "Invite only" y tiene endpoints distintos.
  La Trade API publica solo cubre Spot (ordenes y fills).

  Para posiciones de futuros cerradas, Pionex expone el historial
  en el endpoint de bots (/api/v1/bot/v2/tradehistory) que incluye
  los trades de futuros de los bots, o via exportacion CSV manual.

  Autenticacion (Trade API publica):
    - Header: PIONEX-KEY  = api_key
    - Header: PIONEX-SIGNATURE = HMAC-SHA256(path + "?" + sorted_query_string)
    - Query param: timestamp (ms)
"""
import hashlib
import hmac
import time
import urllib.parse
import requests

PIONEX_BASE = "https://api.pionex.com"


class PionexClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key    = api_key
        self.api_secret = api_secret
        self.session    = requests.Session()

    def _sign(self, method: str, path: str, params: dict) -> tuple[dict, dict]:
        """
        Genera headers y params firmados para la Trade API de Pionex.
        Retorna (headers, params_con_timestamp).
        """
        ts = str(int(time.time() * 1000))
        params = {**params, "timestamp": ts}

        # Ordenar params alfabeticamente y construir query string
        sorted_qs = urllib.parse.urlencode(sorted(params.items()))

        # Mensaje: METHOD + PATH + "?" + query_string
        message = f"{method.upper()}{path}?{sorted_qs}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        headers = {
            "PIONEX-KEY":       self.api_key,
            "PIONEX-SIGNATURE": signature,
        }
        return headers, params

    def _get(self, path: str, params: dict = None) -> dict:
        params  = params or {}
        headers, signed_params = self._sign("GET", path, params)
        url     = PIONEX_BASE + path
        resp    = self.session.get(url, params=signed_params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("result", True):
            raise ValueError(f"Pionex API error: {data}")
        return data

    # ── Trade API (Spot) ───────────────────────────────────────────────────

    def get_account_balances(self) -> dict:
        """Saldos de la cuenta de trading (excluye bots y earn)."""
        return self._get("/api/v1/account/balances")

    def get_all_orders(self, symbol: str, start_ms: int = None, end_ms: int = None, limit: int = 200) -> list:
        """Todas las ordenes (abiertas y cerradas) de un simbolo."""
        params = {"symbol": symbol, "limit": limit}
        if start_ms: params["startTime"] = start_ms
        if end_ms:   params["endTime"]   = end_ms
        data = self._get("/api/v1/trade/allOrders", params)
        return data.get("data", {}).get("orders", [])

    def get_fills(self, symbol: str, start_ms: int = None, end_ms: int = None) -> list:
        """Fills (ejecuciones) de un simbolo. Max 100 por llamada."""
        params = {"symbol": symbol}
        if start_ms: params["startTime"] = start_ms
        if end_ms:   params["endTime"]   = end_ms
        data = self._get("/api/v1/trade/fills", params)
        return data.get("data", {}).get("fills", [])

    def test_connection(self) -> bool:
        """Verifica que las credenciales son validas consultando el balance."""
        try:
            self.get_account_balances()
            return True
        except Exception as e:
            print(f"[pionex_client] test_connection failed: {e}")
            return False
