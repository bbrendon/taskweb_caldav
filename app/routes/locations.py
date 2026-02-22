import niquests
from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.get("/locations/search")
async def search_locations(q: str):
    try:
        resp = niquests.get(
            "https://nominatim.openstreetmap.org/search",
            params={"q": q, "format": "json", "limit": 5},
            headers={"User-Agent": "TaskWeb-CalDAV/1.0"},
            timeout=5,
        )
        results = [
            {
                "title": r["display_name"].split(",")[0].strip(),
                "address": r["display_name"],
                "lat": float(r["lat"]),
                "lng": float(r["lon"]),
            }
            for r in resp.json()
        ]
    except Exception:
        results = []
    return JSONResponse(results)
