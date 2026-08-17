import streamlit as st
import pandas as pd
import sqlite3
import os
from datetime import datetime

# =========================================================
# 1. SAYFA YAPILANDIRMASI
# =========================================================
st.set_page_config(
    page_title="Şimşek Lojistik | Enterprise Live Spreadsheet",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# 2. GLOBAL CSS VE ARAYÜZ STİLLERİ
# =========================================================
st.markdown("""
<style>
    /* Streamlit Üst Menü ve Alt Bilgi Temizliği */
    .stAppHeader, #MainMenu, footer, header {
        display: none !important;
        visibility: hidden !important;
    }

    .stApp {
        background-color: #080d1a !important;
        color: #f8fafc;
    }
    .block-container {
        padding: 0.8rem 1.2rem !important;
        max-width: 100% !important;
    }

    /* Sol Sidebar Tasarımı */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        border-right: 1px solid #1e293b !important;
    }
    div[data-testid="stRadio"] label {
        background-color: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px 14px;
        color: #94a3b8;
        font-weight: 600;
        cursor: pointer;
        margin-bottom: 4px;
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
        padding: 12px 20px;
        margin-bottom: 12px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }

    /* Metrik Kartlar */
    .kpi-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 8px;
        padding: 10px;
        text-align: center;
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

init_db()
if "df_matris" not in st.session_state:
    st.session_state.df_matris = load_data()

# =========================================================
# 4. NAVİGASYON PANELSİ
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; padding-bottom: 5px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:800;">⚡ ŞİMŞEK LOGISTICS</h2>
            <span style="color: #64748B; font-size: 0.75rem; font-weight:600;">ENTERPRISE SAAS PORTAL</span>
        </div>
    """, unsafe_allow_html=True)
    st.divider()
    
    secilen_menu = st.radio(
        "NAVİGASYON",
        [
            "📊 Canlı E-Tablo Matrisi",
            "🚚 Filo & Vardiya Yönetimi",
            "🗄️ Veritabanı Hammaddeleri",
            "➕ Hızlı Kayıt Ekle"
        ],
        label_visibility="collapsed"
    )

# Header
bugun_tarih = datetime.now().strftime("%d.%m.%Y")
df_current = st.session_state.df_matris

st.markdown(f"""
<div class="excel-header">
    <div>
        <h3 style="margin:0; color:#38bdf8;">⚡ ŞİMŞEK LOJİSTİK — {secilen_menu.upper()}</h3>
        <span style="color:#94a3b8; font-size:0.85rem;">Gerçek Zamanlı Saha & Sevkiyat Yönetim Ekranı</span>
    </div>
    <div style="text-align:right; color:#34d399; font-weight:600;">
        ● CANLI İSTASYON ({bugun_tarih})
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 5. MODÜL İÇERİKLERİ
# =========================================================

# --- MODÜL 1: MAX LEVEL CANLI E-TABLO ---
if secilen_menu == "📊 Canlı E-Tablo Matrisi":
    
    # Anlık Metrik Hesaplama
    c1, c2, c3, c4, c5 = st.columns(5)
    cols = ['hat1_ozel', 'hat2_genel', 'eyap_silis', 'guub_cimento', 'isken_komur', 'tosyali_cevher']
    counts = {col: df_current[col].replace('', None).dropna().count() for col in cols}
    
    with c1:
        st.markdown(f'<div class="kpi-card"><span style="color:#94a3b8; font-size:0.75rem;">MMK PORT</span><br><b style="color:#38bdf8; font-size:1.15rem;">{counts["hat1_ozel"] + counts["hat2_genel"]} Araç</b></div>', unsafe_allow_html=True)
    with c2:
        st.markdown(f'<div class="kpi-card"><span style="color:#94a3b8; font-size:0.75rem;">EYAP (SİLİS)</span><br><b style="color:#34d399; font-size:1.15rem;">{counts["eyap_silis"]} Araç</b></div>', unsafe_allow_html=True)
    with c3:
        st.markdown(f'<div class="kpi-card"><span style="color:#94a3b8; font-size:0.75rem;">GÜUB (ÇİMENTO)</span><br><b style="color:#f25900; font-size:1.15rem;">{counts["guub_cimento"]} Araç</b></div>', unsafe_allow_html=True)
    with c4:
        st.markdown(f'<div class="kpi-card"><span style="color:#94a3b8; font-size:0.75rem;">ISKEN (KÖMÜR)</span><br><b style="color:#a855f7; font-size:1.15rem;">{counts["isken_komur"]} Araç</b></div>', unsafe_allow_html=True)
    with c5:
        st.markdown(f'<div class="kpi-card"><span style="color:#94a3b8; font-size:0.75rem;">TOSYALI (CEVHER)</span><br><b style="color:#f43f5e; font-size:1.15rem;">{counts["tosyali_cevher"]} Araç</b></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ARAÇ ÇUBUĞU (Arama, Excel İndir, Boş Temizle)
    t_col1, t_col2, t_col3, t_col4 = st.columns([3, 1, 1, 1])
    
    with t_col1:
        arama_termi = st.text_input("🔍 Plaka Arama / Filtreleme:", placeholder="Örn: 31 ANM...").upper()
    
    with t_col2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        csv_data = st.session_state.df_matris.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Excel/CSV İndir", csv_data, "sevkiyat_matrisi.csv", "text/csv", use_container_width=True)

    with t_col3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ 5 Satır Ekle", use_container_width=True):
            yeni_satirlar = pd.DataFrame([{"sira": None, "hat1_ozel": "", "hat2_genel": "", "eyap_silis": "", "guub_cimento": "", "isken_komur": "", "tosyali_cevher": ""} for _ in range(5)])
            st.session_state.df_matris = pd.concat([st.session_state.df_matris, yeni_satirlar], ignore_index=True)
            st.rerun()

    with t_col4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("🧹 Boşları Temizle", use_container_width=True):
            # Tümü boş olan satırları filtrele
            st.session_state.df_matris = st.session_state.df_matris.dropna(how='all', subset=cols)
            save_data(st.session_state.df_matris)
            st.rerun()

    # Arama Filtreleme Mantığı
    display_df = st.session_state.df_matris.copy()
    if arama_termi:
        mask = display_df.apply(lambda row: row.astype(str).str.contains(arama_termi, case=False).any(), axis=1)
        display_df = display_df[mask]

    # Canlı E-Tablo Matrisi
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
        display_df,
        column_config=column_configuration,
        num_rows="dynamic",
        use_container_width=True,
        height=540,
        hide_index=True
    )

    # Kaydetme Butonu
    if st.button("💾 Değişiklikleri Veritabanına Kaydet", type="primary", use_container_width=True):
        if not arama_termi:
            st.session_state.df_matris = edited_df
            save_data(edited_df)
            st.success("✅ Veritabanı başarıyla senkronize edildi!")
            st.rerun()
        else:
            st.warning("Arama modundayken kaydetme yapılamaz. Lütfen arama kutusunu temizleyiniz.")

# --- MODÜL 2: FİLO & VARDİYA ---
elif secilen_menu == "🚚 Filo & Vardiya Yönetimi":
    st.subheader("📋 Vardiya Amirleri & Saha Notları")
    st.info("📋 **AKTİF VARDİYA AMİRLERİ:** SİNAN GÜL // MUSTAFA ÇETİN")
    
    v1, v2 = st.columns(2)
    with v1:
        st.selectbox("🕒 Aktif Vardiya:", ["08:00 - 16:00 (Gündüz)", "16:00 - 24:00 (Akşam)", "00:00 - 08:00 (Gece)"])
        st.number_input("Saha Personel Sayısı:", value=12)
    with v2:
        st.text_area("📍 Operasyon Vardiya Notu:", "İskenderun liman bölgesinde sevkiyat akışı kesintisiz devam etmektedir.")

# --- MODÜL 3: VERİTABANI YÖNETİMİ ---
elif secilen_menu == "🗄️ Veritabanı Hammaddeleri":
    st.subheader("🗄️ SQLite Veritabanı Ham Kayıt Paneli (`saha_operasyon.db`)")
    st.dataframe(load_data(), use_container_width=True, height=400)
    
    st.divider()
    if st.button("🚨 Veritabanını Varsayılan Duruma Getir"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        init_db()
        st.session_state.df_matris = load_data()
        st.success("Veritabanı sıfırlandı ve fabrika ayarlarına dönüldü.")
        st.rerun()

# --- MODÜL 4: HIZLI KAYIT EKLE ---
elif secilen_menu == "➕ Hızlı Kayıt Ekle":
    st.subheader("➕ Veritabanına Tekil Sevkiyat Kaydı Ekle")
    
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
        
        btn_kaydet = st.form_submit_button("➕ Veritabanına İşle", type="primary", use_container_width=True)
        if btn_kaydet:
            if yeni_plaka.strip():
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute(f"INSERT INTO matris ({hedef_tesis[0]}) VALUES (?)", (yeni_plaka.strip(),))
                conn.commit()
                conn.close()
                st.session_state.df_matris = load_data()
                st.success(f"✅ **{yeni_plaka}** plakası **{hedef_tesis[1]}** alanına eklendi!")
                st.rerun()
            else:
                st.warning("Lütfen geçerli bir plaka giriniz.")
