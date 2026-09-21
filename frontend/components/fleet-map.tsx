"use client";

import { useMemo } from "react";
import { MapContainer, Marker, Popup, TileLayer } from "react-leaflet";
import L from "leaflet";

export type TelemetryPoint = {
  vehicle_id?: string;
  plate?: string;
  latitude?: number | null;
  longitude?: number | null;
  speed_kmh?: number | null;
  engine_on?: boolean | null;
};

const fallback: TelemetryPoint[] = [
  { plate: "34 ABC 123", latitude: 40.9795, longitude: 28.705, speed_kmh: 64, engine_on: true },
  { plate: "06 XYZ 45", latitude: 40.765, longitude: 29.94, speed_kmh: 0, engine_on: false },
  { plate: "35 KLM 78", latitude: 38.43, longitude: 27.14, speed_kmh: 51, engine_on: true },
  { plate: "41 TIR 08", latitude: 40.78, longitude: 29.52, speed_kmh: 72, engine_on: true },
  { plate: "16 TRK 19", latitude: 40.19, longitude: 29.06, speed_kmh: 0, engine_on: false },
];

const vehicleIcon = (active: boolean) =>
  L.divIcon({
    className: "fleet-marker",
    html: `<span style="display:block;width:26px;height:26px;border-radius:50%;border:3px solid white;background:${active ? "#0f9f9a" : "#ed6a5a"};box-shadow:0 2px 8px rgba(19,34,56,.35)"></span>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });

export default function FleetMap({ telemetry = [] }: { telemetry?: TelemetryPoint[] }) {
  const points = useMemo(() => {
    const valid = telemetry.filter((item) => Number.isFinite(item.latitude) && Number.isFinite(item.longitude));
    return valid.length ? valid : fallback;
  }, [telemetry]);

  return (
    <MapContainer center={[40.75, 29.25]} zoom={7} scrollWheelZoom className="h-[300px] w-full">
      <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
      {points.map((point, index) => {
        const active = point.engine_on !== false && Number(point.speed_kmh || 0) > 0;
        return (
          <Marker key={`${point.vehicle_id || point.plate || "vehicle"}-${index}`} position={[Number(point.latitude), Number(point.longitude)] as [number, number]} icon={vehicleIcon(active)}>
            <Popup><strong>{point.plate || "Araç"}</strong><br />{active ? `${point.speed_kmh || 0} km/sa · Hareketli` : "Beklemede"}</Popup>
          </Marker>
        );
      })}
    </MapContainer>
  );
}
