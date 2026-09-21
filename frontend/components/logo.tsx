"use client";

export function Logo({ compact = false }: { compact?: boolean }) {
  return <div className="flex items-center gap-3">
    <svg width={compact ? 30 : 42} height={compact ? 30 : 42} viewBox="0 0 48 48" aria-label="ŞimşekLog logo" role="img">
      <defs><linearGradient id="bolt-gradient" x1="0" x2="1" y1="1" y2="0"><stop stopColor="#2563EB"/><stop offset=".55" stopColor="#38BDF8"/><stop offset="1" stopColor="#F59E0B"/></linearGradient></defs>
      <path d="M27 2 8 27h13l-3 19 22-28H27l4-16Z" fill="url(#bolt-gradient)"/>
      <path d="M4 33h9M35 9h9" stroke="#F59E0B" strokeWidth="2.5" strokeLinecap="round"/>
    </svg>
    {!compact && <div><div className="text-xl font-extrabold tracking-tight">ŞİMŞEK<span className="text-electric">LOG</span></div><div className="text-[9px] uppercase tracking-[.28em] text-slate-400">Fleet command</div></div>}
  </div>;
}
