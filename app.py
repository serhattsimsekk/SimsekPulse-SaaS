import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# =========================================================
# 1. EN ÜSTTE OLMASI GEREKEN SAYFA YAPILANDIRMASI
# =========================================================
st.set_page_config(
    page_title="Şimşek Lojistik | Enterprise Dispatch Portal",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# 2. GLOBAL CSS ENJEKSİYONU (SOL MENÜ & SIFIR STREAMLİT İZİ)
# =========================================================
st.markdown("""
<style>
    /* Streamlit Üst Header, Menü ve Varsayılan Çubukları Gizleme */
    .stAppHeader, #MainMenu, footer, header {
        display: none !important;
        visibility: hidden !important;
    }

    /* Koyu Tema Arka Planı ve Sıfır Boşluk */
    .stApp {
        background-color: #080d1a !important;
        color: #f8fafc;
    }
    .block-container {
        padding: 1rem 1.5rem !important;
        max-width: 100% !important;
    }

    /* Sol Yan Menü (Sidebar) Özel Tasarımı */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1rem !important;
    }

    /* Sol Menü Radio Butonlarını Buton Kartlarına Dönüştürme */
    div[data-testid="stRadio"] > div {
        display: flex;
        flex-direction: column;
        gap: 6px;
    }
    div[data-testid="stRadio"] label {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px 14px;
        color: #94a3b8;
        font-weight: 600;
        cursor: pointer;
        transition: all 0.2s ease;
    }
    div[data-testid="stRadio"] label:hover {
        border-color: #38bdf8;
        color: #ffffff;
    }
    div[data-testid="stRadio"] label[data-checked="true"] {
        background-color: #0284c7 !important;
        border-color: #38bdf8 !important;
        color: #ffffff !important;
    }

    /* Header Banner */
    .excel-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155;
        border-radius: 10px;
        padding: 14px 22px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.4);
    }

    /* İstatistik Sayaç Kartları */
    .counter-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px 14px;
        text-align: center;
    }

    /* SAĞ ALTTAN TÜM ROZETLERİ VE PROFİL İKONLARINI SİLME */
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"],
    [data-testid="stActionButton"],
    div[class*="viewerBadge"],
    div[class*="profileContainer"],
    div[class*="stAppFooter"],
    div[class*="floating"],
    div[data-test-script-badge],
    a[href*="streamlit.io"],
    a[href*="github.com"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        pointer-events: none !important;
    }

    div[style*="position: fixed"][style*="bottom"],
    div[style*="position: absolute"][style*="bottom"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. VERİTABANI YÖNETİMİ (SQLite)
# =========================================================
DB_FILE = "saha_operasyon.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS matris (
            sira INTEGER PRIMARY KEY AUTOINCREMENT,
            hat1_ozel TEXT,
            hat2_genel TEXT,
            eyap_silis TEXT,
            guub_cimento TEXT,
            isken_komur TEXT,
            tosyali_cevher TEXT
        )
    ''')
    c.execute("SELECT COUNT(*) FROM matris")
    if c.fetchone()[0] == 0:
        ornek_veri = [
            ("31 ANM 573", "31 ANM 593", "31 ANK 374", "31 AAG 291", "31 ANM 598", "31 ANN 331"),
            ("31 ANN 019", "31 ANN 168", "31 ANL 936", "31 AKL 553", "31 AIU 808", "31 AOK 866"),
            ("31 ANM 150", "31 ANN 304", "31 ANM 576", "31 AKL 554", "31 AIU 869", "31 AKL 556"),
            ("31 AOB 800", "31 ANN 312", "31 ANN 284", "31 AKL 852", "31 ANK 278", "31 ANM 210"),
            ("31 AIU 820", "31 ANV 235", "31 ANR 925", "31 AKL 862", "31 ANM 584", "31 AIY 548"),
            ("31 AKL 545", "31 ANV 253", "31 ANR 938", "31 ANJ 636", "31 ANN 358", "31 AOV 949")
        ]
        c.executemany("INSERT INTO matris (hat1_ozel, hat2_genel, eyap_silis, guub_cimento, isken_komur, tosyali_cevher) VALUES (?,?,?,?,?,?)", ornek_veri)
        conn.commit()
    conn.close()

def load_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM matris", conn)
    conn.close()
    return df

def save_data(df):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql("matris", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

def insert_single_record(tesis_column, plaka_no):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    query = f"INSERT INTO matris ({tesis_column}) VALUES (?)"
    c.execute(query, (plaka_no,))
    conn.commit()
    conn.close()

init_db()
if "df_matris" not in st.session_state:
    st.session_state.df_matris = load_data()

# =========================================================
# 4. SOL MENÜ (ALT ALTA NAVİGASYON PANELSİ)
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding-bottom: 10px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:800;">⚡ ŞİMŞEK LOGISTICS</h2>
            <span style="color: #64748B; font-size: 0.8rem; font-weight:600;">ENTERPRISE SAAS PORTAL</span>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    secilen_menu = st.radio(
        "NAVİGASYON MENÜSÜ",
        [
            "📊 Canlı Sevkiyat Matrisi",
            "🚚 Filo & Vardiya Amirleri",
            "🗄️ Veritabanı Yönetimi",
            "➕ Yeni Araç / Kayıt Ekle"
        ],
        label_visibility="collapsed"
    )

# =========================================================
# 5. ORTAK ÜST HEADER
# =========================================================
bugun_tarih = datetime.now().strftime("%d.%m.%Y")
df_current = st.session_state.df_matris

st.markdown(f"""
<div class="excel-header">
    <div>
        <h3 style="margin:0; color:#38bdf8;">⚡ ŞİMŞEK LOJİSTİK — {secilen_menu.upper()}</h3>
        <span style="color:#94a3b8; font-size:0.85rem;">Saha Operasyon & Fleet Dispatch Yönetim Merkezi</span>
    </div>
    <div style="text-align:right; color:#34d399; font-weight:600;">
        ● CANLI SİSTEM ({bugun_tarih})
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 6. SAYFA İÇERİKLERİ
# =========================================================

# --- 1. SÜTUN: CANLI SEVKİYAT MATRİSİ ---
if secilen_menu == "📊 Canlı Sevkiyat Matrisi":
    count_mmk = df_current['hat1_ozel'].replace('', None).count() + df_current['hat2_genel'].replace('', None).count()
    count_eyap = df_current['eyap_silis'].replace('', None).count()
    count_guub = df_current['guub_cimento'].replace('', None).count()
    count_isken = df_current['isken_komur'].replace('', None).count()
    count_tosyali = df_current['tosyali_cevher'].replace('', None).count()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">MMK PORT (HURDA)</span><br><b style="color:#38bdf8; font-size:1.15rem;">{count_mmk} Araç</b></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">EYAP (SİLİS KUMU)</span><br><b style="color:#34d399; font-size:1.15rem;">{count_eyap} Araç</b></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">GÜUB (ÇİMENTO)</span><br><b style="color:#f25900; font-size:1.15rem;">{count_guub} Araç</b></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">ISKEN (KÖMÜR)</span><br><b style="color:#a855f7; font-size:1.15rem;">{count_isken} Araç</b></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">TOSYALI (CEVHER)</span><br><b style="color:#f43f5e; font-size:1.15rem;">{count_tosyali} Araç</b></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("💡 Kısayol Bilgisi: Excel'den hücre kopyalayıp doğrudan `Ctrl+C` ve `Ctrl+V` ile tabloya yapıştırabilirsiniz.")

    column_configuration = {
        "sira": st.column_config.NumberColumn("SIRA", disabled=True, width="small"),
        "hat1_ozel": st.column_config.TextColumn("MMK - HAT 1 (ÖZEL)", width="medium"),
        "hat2_genel": st.column_config.TextColumn("MMK - HAT 2 (GENEL)", width="medium"),
        "eyap_silis": st.column_config.TextColumn("EYAP (SİLİS KUMU)", width="medium"),
        "guub_cimento": st.column_config.TextColumn("GÜUB (ÇİMENTO)", width="medium"),
        "isken_komur": st.column_config.TextColumn("ISKEN (KÖMÜR)", width="medium"),
        "tosyali_cevher": st.column_config.TextColumn("TOSYALI (CEVHER)", width="medium"),
    }

    edited_df = st.data_editor(
        st.session_state.df_matris,
        column_config=column_configuration,
        num_rows="dynamic",
        use_container_width=True,
        height=520,
        hide_index=True
    )

    if st.button("💾 Değişiklikleri Veritabanına Kaydet", type="primary", use_container_width=True):
        st.session_state.df_matris = edited_df
        save_data(edited_df)
        st.success("✅ Veritabanı başarıyla güncellendi!")
        st.rerun()

# --- 2. SÜTUN: FİLO & VARDİYA AMİRLERİ ---
elif secilen_menu == "🚚 Filo & Vardiya Amirleri":
    st.subheader("📋 Vardiya Yönetimi & Saha Notları")
    st.info("📋 **AKTİF VARDİYA AMİRLERİ:** SİNAN GÜL // MUSTAFA ÇETİN")
    
    v1, v2 = st.columns(2)
    with v1:
        st.selectbox("🕒 Vardiya Saati:", ["08:00 - 16:00 (Gündüz)", "16:00 - 24:00 (Akşam)", "00:00 - 08:00 (Gece)"])
        st.number_input("Aktif Saha Personeli Sayısı:", value=8)
    with v2:
        st.text_area("📍 Saha Amiri Operasyon Notu:", "Liman kantarlarında yoğunluk yok, akış normal devam ediyor.")

# --- 3. SÜTUN: VERİTABANI YÖNETİMİ ---
elif secilen_menu == "🗄️ Veritabanı Yönetimi":
    st.subheader("🗄️ SQLite Veritabanı Ham Kayıtları (`saha_operasyon.db`)")
    st.dataframe(load_data(), use_container_width=True, height=420)
    
    st.divider()
    if st.button("🚨 Veritabanını Sıfırla ve Örnek Verileri Yükle"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        init_db()
        st.session_state.df_matris = load_data()
        st.success("Veritabanı sıfırlandı ve varsayılan veriler yüklendi.")
        st.rerun()

# --- 4. SÜTUN: YENİ ARAÇ / KAYIT EKLE ---
elif secilen_menu == "➕ Yeni Araç / Kayıt Ekle":
    st.subheader("➕ Veritabanına Yeni Sevkiyat Kaydı Ekle")
    
    with st.form("yeni_kayit_formu"):
        f1, f2 = st.columns(2)
        with f1:
            yeni_plaka = st.text_input("Plaka Giriniz:", placeholder="Örn: 31 ANM 999").upper()
        with f2:
            hedef_tesis = st.selectbox(
                "Atanacak Tesis / Hat Seçiniz:",
                [
                    ("hat1_ozel", "MMK - HAT 1 (ÖZEL)"),
                    ("hat2_genel", "MMK - HAT 2 (GENEL)"),
                    ("eyap_silis", "EYAP (SİLİS KUMU)"),
                    ("guub_cimento", "GÜUB (ÇİMENTO)"),
                    ("isken_komur", "ISKEN (KÖMÜR)"),
                    ("tosyali_cevher", "TOSYALI (CEVHER)")
                ],
                format_func=lambda x: x[1]
            )
        
        btn_kaydet = st.form_submit_button("➕ Veritabanına Ekle", type="primary", use_container_width=True)
        if btn_kaydet:
            if yeni_plaka.strip():
                insert_single_record(hedef_tesis[0], yeni_plaka.strip())
                st.session_state.df_matris = load_data()
                st.success(f"✅ **{yeni_plaka}** plakası **{hedef_tesis[1]}** alanına eklendi!")
                st.rerun()
            else:
                st.warning("Lütfen geçerli bir plaka giriniz.")
