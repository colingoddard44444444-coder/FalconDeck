import json
import os

import config
from aircraft import Aircraft


def _aircraft_json_path():
    candidates = [
        getattr(config, "AIRCRAFT_JSON", ""),
        "/run/dump1090-fa/aircraft.json",
        "/run/dump1090-mutability/aircraft.json",
        "/run/readsb/aircraft.json",
        "/var/run/dump1090-fa/aircraft.json",
    ]
    for path in candidates:
        if path and os.path.exists(path):
            return path
    return candidates[0]


def load_aircraft():
    """Load aircraft from a local dump1090/readsb aircraft.json file."""
    path = _aircraft_json_path()
    if not path or not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as source:
            data = json.load(source)
    except (OSError, ValueError, TypeError):
        return []

    result = []
    for item in data.get("aircraft", []):
        altitude = item.get("alt_baro", item.get("alt_geom"))
        if altitude == "ground":
            altitude = 0
        result.append(
            Aircraft(
                hex=item.get("hex", ""),
                callsign=item.get("flight", "").strip(),
                latitude=item.get("lat"),
                longitude=item.get("lon"),
                altitude=altitude,
                speed=item.get("gs"),
                heading=item.get("track"),
                squawk=item.get("squawk", ""),
                aircraft_type=item.get("t", ""),
                registration=item.get("r", ""),
            )
        )
    return result


def receiver_online():
    path = _aircraft_json_path()
    return bool(path and os.path.exists(path))
