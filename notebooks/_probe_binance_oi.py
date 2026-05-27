import httpx

END = 1779840000000
S30 = END - 30*24*3600*1000
S60 = END - 60*24*3600*1000

for label, start in [("30d", S30), ("60d", S60)]:
    r = httpx.get("https://fapi.binance.com/futures/data/openInterestHist",
                  params={"symbol": "BTCUSDT", "period": "1h", "startTime": start, "limit": 3})
    print(f"{label} startTime: {r.status_code} {r.text[:120]}")

# Pagination using endTime only (no startTime)
r = httpx.get("https://fapi.binance.com/futures/data/openInterestHist",
              params={"symbol": "BTCUSDT", "period": "1h", "endTime": END, "limit": 3})
print(f"endTime only: {r.status_code} {r.text[:200]}")
