import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
from datetime import datetime
from shapely.geometry import Point, Polygon

ALERT_NAMES_BUCKET = {
    "weather": "Weather Advisory",
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


def _get_latest_time_dir(office_dir):
    html = requests.get(office_dir).text
    soup = BeautifulSoup(html, "html.parser")

    time_dirs = [
        office_dir + a["href"]
        for a in soup.find_all("a", href=True)
        if a["href"].endswith("/") and a["href"].strip("/").isdigit()
    ]

    return time_dirs[-1] if time_dirs else None


def _parse_alert_cap(alert_url):
    alert_xml = requests.get(alert_url).content
    root = ET.fromstring(alert_xml)

    parsed_alerts = []

    for info in root.findall(".//{*}info"):
        lang = info.find(".//{*}language")
        if lang is None or lang.text != "en-CA":
            continue

        event_raw = info.find(".//{*}event").text
        event = ALERT_NAMES_BUCKET.get(event_raw, event_raw)

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

        polygons = [
            Polygon([
                (float(lon), float(lat))
                for area_poly in area.findall(".//{*}polygon")
                for cord in area_poly.text.split(" ")
                for lat, lon in [cord.split(",")]
            ])
            for area in info.findall(".//{*}area")
        ]

        parsed_alerts.append({
            "type": event.strip(),
            "description": description,
            "urgency": urgency,
            "severity": severity,
            "instruction": instruction,
            "areas": areas,
            "polygons": polygons,
        })

    return parsed_alerts


def _get_all_alerts():
    date = datetime.today().strftime("%Y%m%d")
    base = f"https://dd.weather.gc.ca/{date}/WXO-DD/alerts/cap/{date}/"

    office_dirs = _get_office_dirs(base)
    all_alerts = []

    for office_dir in office_dirs:
        latest_dir = _get_latest_time_dir(office_dir)
        if not latest_dir:
            continue

        html = requests.get(latest_dir).text
        soup = BeautifulSoup(html, "html.parser")

        alert_urls = [
            latest_dir + a["href"]
            for a in soup.find_all("a", href=True)
            if a["href"].endswith(".cap")
        ]

        for alert_url in alert_urls:
            all_alerts.extend(_parse_alert_cap(alert_url))

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
            if polygon.contains(point):
                matching_alerts.append({
                    "type": alert["type"],
                    "description": alert["description"],
                    "urgency": alert["urgency"],
                    "severity": alert["severity"],
                    "instruction": alert["instruction"],
                    "areas": alert["areas"],
                })
                break

    return matching_alerts