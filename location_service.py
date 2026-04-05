"""
api/services/location_service.py
──────────────────────────────────
Backend GPS / location tracking service:
  • Real-time unit position updates
  • Geofence violation detection
  • Patrol route management
  • Distance / speed calculations
  • Location history replay
"""

import math, random, time
from datetime import datetime
from typing import Optional, List

import sys, os
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT_DIR)
from database.db import upsert_location, get_latest_locations, get_location_history

# ── Sector boundary definitions ───────────────────────────────────────────────
SECTOR_BOUNDS = {
    "A1": {"lat": (31.05, 31.95), "lon": (73.05, 73.95)},
    "A2": {"lat": (31.05, 31.95), "lon": (74.05, 74.95)},
    "A3": {"lat": (31.05, 31.95), "lon": (75.05, 75.95)},
    "B1": {"lat": (30.05, 30.95), "lon": (73.05, 73.95)},
    "B2": {"lat": (30.05, 30.95), "lon": (74.05, 74.95)},
    "B3": {"lat": (30.05, 30.95), "lon": (75.05, 75.95)},
    "C1": {"lat": (29.05, 29.95), "lon": (73.05, 73.95)},
    "C2": {"lat": (29.05, 29.95), "lon": (74.05, 74.95)},
    "C3": {"lat": (29.05, 29.95), "lon": (75.05, 75.95)},
    "D1": {"lat": (28.05, 28.95), "lon": (73.05, 73.95)},
    "D2": {"lat": (28.05, 28.95), "lon": (74.05, 74.95)},
    "D3": {"lat": (28.05, 28.95), "lon": (75.05, 75.95)},
}

# Restricted zones — if a unit enters these, raise an alert
RESTRICTED_ZONES = [
    {"id": "RZ-01", "name": "Hostile Territory North",
     "lat": (31.6, 32.0), "lon": (73.2, 74.0), "level": "CRITICAL"},
    {"id": "RZ-02", "name": "Unmarked Minefield West",
     "lat": (29.8, 30.2), "lon": (72.0, 72.8), "level": "HIGH"},
]

# Patrol waypoints for each unit
PATROL_ROUTES = {
    "UNIT-7":  [(31.5,73.5),(31.5,74.5),(31.5,75.5),(30.5,75.5),(30.5,74.5),(30.5,73.5)],
    "UNIT-3":  [(29.5,73.5),(29.5,74.5),(29.5,75.5),(28.5,75.5),(28.5,74.5),(28.5,73.5)],
    "UNIT-9":  [(30.5,73.5),(30.5,74.5),(30.5,75.5)],
    "DRONE-2": [(31.5,73.5),(30.5,74.5),(29.5,75.5),(28.5,74.5)],
    "DRONE-4": [(29.5,73.5),(30.5,73.5),(31.5,73.5)],
}


