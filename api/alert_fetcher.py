import requests
from annotated_types import Timezone
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from numba.core.ir import Global
from numba.core.types import none
from pytz import utc
from shapely.geometry import Point, Polygon


ALL_ALERTS = None

PROVINCE_OFFICES = {
    "ON": "CWTO",
    "QC": "CWUL",
    "BC": "CWVR",
    "AB": "CWWG",
    "MB": "CWWG",
    "SK": "CWWG",
    "NS": "CWHX",
    "NB": "CWHX",
    "PE": "CWHX",
    "NL": "CWUL"
}

# Simplified bounding polygons (rough provincial bounding boxes)
PROVINCE_POLYGONS = {
    "ON": Polygon([(-95, 41), (-74, 41), (-74, 57), (-95, 57)]),
    "QC": Polygon([(-80, 44), (-57, 44), (-57, 63), (-80, 63)]),
    "BC": Polygon([(-139, 48), (-114, 48), (-114, 60), (-139, 60)]),
    "AB": Polygon([(-120, 49), (-110, 49), (-110, 60), (-120, 60)]),
    "MB": Polygon([(-102, 49), (-89, 49), (-89, 60), (-102, 60)]),
    "SK": Polygon([(-110, 49), (-101, 49), (-101, 60), (-110, 60)]),
    "NS": Polygon([(-66.5, 43), (-59, 43), (-59, 47), (-66.5, 47)]),
    "NB": Polygon([(-69, 45), (-63, 45), (-63, 49), (-69, 49)]),
    "PE": Polygon([(-64.5, 45.8), (-62, 45.8), (-62, 47.2), (-64.5, 47.2)]),
    "NL": Polygon([(-61, 46), (-52, 46), (-52, 61), (-61, 61)])
}

PROVINCE_TIMEZONES = {
    "ON": "America/Toronto",
    "QC": "America/Toronto",
    "BC": "America/Vancouver",
    "AB": "America/Edmonton",
    "MB": "America/Winnipeg",
    "SK": "America/Regina",
    "NS": "America/Halifax",
    "NB": "America/Halifax",
    "PE": "America/Halifax",
    "NL": "America/St_Johns"
}

ALERT_NAMES_BUCKET = {
    "weather": "Special Weather Statement",
    "fog": "Fog Advisory",
    "cold": "Extreme Cold Warning",
    "freezing drizzle": "Freezing Drizzle Advisory",
    "freezing rain": "Freezing Rain Warning",
    "arctic outflow": "Arctic Outflow Warning",
    "snowfall": "Snowfall Warning",
    "blowing snow": "Blowing Snow Advisory",
    "winter storm": "Winter Storm Watch",
    "snow squall": "Snow Squall Warning",
    "wind": "Strong Wind Warning",
}


def _get_office_dirs(base_url):
    html = requests.get(base_url).text
    soup = BeautifulSoup(html, "html.parser")
    return [
        base_url + a["href"]
        for a in soup.find_all("a", href=True)
        if a["href"].startswith("C")
    ]


def _get_time_dirs(office_dir):
    html = requests.get(office_dir).text
    soup = BeautifulSoup(html, "html.parser")

    time_dirs = [
        office_dir + a["href"]
        for a in soup.find_all("a", href=True)
        if a["href"].endswith("/") and a["href"].strip("/").isdigit()
    ]

    # Sort newest to oldest based on the numeric folder name
    return sorted(
        time_dirs,
        key=lambda url: int(url.rstrip("/").split("/")[-1]),
        reverse=True,
    )


