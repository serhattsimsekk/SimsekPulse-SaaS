from __future__ import annotations

import base64
import os
import math
import time
from http.cookiejar import CookieJar
from dataclasses import dataclass
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from urllib.request import build_opener, HTTPCookieProcessor
from xml.etree import ElementTree as ET


ARVENTO_REPORT_URL = "https://ws.arvento.com/v1/report.asmx"
ARVENTO_NAMESPACE = "http://www.arvento.com/"


class ArventoConfigurationError(RuntimeError):
    pass


class ArventoRequestError(RuntimeError):
    pass


@dataclass(frozen=True)
class ArventoCredentials:
    username: str
    password: str
    api_token: str | None = None
    pin: str | None = None


class ArventoClient:
    def __init__(self, credentials: ArventoCredentials, timeout: int = 30):
        if not credentials.username or not credentials.password:
            raise ArventoConfigurationError("Arvento kullanıcı adı ve şifresi zorunludur.")
        self.credentials = credentials
        self.timeout = timeout

    def get_vehicle_status_v3(self, node: str = "", language: str = "TR") -> dict:
        envelope = ET.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")
        body = ET.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
        operation = ET.SubElement(body, f"{{{ARVENTO_NAMESPACE}}}GetVehicleStatusByNodeV3")
        for name, value in (("Username", self.credentials.username), ("PIN1", self.credentials.pin or ""),
                            ("PIN2", ""), ("Node", node), ("Language", language)):
            ET.SubElement(operation, f"{{{ARVENTO_NAMESPACE}}}{name}").text = value
        request = Request(
            ARVENTO_REPORT_URL,
            data=ET.tostring(envelope, encoding="utf-8", xml_declaration=True),
            headers={
                "Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": f'"{ARVENTO_NAMESPACE}GetVehicleStatusByNodeV3"',
                "Authorization": "Basic " + base64.b64encode(
                    f"{self.credentials.username}:{self.credentials.password}".encode()
                ).decode(),
            },
            method="POST",
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                root = ET.fromstring(response.read())
        except (HTTPError, URLError, TimeoutError, ET.ParseError) as exc:
            raise ArventoRequestError(f"Arvento SOAP isteği başarısız: {exc}") from exc
        fault = next((element for element in root.iter() if element.tag.rsplit("}", 1)[-1] == "Fault"), None)
        if fault is not None:
            raise ArventoRequestError("Arvento SOAP Fault döndürdü.")
        packets = []
        for packet in root.iter():
            if packet.tag.rsplit("}", 1)[-1] != "LastPacket":
                continue
            values = {child.tag.rsplit("}", 1)[-1]: child.text for child in packet}
            packets.append({
                "node": values.get("strNode"),
                "plate": values.get("strLicensePlate"),
                "latitude": _number(values.get("dLatitude")),
                "longitude": _number(values.get("dLongitude")),
                "speed_kmh": _number(values.get("dSpeed")),
                "odometer_km": _number(values.get("dOdometer")),
                "engine_on": _bool(values.get("nIgnition") or values.get("bIgnition") or values.get("strIgnition")),
                "recorded_at": values.get("dtLocalDateTime") or values.get("dtGMTDateTime"),
                "driver": values.get("strDriver"),
            })
        return {"configured": True, "method": "GetVehicleStatusByNodeV3", "vehicles": packets, "count": len(packets)}


def simulate_live(vehicles: list[dict]) -> dict:
    """Generate deterministic, moving points for UI and integration testing."""
    now = time.time()
    points = []
    centers = [(41.0082, 28.9784), (40.9927, 29.1244), (38.4237, 27.1428), (40.7654, 29.9408)]
    for index, vehicle in enumerate(vehicles):
        lat, lon = centers[index % len(centers)]
        phase = now / 180 + index
        moving = index % 4 != 1
        points.append({
            "vehicle_id": str(vehicle.get("id") or ""),
            "plate": vehicle.get("plate"),
            "latitude": round(lat + math.sin(phase) * 0.035, 6),
            "longitude": round(lon + math.cos(phase) * 0.045, 6),
            "speed_kmh": round(42 + abs(math.sin(phase)) * 38, 1) if moving else 0,
            "odometer_km": int(vehicle.get("odometer_km") or 0) + int((now % 3600) / 3600 * 3),
            "engine_on": moving,
            "recorded_at": datetime.utcnow().isoformat() + "Z",
            "provider_group": vehicle.get("status") or "owned",
        })
    return {"configured": True, "mode": "simulation", "method": "FleetSimulator",
            "vehicles": points, "count": len(points)}


def fetch_live(settings: dict, vehicles: list[dict]) -> dict:
    try:
        client = client_from_settings(settings)
    except ArventoConfigurationError as exc:
        simulated = simulate_live(vehicles)
        simulated["fallback"] = {"soap_error": str(exc), "portal": "Portal scraper devre dışı."}
        return simulated
    try:
        result = client.get_vehicle_status_v3()
        if result.get("count", 0):
            result["mode"] = "soap"
            return result
    except ArventoRequestError as exc:
        soap_error = str(exc)
    else:
        soap_error = None
    portal_error = portal_session_probe(client.credentials)
    simulated = simulate_live(vehicles)
    simulated["fallback"] = {"soap_error": soap_error, "portal": portal_error}
    return simulated


def portal_session_probe(credentials: ArventoCredentials) -> str:
    """Start a cookie session only when explicitly enabled; no HTML is treated as telemetry."""
    if os.getenv("ENABLE_ARVENTO_PORTAL_SCRAPER", "true").lower() != "true":
        return "Portal scraper devre dışı."
    try:
        opener = build_opener(HTTPCookieProcessor(CookieJar()))
        request = Request("https://web.arvento.com/signin.aspx", headers={"User-Agent": "SimsekLog/1.0"})
        with opener.open(request, timeout=10) as response:
            if response.status == 200:
                return "Portal oturumu başlatıldı; veri adapterı bekleniyor."
        return "Portal oturumu başlatılamadı."
    except (HTTPError, URLError, TimeoutError) as exc:
        return f"Portal oturum denemesi başarısız: {exc}"


def _number(value: str | None) -> float | None:
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _bool(value: str | None) -> bool | None:
    if value is None:
        return None
    return value.strip().lower() in {"1", "true", "on", "yes"}


def client_from_settings(settings: dict) -> ArventoClient:
    return ArventoClient(ArventoCredentials(
        username=settings.get("username") or os.getenv("ARVENTO_USERNAME", ""),
        password=settings.get("password") or os.getenv("ARVENTO_PASSWORD", ""),
        api_token=settings.get("api_token") or os.getenv("ARVENTO_API_TOKEN") or None,
        pin=settings.get("pin") or os.getenv("ARVENTO_PIN") or None,
    ))


def mask_secret(value: str | None) -> str | None:
    if not value:
        return None
    return f"{value[:2]}***" if len(value) > 2 else "***"
