import streamlit as st
import pandas as pd
import sqlite3
import os
import streamlit.components.v1 as components
from datetime import datetime
from collections import Counter

# =========================================================
# 1. SAYFA YAPILANDIRMASI
# =========================================================
st.set_page_config(
    page_title="Şimşek Lojistik | Canlı Saha Matrisi",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- JAVASCRIPT: STREAMLIT BULUT ROZETLERİNİ SİLME ---
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
# 2. GLOBAL CSS (EXECUTIVE TEMA & BİLDİRİM KARTLARI)
# =========================================================
st.markdown("""
<style>
    #MainMenu, footer, [data-testid="stHeader"] { visibility: hidden !important; }
    .stAppHeader { background: transparent !important; height: 0px !important; }
    
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
        z-index: 999999 !important;
        background-color: #0f172a !important;
        border: 1px solid #38bdf8 !important;
        border-radius: 8px !important;
        color: #38bdf8 !important;
        padding: 4px !important;
    }

    [data-testid="stSidebar"] {
        background-color: #0a1120 !important;
        border-right: 1px solid #1e293b !important;
    }

    .stApp { background-color: #050b14 !important; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }

    .excel-main-title {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px 20px;
        color: #38bdf8;
        font-weight: 800;
        font-size: 1.15rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
    }

    .excel-top-header {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
        gap: 4px;
        text-align: center;
        font-weight: bold;
        font-size: 0.85rem;
        margin-bottom: 6px;
    }
    .head-m1 { background: #1e3a8a; color: #ffffff; padding: 8px; border-radius: 4px; }
    .head-m2 { background: #0284c7; color: #ffffff; padding: 8px; border-radius: 4px; }
    .head-m3 { background: #0369a1; color: #ffffff; padding: 8px; border-radius: 4px; }
    .head-m4 { background: #581c87; color: #ffffff; padding: 8px; border-radius: 4px; }
    .head-m5 { background: #9a3412; color: #ffffff; padding: 8px; border-radius: 4px; }

    .counter-bar {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px;
        text-align: center;
        font-size: 0.85rem;
        font-weight: 600;
    }

    .dup-alarm {
        background: rgba(244, 63, 94, 0.15);
        border: 1px solid #f43f5e;
        color: #fca5a5;
        border-radius: 8px;
        padding: 10px 15px;
        margin-bottom: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. VERİTABANI MİMARİSİ
# =========================================================
DB_FILE = "simsek_os.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS excel_matris (
            sira INTEGER PRIMARY KEY AUTOINCREMENT,
            mmk_hat1 TEXT, mmk_hat2 TEXT, eyap_silis TEXT,
            guub_cimento TEXT, isken_komur TEXT, tosyali_cevher TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS header_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            main_title TEXT, vardiya_amirleri TEXT,
            l1 TEXT, c1 TEXT, l2 TEXT, c2 TEXT,
            l3 TEXT, c3 TEXT, l4 TEXT, c4 TEXT,
            l5 TEXT, c5 TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS filo (
            plaka TEXT PRIMARY KEY, dorse TEXT, tip TEXT, durum TEXT
        )
    ''')
    
    c.execute("SELECT COUNT(*) FROM header_config")
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO header_config (main_title, vardiya_amirleri, l1, c1, l2, c2, l3, c3, l4, c4, l5, c5)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            "ŞİMŞEK LOJİSTİK - İSKENDERUN / DİLOVASI SAHA MATRİSİ",
            "SİNAN GÜL // MUSTAFA ÇETİN",
            "MMK PORT / SAHA 1", "HURDA / DÖKME YÜK",
            "EYAP LİMANI", "SİLİS KUMU",
            "GÜÜB LİMANI", "ÇİMENTO",
            "İSKEN SANTRAL", "KÖMÜR",
            "TOSYALI LİMANI", "CEVHER"
        ))

    c.execute("SELECT COUNT(*) FROM excel_matris")
    if c.fetchone()[0] == 0:
        ornek = [
            ("31 ANM 573", "31 ANM 593", "31 ANK 374", "31 AAG 291", "31 ANM 598", "31 ANN 331"),
            ("31 ANN 019", "31 ANN 168", "31 ANL 936", "31 AKL 553", "31 AIU 808", "31 AOK 866"),
            ("31 ANM 150", "31 ANN 304", "31 ANM 576", "31 AKL 554", "31 AIU 869", "31 AKL 556"),
            ("31 AOB 800", "31 ANN 312", "31 ANN 284", "31 AKL 852", "31 ANK 278", "31 ANM 210"),
            ("31 AIU 820", "31 ANV 235", "31 ANR 925", "31 AKL 862", "31 ANM 584", "31 AIY 548")
        ]
        c.executemany("INSERT INTO excel_matris (mmk_hat1, mmk_hat2, eyap_silis, guub_cimento, isken_komur, tosyali_cevher) VALUES (?,?,?,?,?,?)", ornek)
    
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

def get_header_config():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM header_config LIMIT 1", conn)
    conn.close()
    return df.iloc[0].to_dict()

def check_duplicates(df):
    all_plates = []
    cols = ['mmk_hat1', 'mmk_hat2', 'eyap_silis', 'guub_cimento', 'isken_komur', 'tosyali_cevher']
    for col in cols:
        if col in df.columns:
            for val in df[col].dropna():
                p = str(val).strip().upper()
                if p and p != 'NONE' and p != 'NAN':
                    all_plates.append(p)
    counts = Counter(all_plates)
    return {p: c for p, c in counts.items() if c > 1}

if "df_excel" not in st.session_state:
    st.session_state.df_excel = load_data("excel_matris")

if "history" not in st.session_state:
    st.session_state.history = [st.session_state.df_excel.copy()]

# =========================================================
# 4. SOL NAVİGASYON
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 10px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:900;">⚡ ŞimşekLog</h2>
            <span style="color: #64748B; font-size: 0.75rem;">CANLI LOJİSTİK ERP</span>
        </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    kullanici_rolu = st.selectbox("👤 AKTİF ROL:", ["👑 Patron (Yönetici)", "💼 Muhasebe", "🚚 Sevkiyatçı / Vardiya Amiri"])
    st.markdown("---")
    menu = st.radio("NAVİGASYON", ["📋 GÜNCEL SEVKİYAT (Orijinal Excel)", "📊 İstatistikler & Özet", "🚍 Filo Kayıtları"])

# =========================================================
# 5. DİNAMİK MODÜLLER
# =========================================================
if menu == "📋 GÜNCEL SEVKİYAT (Orijinal Excel)":
    
    cfg = get_header_config()
    bugun_str = datetime.now().strftime("%d.%m.%Y")
    
    # 1. DİNAMİK ÜST BANNER
    st.markdown(f"""
    <div class="excel-main-title">
        <span>⚡ {cfg['main_title']}</span>
        <span style="color:#34d399; font-size:0.85rem;">📅 {bugun_str} VARDİYA AMİRLERİ: {cfg['vardiya_amirleri']}</span>
    </div>
    """, unsafe_allow_html=True)

    # 2. DİNAMİK LİMAN VE CİNSİ BAŞLIKLARI
    st.markdown(f"""
    <div class="excel-top-header">
        <div class="head-m1">{cfg['l1']}<br><small style="color:#facc15;">{cfg['c1']}</small></div>
        <div class="head-m2">{cfg['l2']}<br><small style="color:#facc15;">{cfg['c2']}</small></div>
        <div class="head-m3">{cfg['l3']}<br><small style="color:#facc15;">{cfg['c3']}</small></div>
        <div class="head-m4">{cfg['l4']}<br><small style="color:#facc15;">{cfg['c4']}</small></div>
        <div class="head-m5">{cfg['l5']}<br><small style="color:#facc15;">{cfg['c5']}</small></div>
    </div>
    """, unsafe_allow_html=True)

    df_ex = st.session_state.df_excel

    # 3. MÜKERRER PLAKA KONTROLÜ VE CANLI ALARM
    dups = check_duplicates(df_ex)
    if dups:
        dup_str = ", ".join([f"<b>{p}</b> ({c} kez)" for p, c in dups.items()])
        st.markdown(f'<div class="dup-alarm">🚨 MÜKERRER PLAKA ALARMI: Aşağıdaki plakalar matriste birden fazla kez girilmiş! -> {dup_str}</div>', unsafe_allow_html=True)

    # 4. CANLI SAYAÇ HESAPLAMA
    c1, c2, c3, c4, c5 = st.columns(5)
    c_m1 = df_ex['mmk_hat1'].replace('', None).dropna().count() + df_ex['mmk_hat2'].replace('', None).dropna().count()
    c_m2 = df_ex['eyap_silis'].replace('', None).dropna().count()
    c_m3 = df_ex['guub_cimento'].replace('', None).dropna().count()
    c_m4 = df_ex['isken_komur'].replace('', None).dropna().count()
    c_m5 = df_ex['tosyali_cevher'].replace('', None).dropna().count()

    with c1: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_m1} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_m2} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_m3} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_m4} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_m5} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 5. ÜST BANNER & BAŞLIKLARI DEĞİŞTİRME PANELİ
    with st.expander("✏️ Üst Banner, Vardiya Amirleri ve Tesis Başlıklarını Düzenle"):
        with st.form("header_formu"):
            f_title = st.text_input("Ana Banner Başlığı:", value=cfg['main_title'])
            f_amir = st.text_input("Vardiya Amirleri Metni:", value=cfg['vardiya_amirleri'])
            
            st.markdown("---")
            fc1, fc2, fc3, fc4, fc5 = st.columns(5)
            fl1 = fc1.text_input("1. Liman Adı:", value=cfg['l1']); fc1_sub = fc1.text_input("1. Malzeme:", value=cfg['c1'])
            fl2 = fc2.text_input("2. Liman Adı:", value=cfg['l2']); fc2_sub = fc2.text_input("2. Malzeme:", value=cfg['c2'])
            fl3 = fc3.text_input("3. Liman Adı:", value=cfg['l3']); fc3_sub = fc3.text_input("3. Malzeme:", value=cfg['c3'])
            fl4 = fc4.text_input("4. Liman Adı:", value=cfg['l4']); fc4_sub = fc4.text_input("4. Malzeme:", value=cfg['c4'])
            fl5 = fc5.text_input("5. Liman Adı:", value=cfg['l5']); fc5_sub = fc5.text_input("5. Malzeme:", value=cfg['c5'])
            
            if st.form_submit_button("💾 Tüm Başlık Değişikliklerini Veritabanına Kaydet", type="primary", use_container_width=True):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute('''
                    UPDATE header_config SET main_title=?, vardiya_amirleri=?,
                    l1=?, c1=?, l2=?, c2=?, l3=?, c3=?, l4=?, c4=?, l5=?, c5=? WHERE id=1
                ''', (f_title, f_amir, fl1, fc1_sub, fl2, fc2_sub, fl3, fc3_sub, fl4, fc4_sub, fl5, fc5_sub))
                conn.commit(); conn.close()
                st.success("✅ Tüm başlıklar başarıyla güncellendi!")
                st.rerun()

    # 6. TOOLBAR VE İNTERAKTİF GRID
    t1, t2, t3, t4, t5 = st.columns([2.5, 1, 1, 1, 1])
    with t1:
        arama = st.text_input("🔍 Matriste Plaka Ara:", placeholder="Örn: 31 ANM...").upper()
    with t2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("↩️ Geri Al (Ctrl+Z)", use_container_width=True):
            if len(st.session_state.history) > 1:
                st.session_state.history.pop()
                st.session_state.df_excel = st.session_state.history[-1].copy()
                st.toast("↩️ İşlem geri alındı!")
                st.rerun()
            else:
                st.toast("⚠️ Geri alınacak başka işlem yok.")
    with t3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        csv = df_ex.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Excel İndir", csv, "GUNCEL_SEVKIYAT_MATRISI.csv", "text/csv", use_container_width=True)
    with t4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ 5 Satır Ekle", use_container_width=True):
            boslar = pd.DataFrame([{"sira": None, "mmk_hat1": "", "mmk_hat2": "", "eyap_silis": "", "guub_cimento": "", "isken_komur": "", "tosyali_cevher": ""} for _ in range(5)])
            yeni_df = pd.concat([st.session_state.df_excel, boslar], ignore_index=True)
            st.session_state.df_excel = yeni_df
            st.session_state.history.append(yeni_df.copy())
            st.rerun()
    with t5:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("🧹 Boşları Temizle", use_container_width=True):
            cols_check = [c for c in df_ex.columns if c != 'sira']
            yeni_df = df_ex.dropna(how='all', subset=cols_check)
            st.session_state.df_excel = yeni_df
            st.session_state.history.append(yeni_df.copy())
            save_data(st.session_state.df_excel, "excel_matris")
            st.rerun()

    df_disp = df_ex.copy()
    if arama:
        mask = df_disp.apply(lambda r: r.astype(str).str.contains(arama, case=False).any(), axis=1)
        df_disp = df_disp[mask]

    config = {
        "sira": st.column_config.NumberColumn("SIRA", disabled=True),
        "mmk_hat1": st.column_config.TextColumn("HAT 1 (ÖZEL)", width="medium"),
        "mmk_hat2": st.column_config.TextColumn("HAT 2 (GENEL)", width="medium"),
        "eyap_silis": st.column_config.TextColumn("SAHA A (EYAP)", width="medium"),
        "guub_cimento": st.column_config.TextColumn("SAHA B (GÜUB)", width="medium"),
        "isken_komur": st.column_config.TextColumn("SAHA C (İSKEN)", width="medium"),
        "tosyali_cevher": st.column_config.TextColumn("SAHA D (TOSYALI)", width="medium"),
    }

    edited = st.data_editor(df_disp, column_config=config, num_rows="dynamic", use_container_width=True, height=450, hide_index=True)

    if not edited.equals(st.session_state.df_excel) and not arama:
        st.session_state.df_excel = edited
        st.session_state.history.append(edited.copy())

    if st.button("💾 Değişiklikleri Veritabanına Kaydet", type="primary", use_container_width=True):
        if not arama:
            st.session_state.df_excel = edited
            save_data(edited, "excel_matris")
            st.success("✅ Veriler veritabanına başarıyla kaydedildi!")
            st.rerun()
        else:
            st.warning("Arama yaparken kaydetme yapılamaz. Lütfen arama kutusunu temizleyin.")

# --- DİĞER MODÜLLER ---
elif menu == "📊 İstatistikler & Özet":
    st.subheader("📊 Canlı Sevkiyat Veri Analizi")
    st.write(f"Toplam Satır Sayısı: **{len(st.session_state.df_excel)}**")

elif menu == "VIP Filo Kayıtları":
    st.subheader("🚍 Şirket Filo Rehberi")
    st.dataframe(load_data("filo"), use_container_width=True)
