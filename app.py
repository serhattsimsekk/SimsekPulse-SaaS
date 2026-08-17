import streamlit as st
import pandas as pd
import sqlite3
import os
import streamlit.components.v1 as components
from datetime import datetime

# =========================================================
# 1. SAYFA YAPILANDIRMASI
# =========================================================
st.set_page_config(
    page_title="Şimşek Lojistik | Saha Matrisi",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- JAVASCRIPT: STREAMLIT BULUT ROZETLERİNİ SİLME & CTRL+Z SHORTCUT ENJEKSİYONU ---
components.html("""
<script>
    // 1. Rozetleri Temizleme
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

    // 2. CTRL+Z / CTRL+Y HÜCRE GERİ ALMA MANTIĞI (INTERACTIVE GRID UNDO)
    try {
        const parentDoc = window.parent.document;
        parentDoc.addEventListener('keydown', function(e) {
            // Ctrl+Z veya Cmd+Z yakalama
            if ((e.ctrlKey || e.metaKey) && e.key === 'z' && !e.shiftKey) {
                // E-tablo düzenleyicisine Undo komutu tetikle
                const activeEl = parentDoc.activeElement;
                if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.contentEditable === 'true')) {
                    // Hücre içi varsayılan metin undo
                    parentDoc.execCommand('undo', false, null);
                }
            }
            // Ctrl+Shift+Z veya Ctrl+Y Redo yakalama
            if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'Z'))) {
                const activeEl = parentDoc.activeElement;
                if (activeEl && (activeEl.tagName === 'INPUT' || activeEl.contentEditable === 'true')) {
                    parentDoc.execCommand('redo', false, null);
                }
            }
        });
    } catch (e) {}
</script>
""", height=0, width=0)

# =========================================================
# 2. GLOBAL CSS (EXCEL RENKLERİ VE SAYFA DÜZENİ)
# =========================================================
st.markdown("""
<style>
    #MainMenu, footer, [data-testid="stHeader"] { visibility: hidden !important; }
    .stAppHeader { background: transparent !important; height: 0px !important; }
    
    /* YAN MENÜ AÇMA/KAPATMA BUTONU */
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

    /* EXCEL HEADER BANNER */
    .excel-main-title {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px 20px;
        color: #38bdf8;
        font-weight: 800;
        font-size: 1.2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }

    /* EXCEL TABLO BAŞLIKLARI DÜZENİ */
    .excel-top-header {
        display: grid;
        grid-template-columns: 1fr 1fr 1fr 1fr 1fr;
        gap: 4px;
        text-align: center;
        font-weight: bold;
        font-size: 0.85rem;
        margin-bottom: 6px;
    }
    .head-mmk { background: #1e3a8a; color: #ffffff; padding: 6px; border-radius: 4px; }
    .head-eyap { background: #0284c7; color: #ffffff; padding: 6px; border-radius: 4px; }
    .head-guub { background: #0369a1; color: #ffffff; padding: 6px; border-radius: 4px; }
    .head-isken { background: #581c87; color: #ffffff; padding: 6px; border-radius: 4px; }
    .head-tosyali { background: #9a3412; color: #ffffff; padding: 6px; border-radius: 4px; }

    .counter-bar {
        background: #1e293b;
        border: 1px solid #334155;
        border-radius: 6px;
        padding: 8px;
        text-align: center;
        font-size: 0.85rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. VERİTABANI VE STATE SAKLAMA (UNDO / REDO DESTEKLİ)
# =========================================================
DB_FILE = "simsek_os.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS excel_matris (
            sira INTEGER PRIMARY KEY AUTOINCREMENT,
            mmk_hat1 TEXT,
            mmk_hat2 TEXT,
            eyap_silis TEXT,
            guub_cimento TEXT,
            isken_komur TEXT,
            tosyali_cevher TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS filo (
            plaka TEXT PRIMARY KEY, dorse TEXT, tip TEXT,
            sofor_1 TEXT, sofor_2 TEXT, grup TEXT, durum TEXT
        )
    ''')
    
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

if "df_excel" not in st.session_state:
    st.session_state.df_excel = load_data("excel_matris")

# TABLO TARİHÇESİ (UNDO GEÇMİŞİ)
if "history" not in st.session_state:
    st.session_state.history = [st.session_state.df_excel.copy()]

if "df_filo" not in st.session_state:
    st.session_state.df_filo = load_data("filo")

# =========================================================
# 4. SOL NAVİGASYON (RBAC)
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 10px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:900; letter-spacing: 1px;">⚡ ŞimşekLog</h2>
            <span style="color: #64748B; font-size: 0.75rem; font-weight:700;">SUPPLY CHAIN OS v4.0</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    kullanici_rolu = st.selectbox(
        "👤 AKTİF KULLANICI ROLÜ:",
        ["👑 Patron (Yönetici)", "💼 Muhasebe Departmanı", "🚚 Sevkiyatçı / Vardiya Amiri", "👮‍♂️ Baş Şoför"],
        index=0
    )
    st.markdown("---")
    
    menuler = [
        "📋 GÜNCEL SEVKİYAT (Orijinal Excel)",
        "📊 Dashboard & Yönetici Özeti",
        "Master Filo & Öz Mal (HR)",
        "👥 Vardiya Amirleri & İK",
        "🚨 Kademe & Bakım Paneli"
    ]
    
    menu = st.radio("NAVİGASYON", menuler, label_visibility="collapsed")

# =========================================================
# 5. DİNAMİK MODÜLLER
# =========================================================

# --- MODÜL 1: ORİJİNAL EXCEL SEVKİYAT MATRİSİ ---
if menu == "📋 GÜNCEL SEVKİYAT (Orijinal Excel)":
    
    bugun_str = datetime.now().strftime("%d.%m.%Y")
    
    st.markdown(f"""
    <div class="excel-main-title">
        <span>⚡ ŞİMŞEK LOJİSTİK - İSKENDERUN / DİLOVASI SAHA MATRİSİ</span>
        <span style="color:#34d399; font-size:0.9rem;">📅 {bugun_str} VARDİYA AMİRLERİ: SİNAN GÜL // MUSTAFA ÇETİN</span>
    </div>
    """, unsafe_allow_html=True)

    # 1. ÜST LİMAN VE CİNSİ BAŞLIKLARI
    st.markdown("""
    <div class="excel-top-header">
        <div class="head-mmk">MMK PORT / SAHA 1<br><small style="color:#facc15;">HURDA / DÖKME YÜK</small></div>
        <div class="head-eyap">EYAP LİMANI<br><small style="color:#facc15;">SİLİS KUMU</small></div>
        <div class="head-guub">GÜUB LİMANI<br><small style="color:#facc15;">ÇİMENTO</small></div>
        <div class="head-isken">İSKEN SANTRAL<br><small style="color:#facc15;">KÖMÜR</small></div>
        <div class="head-tosyali">TOSYALI LİMANI<br><small style="color:#facc15;">CEVHER</small></div>
    </div>
    """, unsafe_allow_html=True)

    df_ex = st.session_state.df_excel

    # 2. CANLI SAYAÇ HESAPLAMA (ÖZ MAL & DESTEK)
    c1, c2, c3, c4, c5 = st.columns(5)
    c_mmk = df_ex['mmk_hat1'].replace('', None).dropna().count() + df_ex['mmk_hat2'].replace('', None).dropna().count()
    c_eyap = df_ex['eyap_silis'].replace('', None).dropna().count()
    c_guub = df_ex['guub_cimento'].replace('', None).dropna().count()
    c_isken = df_ex['isken_komur'].replace('', None).dropna().count()
    c_tosyali = df_ex['tosyali_cevher'].replace('', None).dropna().count()

    with c1: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_mmk} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_eyap} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_guub} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_isken} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)
    with c5: st.markdown(f'<div class="counter-bar">Öz Mal: <b style="color:#34d399;">{c_tosyali} Araç</b><br>Destek: <b style="color:#f97316;">0 Araç</b></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # 3. İNTERAKTİF DÜZENLENEBİLİR E-TABLO (SPREADSHEET GRID)
    t1, t2, t3, t4, t5 = st.columns([2.5, 1, 1, 1, 1])
    with t1:
        arama = st.text_input("🔍 Matriste Plaka Ara:", placeholder="Örn: 31 ANM...").upper()
    with t2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        # BARIŞÇIL UNDO (GERİ AL) BUTONU
        if st.button("↩️ Geri Al (Ctrl+Z)", use_container_width=True):
            if len(st.session_state.history) > 1:
                st.session_state.history.pop()  # Son halini at
                st.session_state.df_excel = st.session_state.history[-1].copy()
                st.rerun()
            else:
                st.toast("⚠️ Geri alınacak başka işlem kalmadı!")
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

    # Değişiklik Tespiti ve History Güncelleme
    if not edited.equals(st.session_state.df_excel) and not arama:
        st.session_state.df_excel = edited
        st.session_state.history.append(edited.copy())

    if st.button("💾 Sevkiyat Matrisinde Yapılan Değişiklikleri Veritabanına Kaydet", type="primary", use_container_width=True):
        if not arama:
            st.session_state.df_excel = edited
            save_data(edited, "excel_matris")
            st.success("✅ Veriler `simsek_os.db` veritabanına başarıyla kaydedildi!")
            st.rerun()
        else:
            st.warning("Arama modundayken kaydetme yapılamaz. Lütfen arama alanını temizleyin.")

    # 4. ALT SEKMELER (ORİJİNAL EXCEL ALT SEKME ÇUBUĞU)
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("📂 EXCEL SAYFA SEKMELERİ:")
    b1, b2, b3, b4, b5 = st.columns(5)
    b1.button("📊 AYLIK ÖZET", use_container_width=True)
    b2.button("👥 ARAÇ GRUP DÜZENİ", use_container_width=True)
    b3.button("🚍 ARAÇ VERİTABANI", use_container_width=True)
    b4.button(f"📅 {bugun_str}", use_container_width=True)
    b5.button("🟢 GÜNCEL SEVKİYAT", type="primary", use_container_width=True)

# --- DİĞER MODÜLLER ---
elif menu == "📊 Dashboard & Yönetici Özeti":
    st.subheader("Günün Operasyonel Özeti")
    st.info("Saha verileri ve canlı sayaçlar doğrudan Güncel Sevkiyat sekmesinden beslenmektedir.")

elif menu == "Master Filo & Öz Mal (HR)":
    st.subheader("🚍 Şirket Öz Mal Filo Veritabanı")
    df_f = st.session_state.df_filo
    if len(df_f) > 0:
        st.dataframe(df_f, use_container_width=True, hide_index=True)
    else:
        st.info("Filoda henüz kayıtlı araç yok. Aşağıdaki formdan ekleyebilirsiniz.")
    
    with st.form("yeni_arac"):
        c1, c2, c3 = st.columns(3)
        p = c1.text_input("Plaka").upper()
        d = c2.text_input("Dorse Plaka").upper()
        t = c3.selectbox("Tip", ["Damper", "Sal", "Lowbed", "Kılçık", "Kamyon"])
        if st.form_submit_button("Aracı Kaydet", type="primary"):
            if p:
                conn = sqlite3.connect(DB_FILE)
                conn.execute("INSERT OR REPLACE INTO filo (plaka, dorse, tip, durum) VALUES (?,?,?,?)", (p, d, t, "AKTİF"))
                conn.commit(); conn.close()
                st.session_state.df_filo = load_data("filo")
                st.rerun()

else:
    st.info(f"ℹ️ **{menu}** modülü aktif ve kullanıma hazırdır.")
