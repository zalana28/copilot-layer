"""
Copilot Layer - A2MCP server (FastMCP, SSE transport)
SSE: GET /sse (server->client stream), POST /messages/ (client->server)
Health (OKX probe): GET /health -> 200

Run: python main.py
"""

import os
import time
import requests
from fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount

mcp = FastMCP("Copilot Layer")

CRYPTO_MAP = {
    "bera": "berachain-bera", "btc": "bitcoin", "eth": "ethereum",
    "sol": "solana", "okb": "okb",
}
GOODS = {
    "iphone 16 pro": {"US": 999.0, "JP": 159800.0, "EU": 1199.0, "UK": 1199.0},
    "iphone 16": {"US": 799.0, "JP": 124800.0, "EU": 969.0, "UK": 949.0},
    "macbook air m3": {"US": 1099.0, "JP": 164800.0, "EU": 1299.0, "UK": 1099.0},
    "airpods pro 2": {"US": 249.0, "JP": 35600.0, "EU": 299.0, "UK": 249.0},
}
COUNTRY_CCY = {"US": "USD", "JP": "JPY", "EU": "EUR", "UK": "GBP"}
CCY_SYMBOL = {"USD": "$", "JPY": "\u00a5", "EUR": "\u20ac", "GBP": "\u00a3"}
CG_URL = "https://api.coingecko.com/api/v3/simple/price"
_cache = {}
_CACHE_TTL = 30


def _get_crypto(symbol: str):
    sym = symbol.lower().strip()
    coin = CRYPTO_MAP.get(sym, sym)
    now = time.time()
    if sym in _cache and now - _cache[sym]["t"] < _CACHE_TTL:
        return _cache[sym]["v"]
    try:
        r = requests.get(CG_URL, params={"ids": coin, "vs_currencies": "usd"},
                         headers={"User-Agent": "copilot-layer/1.0"}, timeout=8)
        r.raise_for_status()
        price = r.json().get(coin, {}).get("usd")
    except Exception:
        price = None
    _cache[sym] = {"t": now, "v": price}
    return price


@mcp.tool()
def crypto_price(symbol: str) -> str:
    """Get the live USD price of a crypto token/coin by symbol. Args: symbol (BERA, BTC, ETH)."""
    price = _get_crypto(symbol)
    if price is None:
        return f"Sorry, live price for {symbol.upper()} unavailable right now."
    return f"{symbol.upper()} / USDT: ${price:,.4f} (live via CoinGecko)"


@mcp.tool()
def goods_price(product: str, countries: list[str] = None) -> str:
    """Get reference retail prices of a product across countries."""
    p = product.lower().strip()
    match = None
    for key in GOODS:
        if p in key or key in p:
            match = key
            break
    if not match:
        return f"Sorry, I don't have reference prices for '{product}' yet."
    table = GOODS[match]
    countries = [c.upper() for c in (countries or ["US", "JP", "EU"])]
    lines = [f"\U0001F4B0 {match.title()} price check (approx MSRP):"]
    for c in countries:
        if c in table:
            sym = CCY_SYMBOL.get(COUNTRY_CCY.get(c, "USD"), "$")
            lines.append(f"  {c}: {sym}{table[c]:,.0f}")
    return "\n".join(lines)


# SSE app from FastMCP
mcp_app = mcp.sse_app()


async def wrapped(scope, receive, send):
    if scope["type"] == "http" and scope.get("method") == "GET" and scope.get("path") in ("/", "/health"):
        r = JSONResponse({"status": "ok", "agent": "Copilot Layer",
                          "type": "A2MCP", "tools": ["crypto_price", "goods_price"],
                          "mcp_endpoint": "/sse"})
        await r(scope, receive, send)
        return
    await mcp_app(scope, receive, send)


if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(wrapped, host="0.0.0.0", port=port)
