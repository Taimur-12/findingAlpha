"""
Bybit V5 REST client for private API access.

Authenticated wrapper providing the endpoints the execution agent needs:
  - create_order, cancel_order, query_order
  - query_positions, query_wallet_balance

Testnet vs mainnet is controlled by BYBIT_LIVE_MODE env var:
  - "testnet" (default) → api-testnet.bybit.com
  - "mainnet"           → api.bybit.com

Keys are read from BYBIT_TESTNET_API_KEY/SECRET or BYBIT_LIVE_API_KEY/SECRET.
No retries here — the execution agent layers idempotency-aware retries on top.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx

TESTNET_URL = "https://api-testnet.bybit.com"
MAINNET_URL = "https://api.bybit.com"
DEFAULT_RECV_WINDOW = "5000"


class BybitAPIError(Exception):
    """Raised when Bybit returns a non-zero retCode."""

    def __init__(self, ret_code: int, ret_msg: str, endpoint: str) -> None:
        super().__init__(f"Bybit API error {ret_code} on {endpoint}: {ret_msg}")
        self.ret_code = ret_code
        self.ret_msg = ret_msg
        self.endpoint = endpoint


@dataclass(frozen=True)
class BybitClientConfig:
    api_key: str
    api_secret: str
    base_url: str
    recv_window: str = DEFAULT_RECV_WINDOW
    timeout_seconds: float = 10.0

    @classmethod
    def from_env(cls, env: Optional[dict] = None) -> "BybitClientConfig":
        env = env if env is not None else os.environ
        mode = env.get("BYBIT_LIVE_MODE", "testnet").lower()
        if mode == "testnet":
            api_key = env.get("BYBIT_TESTNET_API_KEY")
            api_secret = env.get("BYBIT_TESTNET_API_SECRET")
            base_url = TESTNET_URL
        elif mode == "mainnet":
            api_key = env.get("BYBIT_LIVE_API_KEY")
            api_secret = env.get("BYBIT_LIVE_API_SECRET")
            base_url = MAINNET_URL
        else:
            raise ValueError(f"Unknown BYBIT_LIVE_MODE: {mode!r}")
        if not api_key or not api_secret:
            raise RuntimeError(
                f"Missing Bybit credentials for mode={mode}. Check .env."
            )
        return cls(api_key=api_key, api_secret=api_secret, base_url=base_url)


def _sign(secret: str, payload: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _build_query_string(params: dict[str, Any]) -> str:
    if not params:
        return ""
    items = sorted((k, v) for k, v in params.items() if v is not None)
    return "&".join(f"{k}={v}" for k, v in items)


class BybitClient:
    def __init__(self, cfg: BybitClientConfig, http: Optional[httpx.Client] = None) -> None:
        self._cfg = cfg
        self._http = http if http is not None else httpx.Client(
            base_url=cfg.base_url,
            timeout=cfg.timeout_seconds,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "BybitClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()

    def _headers(self, timestamp_ms: str, payload: str) -> dict[str, str]:
        sign_string = timestamp_ms + self._cfg.api_key + self._cfg.recv_window + payload
        signature = _sign(self._cfg.api_secret, sign_string)
        return {
            "X-BAPI-API-KEY": self._cfg.api_key,
            "X-BAPI-TIMESTAMP": timestamp_ms,
            "X-BAPI-RECV-WINDOW": self._cfg.recv_window,
            "X-BAPI-SIGN": signature,
            "Content-Type": "application/json",
        }

    def _get(self, path: str, params: Optional[dict[str, Any]] = None) -> dict:
        query = _build_query_string(params or {})
        timestamp = str(int(time.time() * 1000))
        headers = self._headers(timestamp, query)
        url = path + ("?" + query if query else "")
        response = self._http.get(url, headers=headers)
        response.raise_for_status()
        return self._unwrap(response.json(), path)

    def _post(self, path: str, body: dict[str, Any]) -> dict:
        body_str = json.dumps(body, separators=(",", ":"))
        timestamp = str(int(time.time() * 1000))
        headers = self._headers(timestamp, body_str)
        response = self._http.post(path, headers=headers, content=body_str)
        response.raise_for_status()
        return self._unwrap(response.json(), path)

    @staticmethod
    def _unwrap(raw: dict, endpoint: str) -> dict:
        ret_code = raw.get("retCode")
        if ret_code != 0:
            raise BybitAPIError(ret_code, raw.get("retMsg", ""), endpoint)
        return raw.get("result", {})

    # ── Order endpoints ───────────────────────────────────────────────────────

    def create_order(
        self,
        *,
        symbol: str,
        side: str,           # "Buy" or "Sell"
        order_type: str,     # "Market" or "Limit"
        qty: str,
        price: Optional[str] = None,
        order_link_id: Optional[str] = None,
        time_in_force: str = "GTC",
        reduce_only: bool = False,
        trigger_price: Optional[str] = None,
        trigger_direction: Optional[int] = None,
        stop_loss: Optional[str] = None,
        take_profit: Optional[str] = None,
        category: str = "linear",
    ) -> dict:
        body: dict[str, Any] = {
            "category": category,
            "symbol": symbol,
            "side": side,
            "orderType": order_type,
            "qty": qty,
            "timeInForce": time_in_force,
            "reduceOnly": reduce_only,
        }
        if price is not None:
            body["price"] = price
        if order_link_id is not None:
            body["orderLinkId"] = order_link_id
        if trigger_price is not None:
            body["triggerPrice"] = trigger_price
        if trigger_direction is not None:
            body["triggerDirection"] = trigger_direction
        if stop_loss is not None:
            body["stopLoss"] = stop_loss
        if take_profit is not None:
            body["takeProfit"] = take_profit
        return self._post("/v5/order/create", body)

    def cancel_order(
        self,
        *,
        symbol: str,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        category: str = "linear",
    ) -> dict:
        if not order_id and not order_link_id:
            raise ValueError("Provide order_id or order_link_id")
        body: dict[str, Any] = {"category": category, "symbol": symbol}
        if order_id:
            body["orderId"] = order_id
        if order_link_id:
            body["orderLinkId"] = order_link_id
        return self._post("/v5/order/cancel", body)

    def query_order(
        self,
        *,
        symbol: str,
        order_id: Optional[str] = None,
        order_link_id: Optional[str] = None,
        category: str = "linear",
    ) -> dict:
        params: dict[str, Any] = {"category": category, "symbol": symbol}
        if order_id:
            params["orderId"] = order_id
        if order_link_id:
            params["orderLinkId"] = order_link_id
        return self._get("/v5/order/realtime", params)

    def query_positions(
        self,
        *,
        symbol: Optional[str] = None,
        category: str = "linear",
        settle_coin: str = "USDT",
    ) -> dict:
        params: dict[str, Any] = {"category": category, "settleCoin": settle_coin}
        if symbol:
            params["symbol"] = symbol
        return self._get("/v5/position/list", params)

    def query_wallet_balance(
        self,
        *,
        account_type: str = "UNIFIED",
        coin: Optional[str] = None,
    ) -> dict:
        params: dict[str, Any] = {"accountType": account_type}
        if coin:
            params["coin"] = coin
        return self._get("/v5/account/wallet-balance", params)
