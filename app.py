import streamlit as st
import pandas as pd
import sqlite3
import os
import streamlit.components.v1 as components
from datetime import datetime
from collections import Counter
import folium
from streamlit_folium import st_folium

# =========================================================
# 1. SAYFA YAPILANDIRMASI
# =========================================================
st.set_page_config(
    page_title="ŞimşekLog | Oztrans-Style Enterprise ERP",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- JAVASCRIPT: STREAMLIT ROZETLERİNİ SİLME ---
components.html("""
<script>
    function removeBadges() {
        try {
            const parentDoc = window.parent.document;
            const selectors = [
                'div[class*="viewerBadge"]', 'div[class*="profileContainer"]',
                'div[class*="stAppFooter"]', 'footer', '[data-testid="stStatusWidget"]',
                '[data-testid="stDecoration"]', 'a[href*="streamlit.io"]', 'a[href*="github.com"]'
            ];
            selectors.forEach(selector => {
                parentDoc.querySelectorAll(selector).forEach(el => {
                    el.style.setProperty('display', 'none', 'important');
                    el.style.setProperty('opacity', '0', 'important');
                    el.style.setProperty('visibility', 'hidden', 'important');
                });
            });
        } catch (e) {}
    }
    removeBadges();
    setInterval(removeBadges, 500);
</script>
""", height=0, width=0)

# =========================================================
# 2. GLOBAL CSS (OZTRANS TİPİ KOYU ERP TEMA & KART DÜZENİ)
# =========================================================
st.markdown("""
<style>
    #MainMenu, footer { visibility: hidden !important; }
    .stAppHeader { background: transparent !important; }
    
    [data-testid="stSidebarCollapseButton"] button,
    [data-testid="collapsedControl"] button {
        background-color: #0f172a !important;
        border: 1px solid #38bdf8 !important;
        color: #38bdf8 !important;
        border-radius: 8px !important;
    }

    [data-testid="stSidebar"] {
        background-color: #090d16 !important;
        border-right: 1px solid #1e293b !important;
    }

    .stApp { background-color: #050b14 !important; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }

    /* OZTRANS STİLİ YAN MENÜ SEÇİCİLERİ */
    div[data-testid="stRadio"] > div { gap: 4px; }
    div[data-testid="stRadio"] label {
        background-color: #0f172a; border: 1px solid #1e293b; border-radius: 6px;
        padding: 8px 12px; color: #94a3b8; font-weight: 600; cursor: pointer; transition: all 0.2s ease;
        font-size: 0.85rem;
    }
    div[data-testid="stRadio"] label:hover { border-color: #38bdf8; color: #ffffff; }
    div[data-testid="stRadio"] label[data-checked="true"] {
        background: linear-gradient(90deg, #1e293b, #0284c7) !important;
        border-left: 4px solid #38bdf8 !important; color: #ffffff !important;
    }

    /* OZTRANS KART SAYAÇLARI */
    .oz-card {
        background: #0f172a; border: 1px solid #1e293b; border-radius: 8px;
        padding: 12px; text-align: center; font-weight: bold; margin-bottom: 10px;
    }
    .oz-card-active { border-top: 3px solid #34d399; }
    .oz-card-spare { border-top: 3px solid #38bdf8; }
    .oz-card-fault { border-top: 3px solid #f43f5e; }
    .oz-card-nodriver { border-top: 3px solid #facc15; }
    .oz-card-sub { border-top: 3px solid #a855f7; }

    .vip-header {
        background: linear-gradient(135deg, #0a1120 0%, #1e293b 100%);
        border: 1px solid #334155; border-radius: 10px; padding: 12px 20px;
        margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center;
    }

    .vehicle-status-badge {
        display: inline-block; padding: 2px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: bold;
    }
    .badge-online { background: rgba(52, 211, 153, 0.15); color: #34d399; border: 1px solid #34d399; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. VERİTABANI VE VERİ YÖNETİMİ
# =========================================================
DB_FILE = "simsek_os.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS excel_matris (
            sira INTEGER PRIMARY KEY AUTOINCREMENT,
            mmk_hat1 TEXT, mmk_hat2 TEXT, eyap_silis TEXT,
            guub_cimento TEXT, isken_komur TEXT, tosyali_cevher TEXT,
            musteri_adi TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS filo (
            plaka TEXT PRIMARY KEY, dorse TEXT, tip TEXT,
            sofor_1 TEXT, sofor_2 TEXT, grup TEXT, durum TEXT, lat REAL, lon REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS kantar_fisleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grup_adi TEXT, gonderen TEXT, plaka TEXT,
            net_tonaj REAL, tesis TEXT, tarih_saat TEXT, durum TEXT
        )
    ''')
    
    # Varsayılan Filo Verileri (Oztrans Tipi Harita ve Pano Testi)
    c.execute("SELECT COUNT(*) FROM filo")
    if c.fetchone()[0] == 0:
        filo_ornek = [
            ("31 ANM 573", "31 KNS 37", "Damper", "ABDİL BAYRAMBEĞ", "", "MUHİTTİN ERGAN", "AKTİF", 36.58, 36.17),
            ("31 ANN 019", "31 KNS 14", "Damper", "MEHMET BOZOK", "", "MUHİTTİN ERGAN", "AKTİF", 36.60, 36.20),
            ("31 ANM 257", "31 KNS 88", "Sal", "HÜSEYİN TEMİZ", "", "KEMAL UZUNOĞLU", "KADEME", 36.55, 36.15),
            ("31 ANF 677", "31 KMN 99", "Lowbed", "HÜSEYİN F. PARLAK", "", "FATİH MAHMUTOĞLU", "YEDEK", 36.62, 36.22),
            ("31 AKL 543", "31 KNS 01", "Kılçık", "SİNAN GÜL", "", "SİNAN GÜL", "ŞOFÖRSÜZ", 36.50, 36.10)
        ]
        c.executemany("INSERT INTO filo (plaka, dorse, tip, sofor_1, sofor_2, grup, durum, lat, lon) VALUES (?,?,?,?,?,?,?,?,?)", filo_ornek)
        
    conn.commit()
    conn.close()

init_db()

def load_data(table):
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
    conn.close()
    return df

def save_data(df, table):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql(table, conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

if "df_excel" not in st.session_state: st.session_state.df_excel = load_data("excel_matris")
if "df_filo" not in st.session_state: st.session_state.df_filo = load_data("filo")
if "df_fisler" not in st.session_state: st.session_state.df_fisler = load_data("kantar_fisleri")

# =========================================================
# 4. OZTRANS TİPİ KATEGORİZE YAN MENÜ
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 15px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:900; letter-spacing: 1px;">⚡ ŞimşekLog</h2>
            <span style="color: #64748B; font-size: 0.75rem; font-weight:700;">OZTRANS ENTERPRISE ERP OS</span>
        </div>
    """, unsafe_allow_html=True)
    
    kullanici_rolu = st.selectbox(
        "👤 ROL KONTROLÜ:",
        ["👑 Patron (Yönetici)", "🏢 Departman Müdürü", "💼 Muhasebe", "🚚 Sevkiyatçı / Vardiya Amiri"],
        index=0
    )
    
    st.markdown("---")
    
    menu = st.radio(
        "MODÜLLER",
        [
            "📋 Hurda & Sal Tablosu (Pano)",
            "🟢 Canlı Sevkiyat Matrisi (Grid)",
            "🗺️ GPS & Arvento Harita Takibi",
            "📄 AI Beyanname Oluşturucu",
            "📱 WhatsApp Kantar Fişi Akışı",
            "🚍 Master Filo & Araç İşlemleri",
            "🛠️ Kademe & Bakım Yönetimi",
            "💼 Finans & Hakediş Paneli"
        ]
    )

# Üst Header
st.markdown(f"""
<div class="vip-header">
    <div>
        <h4 style="margin:0; color:#38bdf8; font-weight:800;">{menu.upper()}</h4>
        <span style="color:#94a3b8; font-size:0.8rem;">ŞimşekLog Kurumsal Saha & Filo Yönetim Portalı</span>
    </div>
    <div style="text-align:right;">
        <span style="color:#f8fafc; font-weight:bold; font-size:1rem;">{datetime.now().strftime("%d.%m.%Y")}</span><br>
        <span style="color:#34d399; font-size:0.75rem; font-weight:600;">ROL: {kullanici_rolu.upper()}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 5. DİNAMİK ERP MODÜLLERİ
# =========================================================

# --- MODÜL 1: HURDA & SAL TABLOSU (OZTRANS KART DÜZENİ) ---
if menu == "📋 Hurda & Sal Tablosu (Pano)":
    st.subheader("📋 Hurda & Sal Saha Araç Pano Görünümü")
    st.caption("Hurda ve Sal operasyonundaki araçların anlık durumlarına göre gruplandırılmış kart görünümü.")
    
    df_f = st.session_state.df_filo
    
    c_aktif = len(df_f[df_f['durum'] == 'AKTİF']) if 'durum' in df_f.columns else 0
    c_yedek = len(df_f[df_f['durum'] == 'YEDEK']) if 'durum' in df_f.columns else 0
    c_ariza = len(df_f[df_f['durum'] == 'KADEME']) if 'durum' in df_f.columns else 0
    c_soforsuz = len(df_f[df_f['durum'] == 'ŞOFÖRSÜZ']) if 'durum' in df_f.columns else 0
    
    # 5 ANA KATEGORİ KART SAYACI (OZTRANS ARAYÜZ BİREBİR)
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1: st.markdown(f'<div class="oz-card oz-card-active">📌 PLAKALAR<br><b style="font-size:1.4rem; color:#34d399;">{c_aktif}</b></div>', unsafe_allow_html=True)
    with k2: st.markdown(f'<div class="oz-card oz-card-spare">🔄 YEDEK ARAÇLAR<br><b style="font-size:1.4rem; color:#38bdf8;">{c_yedek}</b></div>', unsafe_allow_html=True)
    with k3: st.markdown(f'<div class="oz-card oz-card-fault">⚠️ ARIZALI ARAÇLAR<br><b style="font-size:1.4rem; color:#f43f5e;">{c_ariza}</b></div>', unsafe_allow_html=True)
    with k4: st.markdown(f'<div class="oz-card oz-card-nodriver">👤 ŞOFÖRSÜZ ARAÇLAR<br><b style="font-size:1.4rem; color:#facc15;">{c_soforsuz}</b></div>', unsafe_allow_html=True)
    with k5: st.markdown(f'<div class="oz-card oz-card-sub">🚜 TAŞERON ARAÇLAR<br><b style="font-size:1.4rem; color:#a855f7;">0</b></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 🚍 Saha Araç Kartları")
    
    if len(df_f) > 0:
        cols = st.columns(3)
        for idx, row in df_f.iterrows():
            with cols[idx % 3]:
                st.markdown(f"""
                <div style="background:#0f172a; border:1px solid #1e293b; border-radius:8px; padding:12px; margin-bottom:10px;">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <b style="color:#38bdf8; font-size:1.1rem;">🚛 {row['plaka']}</b>
                        <span class="vehicle-status-badge badge-online">{row['durum']}</span>
                    </div>
                    <hr style="border-color:#334155; margin:8px 0;">
                    <span style="color:#94a3b8; font-size:0.85rem;">
                        <b>Dorse:</b> {row['dorse']} ({row['tip']})<br>
                        <b>Şoför:</b> {row['sofor_1']}<br>
                        <b>Grup / Amir:</b> {row['grup']}
                    </span>
                </div>
                """, unsafe_allow_html=True)

# --- MODÜL 2: CANLI SEVKİYAT MATRİSİ ---
elif menu == "🟢 Canlı Sevkiyat Matrisi (Grid)":
    st.subheader("🟢 Canlı Sevkiyat Matrisi ve Grid Düzenleyici")
    df_ex = st.session_state.df_excel
    
    config = {
        "sira": st.column_config.NumberColumn("SIRA", disabled=True),
        "mmk_hat1": st.column_config.TextColumn("MMK PORT (HAT 1)", width="medium"),
        "mmk_hat2": st.column_config.TextColumn("MMK PORT (HAT 2)", width="medium"),
        "eyap_silis": st.column_config.TextColumn("EYAP LİMANI", width="medium"),
        "guub_cimento": st.column_config.TextColumn("GÜÜB LİMANI", width="medium"),
        "isken_komur": st.column_config.TextColumn("İSKEN SANTRAL", width="medium"),
        "tosyali_cevher": st.column_config.TextColumn("TOSYALI LİMANI", width="medium"),
    }
    
    edited = st.data_editor(df_ex, column_config=config, num_rows="dynamic", use_container_width=True, height=450, hide_index=True)
    if st.button("💾 Matris Verilerini Kaydet", type="primary", use_container_width=True):
        st.session_state.df_excel = edited
        save_data(edited, "excel_matris")
        st.success("✅ Matris verileri güncellendi!")

# --- MODÜL 3: GPS & ARVENTO HARİTA TAKİBİ (OZTRANS HARİTA BİREBİR) ---
elif menu == "🗺️ GPS & Arvento Harita Takibi":
    st.subheader("🗺️ Canlı GPS / Telematik ve Harita Takip Ekranı")
    st.caption("Arvento telematik cihazlarından çekilen anlık konum, hız, şoför ve CANBUS verileri.")
    
    df_f = st.session_state.df_filo
    
    m = folium.Map(location=[36.58, 36.17], zoom_start=11, tiles="CartoDB dark_matter")
    
    for _, r in df_f.iterrows():
        if pd.notnull(r['lat']) and pd.notnull(r['lon']):
            popup_html = f"""
            <div style="font-family:Segoe UI; font-size:12px;">
                <b>Plaka:</b> {r['plaka']}<br>
                <b>Şoför:</b> {r['sofor_1']}<br>
                <b>Durum:</b> {r['durum']}<br>
                <b>Sinyal:</b> Online (CANBUS Aktif)
            </div>
            """
            folium.Marker(
                location=[r['lat'], r['lon']],
                popup=popup_html,
                tooltip=r['plaka'],
                icon=folium.Icon(color="green" if r['durum'] == 'AKTİF' else "red", icon="truck", prefix="fa")
            ).add_to(m)
            
    st_folium(m, width=1200, height=500)

# --- MODÜL 4: AI BEYANNAME OLUŞTURUCU (VIDEODAKI BEYANNAME MODULU) ---
elif menu == "📄 AI Beyanname Oluşturucu":
    st.subheader("📄 Yapay Zekâ Destekli Beyanname ve Dilekçe Paneli")
    st.caption("Liman ve tesis geçişleri için otomatik kantar beyannamesi ve saha dilekçesi üretir.")
    
    with st.form("beyanname_formu"):
        b1, b2, b3 = st.columns(3)
        b_plaka = b1.text_input("Araç Plakası:").upper()
        b_tesis = b2.selectbox("Gideceği Tesis / Liman:", ["MMK PORT", "EYAP LİMANI", "GÜÜB LİMANI", "İSKEN SANTRAL", "TOSYALI LİMANI"])
        b_yuk = b3.text_input("Yük Cinsi:", value="Hurda / Dökme Yük")
        
        if st.form_submit_button("⚡ AI Beyanname Oluştur", type="primary", use_container_width=True):
            if b_plaka:
                st.success("✅ AI Beyanname Başarıyla Oluşturuldu!")
                metin = f"""[RESMİ KANTAR BEYANNAMESİ]\nTarih: {datetime.now().strftime('%d.%m.%Y %H:%M')}\nAraç Plakası: {b_plaka}\nTeslimat Adresi: {b_tesis}\nYük Tanımı: {b_yuk}\nDurum: Onaylandı (Sistem Tarafından Dijital İmzalandı)"""
                st.code(metin, language="text")
            else:
                st.warning("Lütfen plaka girin.")

# --- DİĞER MODÜLLER ---
else:
    st.info(f"ℹ️ **{menu}** modülü aktif ve veritabanı senkronizasyonundadır.")
