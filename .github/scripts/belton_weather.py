"""Fetch Belton's hour-by-hour forecast and write it where the room reads it (room/weather.json).

Belton is the village on the Isle of Axholme, North Lincolnshire, west of Scunthorpe
(53.556 N, 0.816 W), not the Belton near Grantham.

The deploy job (.github/workflows/hugo.yaml) runs this every three hours after the build
so the only thing that ever asks Open-Meteo is GitHub's runner: visitors' browsers read the
file from the site itself. Standard library only, so it needs nothing installed.

    python3 .github/scripts/belton_weather.py public/room/weather.json [public/new/room/weather.json ...]

For the local preview, write it to static/room/weather.json (gitignored).

If Open-Meteo can't be reached it says so and writes nothing; the room then keeps a fair sky.
It never fails the deploy.
"""

import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

LAT, LON = 53.556, -0.816
URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={LAT}&longitude={LON}"
    "&hourly=weather_code,cloud_cover,visibility,wind_speed_10m"
    "&wind_speed_unit=ms&timezone=Europe%2FLondon&past_days=1&forecast_days=3"
)


def fetch():
    for attempt in range(3):
        try:
            req = urllib.request.Request(URL, headers={"User-Agent": "davebuckley.tech room weather"})
            with urllib.request.urlopen(req, timeout=20) as res:
                return json.load(res)
        except Exception as e:  # noqa: BLE001 (any failure: try again, then give up quietly)
            print(f"weather: attempt {attempt + 1} failed: {e}", file=sys.stderr)
            time.sleep(5 * (attempt + 1))
    return None


def main(paths):
    data = fetch()
    if not data or "hourly" not in data:
        print("weather: no forecast this time; the room keeps a fair sky", file=sys.stderr)
        return
    h = data["hourly"]
    hours = {}
    for i, t in enumerate(h["time"]):  # London wall-clock hours, e.g. 2026-10-21T14:00
        code = h["weather_code"][i]
        if code is None:
            continue
        hours[t] = [code, h["cloud_cover"][i], h["visibility"][i], h["wind_speed_10m"][i]]
    out = {
        "place": "Belton, Isle of Axholme, North Lincolnshire",
        "source": "Open-Meteo (open-meteo.com), CC BY 4.0",
        "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
        "hours": hours,
    }
    text = json.dumps(out, separators=(",", ":"))
    for p in map(Path, paths):
        if not p.parent.exists():
            print(f"weather: skipping {p} (no {p.parent})", file=sys.stderr)
            continue
        p.write_text(text)
        print(f"weather: wrote {len(hours)} hours to {p}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["static/room/weather.json"])
