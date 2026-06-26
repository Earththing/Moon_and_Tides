import httpx


def geocode_address(address: str) -> list[dict]:
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": address, "format": "json", "limit": 5}
    headers = {"User-Agent": "moon_and_tides/0.1"}
    resp = httpx.get(url, params=params, headers=headers, timeout=15)
    resp.raise_for_status()
    results = resp.json()
    return [
        {
            "lat": float(r["lat"]),
            "lon": float(r["lon"]),
            "display_name": r["display_name"],
        }
        for r in results
    ]
