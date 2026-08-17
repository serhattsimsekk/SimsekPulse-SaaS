import streamlit as st
import pandas as pd
from datetime import date

# 1. EN ÜSTTE OLMASI GEREKEN SAYFA YAPILANDIRMASI
st.set_page_config(
    page_title="Şimşek Lojistik | SimsekPulse Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 2. KURUMSAL ARAYÜZ & STREAMLİT İMZA TEMİZLİĞİ (CSS ENJEKSİYONU)
st.markdown("""
<style>
    /* Sağ üstteki Fork, GitHub, Varsayılan Menü ve Header'ı Gizle */
    .stAppHeader, #MainMenu, footer, header {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Sağ alttaki Streamlit Rozetlerini ve Toolbar'ı Yok Et */
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"],
    .viewerBadge_container__1vB22,
    .viewerBadge_link__1S137 {
        display: none !important;
    }

    /* Sayfa Üst Boşluğunu Optimize Et */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 2rem !important;
    }

    /* Koyu Tema Arka Plan Yapısı */
    .stApp {
        background-color: #0e1117;
        color: #e2e8f0;
    }

    /* Üst Kurumsal Header Banner */
    .brand-header {
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 1.2rem 1.8rem;
        border-radius: 12px;
        border: 1px solid #334155;
        margin-bottom: 1.5rem;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5);
        display: flex;
        align-items: center;
        justify-content: space-between;
    }

    /* İstatistik Kartları */
    .stat-card {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 0.8rem;
        text-align: center;
        font-weight: 600;
    }
    .stat-card-ozmal { border-left: 5px solid #2563eb; }
    .stat-card-destek { border-left: 5px solid #dc2626; }
    .stat-card-saha { border-left: 5px solid #16a34a; }

    /* Tab / Sekme Tasarımı */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #1e293b;
        padding: 6px;
        border-radius: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 6px;
        color: #94a3b8;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2563eb !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# 3. SOL MENÜ (SIDEBAR)
with st.sidebar:
    st.markdown("### ⚡ Şimşek Lojistik")
    st.markdown("**Operasyon Kontrol Merkezi**")
    st.divider()
    
    calisma_gunu = st.date_input("📅 Çalışma Günü (08:00 - 08:00):", date(2026, 8, 14))
    vardiya = st.selectbox("🕒 Aktif Vardiya:", ["08:00 - 16:00 (Gündüz)", "16:00 - 24:00 (Akşam)", "00:00 - 08:00 (Gece)"])
    
    st.divider()
    st.success("● Veritabanı Senkronize")
    st.info("SimsekPulse Engine v2.4")

# 4. ÜST KURUMSAL BANNER
st.markdown("""
<div class="brand-header">
    <div>
        <h2 style="color: #ffffff; margin: 0; font-size: 1.6rem; font-weight: 800; letter-spacing: -0.5px;">
            ⚡ ŞİMŞEK LOJİSTİK <span style="color: #38bdf8; font-size: 1.1rem; font-weight: 500;">| SimsekPulse Pro</span>
        </h2>
        <p style="color: #94a3b8; margin: 4px 0 0 0; font-size: 0.9rem;">
            Fleet, Dispatch & ERP Intelligence — Canlı Sevkiyat Matrisi & Saha Operasyon Yönetimi
        </p>
    </div>
    <div style="background: #1e293b; padding: 6px 14px; border-radius: 20px; border: 1px solid #10b981;">
        <span style="color: #34d399; font-weight: 600; font-size: 0.85rem;">● Sistem Canlı</span>
    </div>
</div>
""", unsafe_allow_html=True)

# 5. VARDIYA AMİRLERİ VE HIZLI ÖZET KARTLARI
col_amir, col_saha, col_ozmal, col_destek = st.columns([2.5, 1, 1, 1])

with col_amir:
    st.info("📋 **VARDİYA AMİRLERİ:** SİNAN GÜL // MUSTAFA ÇETİN")

with col_saha:
    st.markdown('<div class="stat-card stat-card-saha"><span style="color:#a7f3d0; font-size:0.8rem;">SAHA DURUMU</span><br><span style="font-size:1.2rem; color:white;">AKTİF</span></div>', unsafe_allow_html=True)

with col_ozmal:
    st.markdown('<div class="stat-card stat-card-ozmal"><span style="color:#bfdbfe; font-size:0.8rem;">ÖZ MAL (FİLO)</span><br><span style="font-size:1.2rem; color:white;">12 ARAÇ</span></div>', unsafe_allow_html=True)

with col_destek:
    st.markdown('<div class="stat-card stat-card-destek"><span style="color:#fca5a5; font-size:0.8rem;">DESTEK (DIŞ)</span><br><span style="font-size:1.2rem; color:white;">3 ARAÇ</span></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 6. OPERASYONEL SEKMELER (TABS)
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📄 GÜNCEL SEVKİYAT (Excel Matris)",
    "📊 24 Saatlik Şoför Karnesi",
    "🎨 Tedarikçi & Dorse Renk Matrisi",
    "🏛️ Öz Mal Garaj & Toplu Ekleme",
    "🔄 Vardiya Şoför Değişimi",
    "💰 Finans & Raporlama"
])

with tab1:
    st.subheader("📋 Canlı Sevkiyat Matrisi")
    matris_data = {
        "Plaka": ["31ANC225", "34ABC123", "35XYZ987", "06DEF456"],
        "Sürücü": ["Ahmet Yılmaz", "Mehmet Kaya", "Ali Demir", "Hasan Şahin"],
        "Araç Tipi": ["Öz Mal", "Destek (Dış)", "Öz Mal", "Destek (Dış)"],
        "Yük / Hammadde": ["Silis Kumu", "Endüstriyel Hammadde", "Çimento", "Dökme Yük"],
        "Giriş Saati": ["08:30", "09:15", "10:00", "10:45"],
        "Durum": ["Yolda", "Yüklemede", "Tamamlandı", "Beklemede"]
    }
    df = pd.DataFrame(matris_data)
    st.dataframe(df, use_container_width=True)

with tab2:
    st.subheader("📊 24 Saatlik Şoför Karnesi ve Performans")
    st.write("Sürücülerin vardiya içi mola, çalışma ve yükleme süreleri takibi.")

with tab3:
    st.subheader("🎨 Tedarikçi & Dorse Renk Matrisi")
    st.write("Dorse tipleri ve dış tedarikçi araçlarının renk kodlu canlı haritası.")

with tab4:
    st.subheader("🏛️ Öz Mal Garaj & Toplu Araç Yönetimi")
    st.write("Filoda bulunan araçların garaj bakım ve aktiflik durumları.")

with tab5:
    st.subheader("🔄 Vardiya Şoför Değişimi Kontrolü")
    st.write("Vardiya devir teslimlerinde şoför ve zimmet değişiklik paneli.")

with tab6:
    st.subheader("💰 Finans & Raporlama Modülü")
    st.write("Lojistik hakedişler, harcamalar ve operasyon verimlilik istatistikleri.")
