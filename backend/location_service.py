import math
import re
from urllib.parse import parse_qs, unquote, urlparse


def haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance in meters between two GPS coordinates."""
    radius = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def is_finite_number(value):
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def has_coordinates(spot):
    return is_finite_number(spot.get("lat")) and is_finite_number(spot.get("lon"))


def spot_location_code(spot, route_spot_order):
    zone = str(spot.get("mapZone") or "lingshan").strip().lower()
    prefix = "NH" if zone == "nianhua" else "LS"
    name = str(spot.get("name") or "").strip()
    order = route_spot_order.get(zone, {}).get(name)
    if order:
        return f"{prefix}-{max(1, int(order) // 10):03d}"
    try:
        spot_id = int(spot.get("id") or 0)
    except (TypeError, ValueError):
        spot_id = 0
    return f"{prefix}-M{spot_id:03d}" if spot_id else f"{prefix}-000"


def extract_location_code(value):
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = urlparse(raw)
        if parsed.scheme and parsed.netloc:
            query = parse_qs(parsed.query)
            hash_query = parsed.fragment.split("?", 1)[1] if "?" in parsed.fragment else ""
            hash_params = parse_qs(hash_query)
            return (
                query.get("loc", [""])[0]
                or query.get("code", [""])[0]
                or hash_params.get("loc", [""])[0]
                or hash_params.get("code", [""])[0]
                or raw
            )
    except ValueError:
        pass
    match = re.search(r"(?:loc|code)=([^&#]+)", raw, re.I)
    return unquote(match.group(1)) if match else raw


def normalize_location_code(value):
    code = extract_location_code(value)
    return re.sub("[\\s_\\-#:\\uFF03\\uFF1A]+", "", str(code or "")).upper()


def spot_matches_location_code(spot, raw_code):
    normalized = normalize_location_code(raw_code)
    raw_text = extract_location_code(raw_code).strip()
    candidates = [
        spot.get("locationCode"),
        spot.get("id"),
        f"SPOT-{spot.get('id')}" if spot.get("id") is not None else "",
        spot.get("name"),
    ]
    return any(normalize_location_code(candidate) == normalized for candidate in candidates) or raw_text == spot.get("name")


def spots_with_distance(lat, lon, spots):
    with_coords = [
        (spot, haversine_distance(float(lat), float(lon), float(spot["lat"]), float(spot["lon"])))
        for spot in spots
        if has_coordinates(spot)
    ]
    with_coords.sort(key=lambda item: item[1])
    return with_coords


def spot_with_distance(spot, distance):
    item = dict(spot)
    item["distance"] = round(distance)
    return item


def clamp_limit(limit, default=5, maximum=10):
    try:
        value = int(limit or default)
    except (TypeError, ValueError):
        value = default
    return max(1, min(value, maximum))


def spots_nearby(lat, lon, spots, limit=5):
    with_coords = spots_with_distance(lat, lon, spots)
    return [spot_with_distance(spot, dist) for spot, dist in with_coords[:clamp_limit(limit)]]


def parse_optional_float(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def location_confidence(distance, accuracy=None):
    if distance is None:
        return "low"
    accuracy_value = parse_optional_float(accuracy)
    accuracy_margin = max(0, accuracy_value or 0)
    if distance <= max(35, accuracy_margin + 20):
        return "medium" if accuracy_value and accuracy_value > 120 else "high"
    if distance <= max(150, accuracy_margin + 90):
        return "medium"
    return "low"


def nearby_location_result(lat, lon, spots, limit=5, accuracy=None):
    safe_limit = clamp_limit(limit)
    with_coords = spots_with_distance(lat, lon, spots)
    items = [spot_with_distance(spot, dist) for spot, dist in with_coords[:safe_limit]]
    nearest = items[0] if items else None
    nearest_distance = nearest.get("distance") if nearest else None
    confidence = location_confidence(nearest_distance, accuracy)
    accuracy_value = parse_optional_float(accuracy)
    scenic_radius = max(650, (accuracy_value or 0) + 220)
    inside_scenic = nearest is not None and nearest_distance <= scenic_radius
    if not nearest:
        message = "\u6682\u65e0\u53ef\u7528\u666f\u70b9\u5750\u6807\u3002"
    elif confidence == "high":
        message = f"\u5df2\u5b9a\u4f4d\u5230 {nearest['name']} \u9644\u8fd1\uff0c\u8ddd\u79bb\u7ea6 {nearest_distance} \u7c73\u3002"
    elif confidence == "medium":
        message = f"\u5b9a\u4f4d\u63a5\u8fd1 {nearest['name']}\uff0c\u8ddd\u79bb\u7ea6 {nearest_distance} \u7c73\uff0c\u5efa\u8bae\u73b0\u573a\u590d\u6838\u3002"
    else:
        message = f"\u5df2\u83b7\u53d6\u5b9a\u4f4d\uff0c\u6700\u8fd1\u70b9\u4f4d\u4e3a {nearest['name']}\uff0c\u8ddd\u79bb\u7ea6 {nearest_distance} \u7c73\uff0c\u53ef\u4fe1\u5ea6\u504f\u4f4e\u3002"
    return {
        "items": items,
        "nearest": nearest,
        "accuracy": accuracy_value,
        "confidence": confidence,
        "insideScenic": inside_scenic,
        "message": message,
    }


def location_anchors(spots, route_order_key):
    anchors = [spot for spot in spots if spot.get("verifiedLocation") and has_coordinates(spot)]
    return sorted(
        anchors,
        key=lambda spot: (
            str(spot.get("mapZone") or "lingshan") != "lingshan",
            route_order_key(spot, str(spot.get("mapZone") or "lingshan")),
            spot.get("id") or 0,
        ),
    )


def resolve_location_code(raw_code, anchors):
    if not extract_location_code(raw_code).strip():
        return {
            "ok": False,
            "anchor": None,
            "confidence": "low",
            "message": "\u8bf7\u8f93\u5165\u70b9\u4f4d\u7801\u6216\u626b\u7801\u94fe\u63a5\u3002",
        }
    for spot in anchors:
        if spot_matches_location_code(spot, raw_code):
            return {
                "ok": True,
                "anchor": spot,
                "confidence": "high",
                "message": f"\u5df2\u6821\u51c6\u5230 {spot['name']}\u3002",
            }
    return {
        "ok": False,
        "anchor": None,
        "confidence": "low",
        "message": "\u672a\u627e\u5230\u5339\u914d\u7684\u70b9\u4f4d\u7801\uff0c\u8bf7\u6838\u5bf9\u6807\u8bc6\u724c\u3002",
    }