def _parse_alert_cap(alert_url, seen_types, tz):
    alert_xml = requests.get(alert_url).content
    root = ET.fromstring(alert_xml)

    parsed_alerts = []

    for info in root.findall(".//{*}info"):
        lang = info.find(".//{*}language")
        if lang is None or lang.text != "en-CA":
            continue

        event_raw = info.find(".//{*}event").text
        event = ALERT_NAMES_BUCKET.get(event_raw, event_raw)

        if event in seen_types:
            continue

        expires_el = info.find(".//{*}expires")
        if expires_el is not None and expires_el.text:
            try:
                expires = datetime.fromisoformat(expires_el.text.replace("Z", "+00:00"))
                expires = expires.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        if expires < datetime.now(timezone.utc):
            continue

        onset_el = info.find(".//{*}onset")

        if onset_el is not None and onset_el.text:
            try:
                onset = datetime.fromisoformat(onset_el.text.replace("Z", "+00:00"))
                onset.replace(tzinfo=timezone.utc)
            except Exception:
                pass

        description_el = info.find(".//{*}description")
        description = description_el.text if description_el is not None else ""

        urgency_el = info.find(".//{*}urgency")
        urgency = urgency_el.text if urgency_el is not None else ""

        severity_el = info.find(".//{*}severity")
        severity = severity_el.text if severity_el is not None else ""

        instruction_el = info.find(".//{*}instruction")
        instruction = instruction_el.text if instruction_el is not None else ""

        areas = [
            area_name
            for area in info.findall(".//{*}area")
                for area_desc in area.findall(".//{*}areaDesc")
                    for area_name in area_desc.text.split(" - ")
        ]

        polygons = []
        for area in info.findall(".//{*}area"):
            for area_poly in area.findall(".//{*}polygon"):
                if not area_poly.text:
                    continue
                coords = []
                for cord in area_poly.text.strip().split():
                    parts = cord.split(",")
                    if len(parts) != 2:
                        continue
                    lat, lon = parts
                    coords.append((float(lon), float(lat)))
                if len(coords) >= 3:
                    polygons.append(Polygon(coords))

        parsed_alerts.append({
            "type": event.strip(),
            "description": description,
            "urgency": urgency,
            "severity": severity,
            "instruction": instruction,
            "areas": areas,
            "polygons": polygons,
            "onset": onset,
            "expires": expires,
            "timezone": tz
        })

    return parsed_alerts

def _detect_province_for_coords(lat, lon):
    point = Point(lon, lat)
    for prov, polygon in PROVINCE_POLYGONS.items():
        if polygon.contains(point):
            return prov
    return None


def _get_all_alerts(office_code, province):
    tz = PROVINCE_TIMEZONES.get(province)
    date = datetime.now(ZoneInfo(tz)).strftime("%Y%m%d")
    base = f"https://dd.weather.gc.ca/{date}/WXO-DD/alerts/cap/{date}/"
    office_dir = base + f"{office_code}/"
    all_alerts = []

    if office_dir:
        print("\n-------------------------------\n" + office_dir)
        time_dirs = _get_time_dirs(office_dir)
        seen_types = set()

        for time_dir in time_dirs:
            print("\n- Time_dir: ", time_dir.split("/")[-2])
            html = requests.get(time_dir).text
            soup = BeautifulSoup(html, "html.parser")

            alert_urls = [
                time_dir + a["href"]
                for a in soup.find_all("a", href=True)
                if a["href"].endswith(".cap")
            ]

            for alert_url in alert_urls:
                parsed = _parse_alert_cap(alert_url, seen_types, tz)
                for alert in parsed:
                    if not alert:
                        continue

                    alert_type = alert["type"]
                    print("\n" + alert_type)

                    all_alerts.append(alert)
                    seen_types.add(alert_type)

    return all_alerts


def get_alerts_for_coords(lat, lon):
    """
    Returns a list of alert dicts affecting the given coordinates.
    Each alert includes type, description, urgency, severity, instruction, and areas.
    """
    point = Point(lon, lat)
    matching_alerts = []

    province = _detect_province_for_coords(lat, lon)
    if not province:
        return []

    office_code = PROVINCE_OFFICES.get(province)
    if not office_code:
        return []

    alerts = _get_all_alerts(office_code, province)
    print_alerts(alerts)

    for alert in alerts :
        for polygon in alert["polygons"]:
            if polygon.contains(point) or polygon.buffer(0.05).contains(point):
                matching_alerts.append(alert)
                break

    return matching_alerts

def print_alerts(alerts):
    est = ZoneInfo("America/Toronto")

    for alert in alerts:
        print("\n" + alert["type"])

        expires = alert.get("expires")
        onset = alert.get("onset")
        if expires:
            expires_est = expires.astimezone(est)
        else:
            print("Expires: Unknown")

        if onset:
            onset_est = onset.astimezone(est)
        else:
            print("Onset: Unknown")

        print("Event from " + onset_est.strftime("%b %d, %H:%M") + " to " + expires_est.strftime("%b %d, %H:%M"))
        print("Severity: " + alert["severity"])