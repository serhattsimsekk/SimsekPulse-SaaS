import streamlit as st
import pandas as pd
from datetime import date

# 1. EN ÜSTTE PAGE CONFIG
st.set_page_config(
    page_title="Şimşek Lojistik | SimsekPulse Enterprise",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. GLOBAL ENTERPRISE SAAS STİL ENJEKSİYONU (CSS)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    /* Global Streamlit Elemanlarını & Rozetlerini Sıfırla */
    .stAppHeader, #MainMenu, footer, header,
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"],
    .viewerBadge_container__1vB22,
    .viewerBadge_link__1S137 {
        display: none !important;
        visibility: hidden !important;
    }

    /* Sayfa Yerleşimi ve Tipografi */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background-color: #080C14;
        color: #F1F5F9;
    }
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
        max-width: 98% !important;
    }

    /* Sol Menü (Sidebar) Kurumsal Tasarım */
    [data-testid="stSidebar"] {
        background-color: #0F172A !important;
        border-right: 1px solid rgba(255, 255, 255, 0.08) !important;
    }

    /* Top Brand Hero Banner */
    .hero-banner {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.25rem 1.75rem;
        margin-bottom: 1.25rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
    }
    .brand-title {
        color: #FFFFFF;
        font-size: 1.5rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .brand-subtitle {
        color: #94A3B8;
        font-size: 0.875rem;
        margin-top: 4px;
        font-weight: 400;
    }

    /* Enterprise KPI Kartları */
    .kpi-card {
        background: rgba(15, 23, 42, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 1rem 1.25rem;
        transition: all 0.2s ease;
    }
    .kpi-card:hover {
        border-color: rgba(56, 189, 248, 0.4);
        transform: translateY(-2px);
    }
    .kpi-label {
        color: #64748B;
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .kpi-value {
        color: #F8FAFC;
        font-size: 1.5rem;
        font-weight: 700;
        margin-top: 4px;
    }
    .kpi-trend {
        font-size: 0.75rem;
        font-weight: 600;
        margin-top: 4px;
    }

    /* Tab / Navigasyon Barı */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #0F172A;
        padding: 6px;
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.05);
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        border-radius: 8px;
        color: #94A3B8;
        font-weight: 600;
        font-size: 0.875rem;
        padding: 0 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #0284C7 !important;
        color: #FFFFFF !important;
        box-shadow: 0 4px 12px rgba(2, 132, 199, 0.3);
    }

    /* HTML Özel Matris Tablosu (Pills & Status) */
    .custom-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        background: #0F172A;
        border-radius: 12px;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.08);
        margin-top: 10px;
    }
    .custom-table th {
        background: #1E293B;
        color: #94A3B8;
        font-weight: 600;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 14px 18px;
        text-align: left;
        border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    }
    .custom-table td {
        padding: 14px 18px;
        color: #E2E8F0;
        font-size: 0.9rem;
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .custom-table tr:last-child td {
        border-bottom: none;
    }
    .custom-table tr:hover td {
        background-color: rgba(255, 255, 255, 0.02);
    }

    /* Status Pills */
    .badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-transit { background: rgba(14, 165, 233, 0.15); color: #38BDF8; border: 1px solid rgba(14, 165, 233, 0.3); }
    .badge-loading { background: rgba(245, 158, 11, 0.15); color: #FBBF24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .badge-done { background: rgba(16, 185, 129, 0.15); color: #34D399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .badge-waiting { background: rgba(239, 68, 68, 0.15); color: #F87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .badge-ozmal { background: rgba(99, 102, 241, 0.15); color: #818CF8; border: 1px solid rgba(99, 102, 241, 0.3); }
    .badge-destek { background: rgba(148, 163, 184, 0.15); color: #CBD5E1; border: 1px solid rgba(148, 163, 184, 0.3); }
</style>
""", unsafe_allow_html=True)

# 3. SOL YAN MENÜ (ENTERPRISE SIDEBAR)
with st.sidebar:
    st.markdown("""
        <div style="padding: 10px 0;">
            <h3 style="color:#FFF; margin:0; font-size:1.2rem; font-weight:800;">⚡ ŞİMŞEK LOGISTICS</h3>
            <p style="color:#64748B; margin:2px 0 0 0; font-size:0.75rem; font-weight:600;">ENTERPRISE DISPATCH PLATFORM</p>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    calisma_gunu = st.date_input("📅 Operasyon Tarihi:", date(2026, 8, 17))
    vardiya = st.selectbox("🕒 Aktif Vardiya:", ["08:00 - 16:00 (Gündüz)", "16:00 - 24:00 (Akşam)", "00:00 - 08:00 (Gece)"])
    bolge = st.multiselect("📍 Bölge Filtresi:", ["Marmara", "Ege", "İç Anadolu", "Liman Operasyon"], default=["Marmara", "Ege"])
    
    st.divider()
    st.markdown("""
        <div style="background:rgba(16, 185, 129, 0.1); border:1px solid rgba(16, 185, 129, 0.2); border-radius:8px; padding:10px; text-align:center;">
            <span style="color:#34D399; font-size:0.8rem; font-weight:600;">● Live Cloud Data Sync</span><br>
            <span style="color:#64748B; font-size:0.7rem;">SimsekPulse Core v3.0</span>
        </div>
    """, unsafe_allow_html=True)

# 4. ÜST HERO BANNER
st.markdown("""
<div class="hero-banner">
    <div>
        <div class="brand-title">
            <span>⚡ ŞİMŞEK LOJİSTİK</span>
            <span style="background: #0284C7; color: #FFF; font-size: 0.65rem; padding: 2px 8px; border-radius: 12px; font-weight: 700;">PRO ENTERPRISE</span>
        </div>
        <div class="brand-subtitle">
            Canlı Fleet Matrisi, Dökme Hammadde & Saha Operasyon Yönetim Merkezi
        </div>
    </div>
    <div style="display:flex; align-items:center; gap:12px;">
        <div style="text-align:right;">
            <div style="color:#34D399; font-size:0.85rem; font-weight:700;">● SYSTEM ONLINE</div>
            <div style="color:#64748B; font-size:0.75rem;">Latency: 14ms</div>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. METRİK VE KPI KARTLARI
c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Vardiya Amiri</div>
        <div style="color:#F1F5F9; font-size:0.95rem; font-weight:700; margin-top:6px;">Sinan Gül</div>
        <div class="kpi-trend" style="color:#64748B;">Yrd: M. Çetin</div>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Saha Durumu</div>
        <div class="kpi-value" style="color:#34D399;">AKTİF</div>
        <div class="kpi-trend" style="color:#34D399;">↑ %100 Kapasite</div>
    </div>
    """, unsafe_allow_html=True)

with c3:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Öz Mal (Filo)</div>
        <div class="kpi-value">18 Araç</div>
        <div class="kpi-trend" style="color:#38BDF8;">16 Seferde</div>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Destek (Dış)</div>
        <div class="kpi-value">7 Araç</div>
        <div class="kpi-trend" style="color:#FBBF24;">5 Yüklemede</div>
    </div>
    """, unsafe_allow_html=True)

with c5:
    st.markdown("""
    <div class="kpi-card">
        <div class="kpi-label">Günlük Tonaj</div>
        <div class="kpi-value">1,420 Ton</div>
        <div class="kpi-trend" style="color:#34D399;">↑ %12 Hedef Üstü</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 6. OPERASYONEL TABS (SEKMELER)
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 CANLI SEVKİYAT MATRİSİ",
    "🚚 FİLO & SÜRÜCÜ KARNESİ",
    "🎨 DORSE & RENK MATRİSİ",
    "🏛️ GARAJ & BAKIM KONTROL",
    "📈 FİNANS & OPERASYON RAPORU"
])

with tab1:
    st.markdown("""
    <table class="custom-table">
        <thead>
            <tr>
                <th>PLAKA</th>
                <th>SÜRÜCÜ</th>
                <th>ARAÇ TİPİ</th>
                <th>YÜK / HAMMADDE</th>
                <th>ÇIKIŞ - VARDIŞ</th>
                <th>GİRİŞ SAATİ</th>
                <th>OPERASYON DURUMU</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><b>31ANC225</b></td>
                <td>Ahmet Yılmaz</td>
                <td><span class="badge badge-ozmal">Öz Mal</span></td>
                <td>Silis Kumu (Dökme)</td>
                <td>Dilovası ➔ Gebze</td>
                <td>08:30</td>
                <td><span class="badge badge-transit">● Yolda</span></td>
            </tr>
            <tr>
                <td><b>34ABC123</b></td>
                <td>Mehmet Kaya</td>
                <td><span class="badge badge-destek">Destek</span></td>
                <td>Endüstriyel Hammadde</td>
                <td>Liman Kuyu ➔ Aliağa</td>
                <td>09:15</td>
                <td><span class="badge badge-loading">● Yüklemede</span></td>
            </tr>
            <tr>
                <td><b>35XYZ987</b></td>
                <td>Ali Demir</td>
                <td><span class="badge badge-ozmal">Öz Mal</span></td>
                <td>Çimento / Bigbag</td>
                <td>Konya ➔ Afyon</td>
                <td>10:00</td>
                <td><span class="badge badge-done">✓ Tamamlandı</span></td>
            </tr>
            <tr>
                <td><b>06DEF456</b></td>
                <td>Hasan Şahin</td>
                <td><span class="badge badge-destek">Destek</span></td>
                <td>Buğday / Arpa Sevkiyatı</td>
                <td>Bandırma ➔ Bursa</td>
                <td>10:45</td>
                <td><span class="badge badge-waiting">⏳ Kantarda Bekliyor</span></td>
            </tr>
            <tr>
                <td><b>41LGT889</b></td>
                <td>Mustafa Çelik</td>
                <td><span class="badge badge-ozmal">Öz Mal</span></td>
                <td>Dökme Kuru Yük</td>
                <td>Gemlik ➔ İnegöl</td>
                <td>11:20</td>
                <td><span class="badge badge-transit">● Yolda</span></td>
            </tr>
        </tbody>
    </table>
    """, unsafe_allow_html=True)

with tab2:
    st.subheader("🚚 Sürücü Performans & Vardiya Analizi")
    st.info("Canlı GPS ve dijital takoğraf verileri ile sürücü sürüş/mola zamanı takibi.")

with tab3:
    st.subheader("🎨 Dış Tedarikçi & Dorse Renk Haritası")
    st.write("Dorse türlerine göre dinamik renk kategorizasyonu.")

with tab4:
    st.subheader("🏛️ Öz Mal Garaj & Teknik Servis Durumu")
    st.write("Periyodik bakım zamanı gelen çekici ve dorse takip listesi.")

with tab5:
    st.subheader("📈 Operasyonel Finans ve Hakediş Raporları")
    st.write("Sefer başı maliyet, yakıt tüketim oranları ve müşteri hakediş matrisi.")
