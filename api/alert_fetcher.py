import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from shapely.geometry import Point, Polygon


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


def _parse_alert_cap(alert_url, seen_types):
    alert_xml = requests.get(alert_url).content
    root = ET.fromstring(alert_xml)

    parsed_alerts = []

    for info in root.findall(".//{*}info"):
        lang = info.find(".//{*}language")
        if lang is None or lang.text != "en-CA":
            continue

        event_raw = info.find(".//{*}event").text
        event = ALERT_NAMES_BUCKET.get(event_raw, event_raw)

        expires_el = info.find(".//{*}expires")
        if expires_el is not None and expires_el.text:
            try:
                expires = datetime.fromisoformat(expires_el.text.replace("Z", "+00:00"))
            except Exception:
                pass

        if expires < datetime.now(timezone.utc):
            continue

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
            "expires": expires,
        })

    return parsed_alerts


def _get_all_alerts():
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    base = f"https://dd.weather.gc.ca/{date}/WXO-DD/alerts/cap/{date}/"

    office_dirs = _get_office_dirs(base)
    all_alerts = []

    for office_dir in office_dirs:
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
                parsed = _parse_alert_cap(alert_url, seen_types)
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

    for alert in _get_all_alerts():
        for polygon in alert["polygons"]:
            if polygon.contains(point) or polygon.buffer(0.05).contains(point):
                matching_alerts.append(alert)
                break

    return matching_alerts

def print_alerts(alerts):
    for alert in alerts:
        print("\n" + alert["type"])
        print("Expires: " + str(alert["expires"]))
        print("Severity: " + alert["severity"])
