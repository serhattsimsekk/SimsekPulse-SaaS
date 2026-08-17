import streamlit as st
import pandas as pd
import sqlite3
import os

# 1. EN ÜSTTE SAYFA YAPILANDIRMASI
st.set_page_config(
    page_title="Şimşek Lojistik | Canlı Sevkiyat Matrisi",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. TAM KURUMSAL ARAYÜZ VE SIFIR ROZET CSS ENJEKSİYONU
st.markdown("""
<style>
    /* Üst Menü, Header, Footer ve Toolbar Gizleme */
    .stAppHeader, #MainMenu, footer, header {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Sağ Alttaki Profil İkonu, GitHub ve Streamlit Rozetlerini Tamamen Yok Etme */
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"],
    .viewerBadge_container__1vB22,
    .viewerBadge_link__1S137,
    div[class*="viewerBadge"],
    div[class*="profileContainer"],
    div[class*="stAppFooter"],
    a[href*="streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Sayfa Arka Planı ve Yerleşim Optimization */
    .stApp {
        background-color: #0b1329 !important;
        color: #f8fafc;
    }
    .block-container {
        padding: 0.8rem 1rem !important;
        max-width: 100% !important;
    }

    /* Top Bar Header */
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

    /* Dynamic Counter Cards */
    .counter-card {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 8px 12px;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# 3. VERİTABANI BAĞLANTISI VE BAŞLANGIÇ VERİSİ
DB_FILE = "saha_operasyon.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS matris (
            sira INTEGER PRIMARY KEY,
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
            (1, "31 ANM 573", "31 ANM 593", "31 ANK 374", "31 AAG 291", "31 ANM 598", "31 ANN 331"),
            (2, "31 ANN 019", "31 ANN 168", "31 ANL 936", "31 AKL 553", "31 AIU 808", "31 AOK 866"),
            (3, "31 ANM 150", "31 ANN 304", "31 ANM 576", "31 AKL 554", "31 AIU 869", "31 AKL 556"),
            (4, "31 AOB 800", "31 ANN 312", "31 ANN 284", "31 AKL 852", "31 ANK 278", "31 ANM 210"),
            (5, "31 AIU 820", "31 ANV 235", "31 ANR 925", "31 AKL 862", "31 ANM 584", "31 AIY 548"),
            (6, "31 AKL 545", "31 ANV 253", "31 ANR 938", "31 ANJ 636", "31 ANN 358", "31 AOV 949"),
            (7, "31 ANJ 479", "31 AOB 756", "31 ANR 943", "31 ANK 359", "31 ANR 916", "31 ANF 677"),
            (8, "31 ANM 112", "31 AOK 710", "31 AOB 847", "31 ANM 091", "31 ANR 937", "31 AOK 698"),
            (9, "31 ANM 157", "31 AOK 715", "31 AOK 711", "31 ANM 187", "31 AOV 941", "31 AIY 560"),
            (10, "31 ANM 200", "31 AOV 747", "31 AOV 964", "31 ANM 201", "31 AOV 956", "31 AOC 430"),
            (11, "31 ANM 219", "31 AOV 960", "31 ASZ 260", "31 ANM 244", "31 ANN 018", "31 ANM 211"),
            (12, "31 ANM 243", "31 AOV 973", "31 AUR 259", "31 ANM 254", "31 ASZ 241", "31 ANM 337"),
            (13, "31 ANM 265", "31 APP 839", "31 AUR 263", "31 ANM 260", "31 ANM 286", "31 ANM 264"),
            (14, "31 ANM 295", "31 AUR 239", "31 AUR 289", "31 ANM 566", "31 AOV 943", "31 AIY 516"),
            (15, "31 ANM 664", "31 AUR 243", "31 AUR 297", "31 ANR 914", "31 ABC 123", "31 ANM 285")
        ]
        c.executemany("INSERT INTO matris VALUES (?,?,?,?,?,?,?)", ornek_veri)
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

# 4. ÜST PANEL & İSTATİSTİKLER
df_current = st.session_state.df_matris

count_mmk = df_current['hat1_ozel'].replace('', None).count() + df_current['hat2_genel'].replace('', None).count()
count_eyap = df_current['eyap_silis'].replace('', None).count()
count_guub = df_current['guub_cimento'].replace('', None).count()
count_isken = df_current['isken_komur'].replace('', None).count()
count_tosyali = df_current['tosyali_cevher'].replace('', None).count()

st.markdown("""
<div class="excel-header">
    <div>
        <h3 style="margin:0; color:#38bdf8;">⚡ ŞİMŞEK LOJİSTİK — OTOMASYONLU SEVKİYAT MATRİSİ</h3>
        <span style="color:#94a3b8; font-size:0.85rem;">Veritabanı Entegreli Canlı Hücre Editörü</span>
    </div>
    <div style="text-align:right; color:#34d399; font-weight:600;">
        ● CANLI SİSTEM (12.08.2026)
    </div>
</div>
""", unsafe_allow_html=True)

# Canlı Sayaç Kartları
c1, c2, c3, c4, c5 = st.columns(5)
with c1:
    st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">MMK PORT (HURDA)</span><br><b style="color:#38bdf8; font-size:1.1rem;">{count_mmk} Araç</b></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">EYAP (SİLİS KUMU)</span><br><b style="color:#34d399; font-size:1.1rem;">{count_eyap} Araç</b></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">GÜUB (ÇİMENTO)</span><br><b style="color:#f25900; font-size:1.1rem;">{count_guub} Araç</b></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">ISKEN (KÖMÜR)</span><br><b style="color:#a855f7; font-size:1.1rem;">{count_isken} Araç</b></div>', unsafe_allow_html=True)
with c5:
    st.markdown(f'<div class="counter-card"><span style="color:#94a3b8; font-size:0.75rem;">TOSYALI (CEVHER)</span><br><b style="color:#f43f5e; font-size:1.1rem;">{count_tosyali} Araç</b></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# 5. İNTERAKTİF VE CANLI EDİTÖRLÜ EXCEL MATRİSİ
st.subheader("📋 Canlı Sevkiyat Planlama Tablosu (Düzenlenebilir)")
st.caption("💡 İpucu: Herhangi bir hücreye çift tıklayarak plakayı değiştirebilir, doğrudan Excel'den kopyala-yapıştır yapabilirsiniz.")

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

# 6. VERİTABANI KAYDETME & CANLI SENKRONİZASYON
btn_col1, btn_col2 = st.columns([1, 4])

with btn_col1:
    if st.button("💾 Değişiklikleri Kaydet", type="primary", use_container_width=True):
        st.session_state.df_matris = edited_df
        save_data(edited_df)
        st.success("✅ Veritabanına başarıyla kaydedildi!")
        st.rerun()

with btn_col2:
    st.info("Değişiklik yaptıktan sonra 'Değişiklikleri Kaydet' butonuna basarak veritabanınızı güncelleyebilirsiniz.")