class LocationService:
    """GPS tracking, geofencing, and patrol management."""

    def __init__(self):
        # In-memory position cache for real-time updates
        self._positions: dict = {}
        self._patrol_indices: dict = {}  # unit → current waypoint index

    # ── Unit position update ──────────────────────────────────────────────────
    def update_position(self, unit_id: str, unit_type: str,
                        lat: float, lon: float,
                        speed: float = 0.0, heading: float = 0.0) -> dict:
        """
        Record a new position for a unit.
        Returns geofence alerts if any.
        """
        sector  = self.coords_to_sector(lat, lon)
        prev    = self._positions.get(unit_id)
        dist_km = 0.0
        if prev:
            dist_km = self.haversine(prev["lat"], prev["lon"], lat, lon)

        self._positions[unit_id] = {
            "unit_id":    unit_id,
            "unit_type":  unit_type,
            "lat":        lat,
            "lon":        lon,
            "sector":     sector,
            "speed":      speed,
            "heading":    heading,
            "updated_at": datetime.now().isoformat(),
            "dist_km_since_last": round(dist_km, 4),
        }

        upsert_location(unit_id, unit_type, lat, lon, sector, speed, heading)

        violations = self.check_geofence(unit_id, lat, lon)

        return {
            "unit_id":   unit_id,
            "lat":       lat,
            "lon":       lon,
            "sector":    sector,
            "speed":     speed,
            "heading":   heading,
            "violations": violations,
            "recorded":  True,
        }

    # ── Get all live positions ────────────────────────────────────────────────
    def get_all_positions(self) -> list:
        """Return latest position for every known unit."""
        db_locs = get_latest_locations()
        # Merge with in-memory cache
        seen = {loc["unit_id"] for loc in db_locs}
        for uid, pos in self._positions.items():
            if uid not in seen:
                db_locs.append(pos)
        return db_locs

    # ── Sector lookup ─────────────────────────────────────────────────────────
    @staticmethod
    def coords_to_sector(lat: float, lon: float) -> str:
        """Return sector label for given coordinates."""
        for sector, bounds in SECTOR_BOUNDS.items():
            if (bounds["lat"][0] <= lat <= bounds["lat"][1] and
                    bounds["lon"][0] <= lon <= bounds["lon"][1]):
                return sector
        return "UNKNOWN"

    # ── Haversine distance ────────────────────────────────────────────────────
    @staticmethod
    def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate great-circle distance between two GPS points (km)."""
        R   = 6371.0
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a   = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
        return round(R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a)), 4)

    # ── Geofence violation ────────────────────────────────────────────────────
    def check_geofence(self, unit_id: str, lat: float, lon: float) -> list:
        """Check if coordinates fall inside any restricted zone."""
        violations = []
        for zone in RESTRICTED_ZONES:
            in_lat = zone["lat"][0] <= lat <= zone["lat"][1]
            in_lon = zone["lon"][0] <= lon <= zone["lon"][1]
            if in_lat and in_lon:
                violations.append({
                    "zone_id":   zone["id"],
                    "zone_name": zone["name"],
                    "level":     zone["level"],
                    "unit_id":   unit_id,
                    "lat":       lat,
                    "lon":       lon,
                    "timestamp": datetime.now().isoformat(),
                })
        return violations

    # ── Patrol simulation ─────────────────────────────────────────────────────
    def advance_patrol(self, unit_id: str) -> Optional[dict]:
        """
        Move a patrol unit to the next waypoint.
        Call this on a timer to simulate patrol movement.
        """
        route = PATROL_ROUTES.get(unit_id)
        if not route:
            return None

        idx  = self._patrol_indices.get(unit_id, 0)
        next_idx = (idx + 1) % len(route)
        self._patrol_indices[unit_id] = next_idx

        curr = route[idx]
        nxt  = route[next_idx]

        # Interpolate midpoint
        mid_lat = (curr[0] + nxt[0]) / 2 + random.uniform(-0.02, 0.02)
        mid_lon = (curr[1] + nxt[1]) / 2 + random.uniform(-0.02, 0.02)

        heading = math.degrees(math.atan2(nxt[1]-curr[1], nxt[0]-curr[0]))
        speed   = round(random.uniform(30, 60), 1)
        unit_type = "drone" if "DRONE" in unit_id else "vehicle" if "UNIT" in unit_id else "officer"

        return self.update_position(unit_id, unit_type, mid_lat, mid_lon, speed, heading)

    def simulate_all_patrols(self) -> list:
        """Advance all patrol units one step."""
        results = []
        for unit_id in PATROL_ROUTES:
            result = self.advance_patrol(unit_id)
            if result:
                results.append(result)
        return results

    # ── Location history ──────────────────────────────────────────────────────
    def get_unit_history(self, unit_id: str, limit: int = 50) -> dict:
        history = get_location_history(unit_id, limit)
        if not history:
            return {"unit_id": unit_id, "history": [], "total_distance_km": 0}

        total_dist = 0.0
        for i in range(1, len(history)):
            total_dist += self.haversine(
                history[i-1]["lat"], history[i-1]["lon"],
                history[i]["lat"],   history[i]["lon"]
            )

        return {
            "unit_id":         unit_id,
            "history":         history,
            "point_count":     len(history),
            "total_distance_km": round(total_dist, 3),
            "first_seen":      history[-1].get("recorded_at","") if history else "",
            "last_seen":       history[0].get("recorded_at","")  if history else "",
        }

    # ── Nearest units to a point ──────────────────────────────────────────────
    def nearest_units(self, lat: float, lon: float, n: int = 3) -> list:
        """Return n closest units to given coordinates."""
        positions = self.get_all_positions()
        with_dist = [
            {**p, "distance_km": self.haversine(lat, lon, p.get("lat",0), p.get("lon",0))}
            for p in positions
        ]
        return sorted(with_dist, key=lambda x: x["distance_km"])[:n]


# ─── Singleton ────────────────────────────────────────────────────────────────
location_service = LocationService()
