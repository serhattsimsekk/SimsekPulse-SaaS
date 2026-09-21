"use client";

import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "../../lib/api";
import { Logo } from "../../components/logo";

export default function LoginPage() {
  const router = useRouter();
  const [form, setForm] = useState({ tenant_code: "", email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [brandLogo, setBrandLogo] = useState<string | null>(null);
  useEffect(() => { if (!form.tenant_code.trim()) { setBrandLogo(null); return; } api.branding(form.tenant_code.trim()).then(result => setBrandLogo(result.logo_data || null)).catch(() => setBrandLogo(null)); }, [form.tenant_code]);
  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const token = await api.login(form);
      localStorage.setItem("simseklog_access_token", token.access_token);
      localStorage.setItem("simseklog_principal", JSON.stringify({ tenant_id: token.tenant_id, tenant_code: form.tenant_code, role: token.role, department: token.department, email: form.email, logo_data: brandLogo }));
      router.replace("/");
    } catch {
      setError("Şirket kodu, e-posta veya şifre hatalı; şirket lisansı aktif olmayabilir.");
    } finally {
      setBusy(false);
    }
  };
  return <main className="grid min-h-screen bg-slate-950 lg:grid-cols-[1.15fr_.85fr]"><section className="relative hidden overflow-hidden bg-gradient-to-br from-slate-950 via-blue-950 to-blue-700 p-12 text-white lg:flex lg:flex-col lg:justify-between"><div className="absolute inset-0 opacity-20 grid-lines"/><div className="relative"><Logo/><p className="mt-20 max-w-xl text-5xl font-extrabold leading-tight">Filo hızını<br/><span className="text-sky-300">tek merkezden</span> yönetin.</p><p className="mt-6 max-w-lg text-slate-300">Canlı takip, güvenli operasyon ve finansal görünürlük. ŞimşekLog kapalı kurumsal platformuna hoş geldiniz.</p></div><div className="relative grid max-w-xl grid-cols-3 gap-4"><div className="rounded-2xl border border-white/10 bg-white/10 p-4"><p className="text-2xl font-bold">24/7</p><p className="text-xs text-slate-300">Canlı izleme</p></div><div className="rounded-2xl border border-white/10 bg-white/10 p-4"><p className="text-2xl font-bold">360°</p><p className="text-xs text-slate-300">Filo görünürlüğü</p></div><div className="rounded-2xl border border-white/10 bg-white/10 p-4"><p className="text-2xl font-bold">100%</p><p className="text-xs text-slate-300">Tenant izolasyonu</p></div></div></section><section className="flex items-center justify-center p-5 sm:p-10"><form onSubmit={submit} className="glass w-full max-w-md rounded-3xl p-8 shadow-2xl">
    <div className="mb-8"><div className="lg:hidden">{brandLogo ? <img src={brandLogo} alt="Şirket logosu" className="h-12 max-w-[190px] object-contain"/> : <Logo/>}</div><p className="mt-4 text-sm text-slate-500">Kapalı kurumsal giriş</p><h1 className="mt-2 text-2xl font-extrabold text-ink">Hesabınıza giriş yapın</h1></div>
    <div className="space-y-4"><label className="block text-sm font-semibold text-ink">Şirket Kodu<input required value={form.tenant_code} onChange={(e) => setForm({ ...form, tenant_code: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 outline-none focus:border-teal" placeholder="firma-kodu" /></label>
      <label className="block text-sm font-semibold text-ink">E-posta<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 outline-none focus:border-teal" placeholder="kullanici@firma.com" /></label>
      <label className="block text-sm font-semibold text-ink">Şifre<input required type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} className="mt-1 w-full rounded-xl border border-slate-200 px-3 py-3 outline-none focus:border-teal" /></label>
    </div>{error && <p className="mt-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</p>}<button disabled={busy} className="mt-6 w-full rounded-xl bg-teal py-3 font-bold text-white disabled:opacity-60">{busy ? "Giriş yapılıyor..." : "Giriş yap"}</button><p className="mt-5 text-center text-xs text-slate-400">Üyelik yalnızca SaaS Master Admin tarafından oluşturulur.</p>
  </form></section></main>;
}
