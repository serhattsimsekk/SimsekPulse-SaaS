const base = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("simseklog_access_token") : null;
  const headers = { ...(options?.headers || {}), ...(token ? { Authorization: "Bearer " + token } : {}) };
  const res = await fetch(`${base}${path}`, { ...options, headers });
  if (res.status === 401 && typeof window !== "undefined") {
    window.localStorage.removeItem("simseklog_access_token");
    window.localStorage.removeItem("simseklog_principal");
    window.location.assign("/login");
  }
  if (!res.ok) throw new Error((await res.text()) || `Request failed (${res.status})`);
  return res.json();
}

export const api = {
  login: (payload: { tenant_code: string; email: string; password: string }) => request<any>("/api/v1/auth/login", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  branding: (tenantCode: string) => request<any>(`/api/v1/branding/${encodeURIComponent(tenantCode)}`),
  dashboard: () => request<any>("/api/v1/operations/dashboard"),
  telemetry: () => request<any[]>("/api/v1/operations/telemetry/latest"),
  issues: () => request<any[]>("/api/v1/operations/maintenance/issues"),
  parts: (tenant = "demo") => request<any[]>(`/api/v1/operations/maintenance/parts?tenant_id=${tenant}`),
  uploadReceipt: (data: FormData) => request<any>("/api/v1/receipts/ocr", { method: "POST", body: data }),
  uploadWeighbridge: (data: FormData) => request<any>("/api/v1/ocr/weighbridge", { method: "POST", body: data }),
  shiftReport: (hours = 8) => request<any>(`/api/v1/shifts/reports?hours=${hours}`),
  shiftHandover: (driverId: string, payload: { receiving_driver_id: string; notes?: string; vehicle_id?: string }) => request<any>(`/api/v1/operations/drivers/${encodeURIComponent(driverId)}/shift-handover`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  createIssue: (payload: object) => request<any>("/api/v1/operations/maintenance/issues", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  createBreak: (driver: string, payload: object) => request<any>(`/api/v1/drivers/${driver}/breaks`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  commandCenter: () => request<any>("/api/v1/command-center/master-dashboard"),
  operationMatrix: () => request<any[]>("/api/v1/command-center/operation-matrix"),
  heatmap: () => request<any>("/api/v1/command-center/heatmap"),
  liveTelemetry: () => request<any[]>("/api/v1/command-center/telemetry/live"),
  demurrageWarnings: () => request<any[]>("/api/v1/command-center/demurrage/early-warning"),
  profitabilityMap: () => request<any[]>("/api/v1/command-center/profitability-map"),
  carbonReport: () => request<any>("/api/v1/command-center/esg/carbon"),
  predictiveMaintenance: () => request<any[]>("/api/v1/command-center/maintenance/predictive"),
  normalizePlate: (plate: string) => request<any>("/api/v1/command-center/plate/normalize", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ plate }) }),
  formatTonnage: (tons: number) => request<any>("/api/v1/command-center/tonnage/format", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ tons }) }),
  tyreAnalytics: () => request<any>("/api/v1/field/tyre-analytics"),
  fuelAnomalies: () => request<any>("/api/v1/field/fuel-anomalies"),
  ecoScore: (driverId: string) => request<any>(`/api/v1/field/drivers/${encodeURIComponent(driverId)}/eco-score`),
  trackingLink: (tripId: string) => request<any>(`/api/v1/trips/${encodeURIComponent(tripId)}/tracking-link`, { method: "POST" }),
  vehicleTires: (vehicleId: string) => request<any>(`/api/v1/field/vehicles/${encodeURIComponent(vehicleId)}/tires`),
  arventoSettings: () => request<any>("/api/v1/arvento/settings"),
  saveArventoSettings: (payload: object) => request<any>("/api/v1/arvento/settings", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }),
  arventoLive: () => request<any>("/api/v1/arvento/live"),
};
