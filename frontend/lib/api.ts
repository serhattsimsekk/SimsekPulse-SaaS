// `NEXT_PUBLIC_API_URL` Next.js tarafından DERLEME zamanında (next build)
// sabit bir metin olarak koda gömülür (bkz. frontend/Dockerfile ARG/ENV).
// Eğer bu değişken .env.production içinde tanımlanmamış/boş bırakılırsa,
// eskiden buraya sabit "http://localhost:8000" varsayılanı yazılıyordu.
// Prodüksiyonda bu, ziyaretçinin KENDİ tarayıcısından kendi bilgisayarındaki
// (localhost) 8000 portuna istek atmaya çalışmasına yol açar — orada hiçbir
// şey dinlemediği için istek asla backend'e ulaşmaz ve giriş formu "Giriş
// yapılıyor..." durumunda sonsuza kadar takılı kalır (ya da anlaşılmaz bir
// ağ hatası verir). nginx zaten "/api/" yolunu aynı alan adı (domain)
// üzerinden backend'e proxy'lediğinden, prodüksiyonda değişken boşsa
// GÖRECELİ (relative, aynı origin) bir taban kullanmak çok daha güvenlidir;
// yerel geliştirmede ise (NODE_ENV !== "production") eski localhost:8000
// varsayılanı korunur.
const rawBase = (process.env.NEXT_PUBLIC_API_URL || "").trim().replace(/\/+$/, "");
const base = rawBase || (process.env.NODE_ENV === "production" ? "" : "http://localhost:8000");

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = typeof window !== "undefined" ? window.localStorage.getItem("simseklog_access_token") : null;
  const headers = { ...(options?.headers || {}), ...(token ? { Authorization: "Bearer " + token } : {}) };
  let res: Response;
  try {
    res = await fetch(`${base}${path}`, { ...options, headers });
  } catch (networkError) {
    // fetch() CORS/DNS/bağlantı hatalarında bir Response DEĞİL, bir istisna
    // fırlatır. Bunu açıkça yakalayıp anlaşılır bir hataya çeviriyoruz;
    // aksi halde çağıran taraf (ör. login formu) neyin yanlış gittiğini
    // hiç bilmeden sonsuza kadar "yükleniyor" durumunda kalabilir.
    throw new Error(`Sunucuya bağlanılamadı (${base}${path}): ${(networkError as Error).message}`);
  }
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
