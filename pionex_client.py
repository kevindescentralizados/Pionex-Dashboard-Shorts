"""
pionex_client.py
Cliente oficial para la API REST de Pionex v1.
Autenticacion: HMAC-SHA256 con API Key + Secret.
Documentacion: https://pionex-doc.gitbook.io/apidocs/
"""
import hashlib
import hmac
import time
import urllib.parse
import requests

PIONEX_BASE = "https://api.pionex.com"


class PionexClient:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.session = requests.Session()
        self.session.headers.update({"PIONEX-KEY": api_key})

    def _sign(self, method: str, path: str, params: dict) -> dict:
        """
        Genera la firma HMAC-SHA256 requerida por Pionex.
        El timestamp debe estar en milisegundos.
        """
        ts = str(int(time.time() * 1000))
        params = {**params, "timestamp": ts}

        # Ordenar params y construir query string
        sorted_params = sorted(params.items())
        query_string = urllib.parse.urlencode(sorted_params)

        # Mensaje a firmar: METHOD + PATH + ? + query_string
        message = f"{method.upper()}{path}?{query_string}"
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        params["signature"] = signature
        return params

    def _get(self, path: str, params: dict = None) -> dict:
        params = params or {}
        signed = self._sign("GET", path, params)
        url = PIONEX_BASE + path
        resp = self.session.get(url, params=signed, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("result", True):
            raise ValueError(f"Pionex API error: {data}")
        return data

    # ── Futures positions ──────────────────────────────────────────────────

    def get_closed_futures_positions(
        self,
        start_time: int = None,
        end_time: int = None,
        limit: int = 200,
        cursor: str = None,
    ) -> dict:
        """
        Obtiene posiciones de futuros cerradas.
        start_time / end_time: timestamps en milisegundos.
        Devuelve el JSON completo de la respuesta.
        """
        params = {"limit": limit}
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
        if cursor:
            params["cursor"] = cursor
        return self._get("/api/v1/futures/positions/history", params)

    def get_all_closed_positions(
        self,
        start_ms: int = None,
        side: str = "SHORT",
    ) -> list:
        """
        Pagina automaticamente para obtener todas las posiciones cerradas
        desde start_ms hasta ahora. Filtra por side (SHORT por defecto).
        """
        positions = []
        cursor = None
        end_ms = int(time.time() * 1000)

        while True:
            resp = self.get_closed_futures_positions(
                start_time=start_ms,
                end_time=end_ms,
                limit=200,
                cursor=cursor,
            )
            data = resp.get("data", {})
            items = data.get("items") or data.get("positions") or data.get("list") or []

            if not items:
                break

            for pos in items:
                # Normalizar: Pionex puede devolver el lado como "SHORT" o "short"
                pos_side = str(pos.get("positionSide", pos.get("position_side", ""))).upper()
                if side and pos_side != side.upper():
                    continue
                positions.append(pos)

            # Paginacion: si hay cursor/nextCursor, continuar
            cursor = data.get("nextCursor") or data.get("cursor")
            if not cursor or not items:
                break

        return positions

    def get_futures_fills(
        self,
        start_ms: int = None,
        limit: int = 200,
    ) -> list:
        """
        Obtiene el historico de ejecuciones (fills) de futuros.
        Usado para reconstruir entradas/promedios.
        """
        fills = []
        cursor = None
        end_ms = int(time.time() * 1000)

        while True:
            params = {"limit": limit, "endTime": end_ms}
            if start_ms:
                params["startTime"] = start_ms
            if cursor:
                params["cursor"] = cursor

            resp = self._get("/api/v1/futures/trades", params)
            data = resp.get("data", {})
            items = data.get("items") or data.get("list") or data.get("trades") or []

            if not items:
                break

            fills.extend(items)
            cursor = data.get("nextCursor") or data.get("cursor")
            if not cursor or not items:
                break

        return fills
