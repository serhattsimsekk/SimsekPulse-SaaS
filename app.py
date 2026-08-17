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
    page_title="ŞimşekLog | Enterprise Supply Chain OS",
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
# 2. GLOBAL CSS (SERBEST SOL MENÜ BUTONU & DARK EXECUTIVE TEMA)
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
        background-color: #0a1120 !important;
        border-right: 1px solid #1e293b !important;
    }

    .stApp { background-color: #050b14 !important; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }

    div[data-testid="stRadio"] > div { gap: 6px; }
    div[data-testid="stRadio"] label {
        background-color: #111827; border: 1px solid #1f2937; border-radius: 8px;
        padding: 10px 14px; color: #94a3b8; font-weight: 600; cursor: pointer; transition: all 0.2s ease;
    }
    div[data-testid="stRadio"] label:hover { border-color: #38bdf8; color: #e2e8f0; }
    div[data-testid="stRadio"] label[data-checked="true"] {
        background: linear-gradient(90deg, #0f172a, #0369a1) !important;
        border-left: 4px solid #38bdf8 !important; border-color: #0284c7 !important; color: #ffffff !important;
    }

    .vip-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155; border-radius: 12px; padding: 15px 25px;
        margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.5);
    }

    .excel-main-title {
        background: #0f172a; border: 1px solid #334155; border-radius: 8px;
        padding: 10px 20px; color: #38bdf8; font-weight: 800; font-size: 1.15rem;
        display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;
    }

    .excel-top-header {
        display: grid; grid-template-columns: 1fr 1fr 1fr 1fr 1fr; gap: 4px;
        text-align: center; font-weight: bold; font-size: 0.85rem; margin-bottom: 6px;
    }
    .head-m1 { background: #1e3a8a; color: #ffffff; padding: 8px; border-radius: 4px; }
    .head-m2 { background: #0284c7; color: #ffffff; padding: 8px; border-radius: 4px; }
    .head-m3 { background: #0369a1; color: #ffffff; padding: 8px; border-radius: 4px; }
    .head-m4 { background: #581c87; color: #ffffff; padding: 8px; border-radius: 4px; }
    .head-m5 { background: #9a3412; color: #ffffff; padding: 8px; border-radius: 4px; }

    .counter-bar {
        background: #1e293b; border: 1px solid #334155; border-radius: 6px;
        padding: 8px; text-align: center; font-size: 0.85rem; font-weight: 600;
    }

    .metric-card {
        background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(10px);
        border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 10px; padding: 15px; text-align: center;
    }
    
    .fis-card {
        background: #0f172a; border: 1px solid #1e293b; border-radius: 10px;
        padding: 15px; margin-bottom: 12px;
    }

    .dup-alarm {
        background: rgba(244, 63, 94, 0.15); border: 1px solid #f43f5e;
        color: #fca5a5; border-radius: 8px; padding: 10px 15px; margin-bottom: 12px; font-weight: bold;
    }
    .c-ozmal { color: #34d399; font-weight: bold; }
    .c-alert { color: #f43f5e; font-weight: bold; }
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
            plaka TEXT PRIMARY KEY, dorse TEXT, tip TEXT,
            sofor_1 TEXT, sofor_2 TEXT, grup TEXT, durum TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS finans_tarife (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tesis_adi TEXT, birim_fiyat REAL, toplam_tonaj REAL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS whatsapp_gruplar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grup_adi TEXT, grup_id TEXT, bildirim_tipi TEXT, aktif INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS kantar_fisleri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            grup_adi TEXT, gonderen TEXT, plaka TEXT,
            net_tonaj REAL, tesis TEXT, tarih_saat TEXT, durum TEXT
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

if "df_excel" not in st.session_state: st.session_state.df_excel = load_data("excel_matris")
if "df_filo" not in st.session_state: st.session_state.df_filo = load_data("filo")
if "df_finans" not in st.session_state: st.session_state.df_finans = load_data("finans_tarife")
if "df_wa" not in st.session_state: st.session_state.df_wa = load_data("whatsapp_gruplar")
if "df_fisler" not in st.session_state: st.session_state.df_fisler = load_data("kantar_fisleri")

if "history" not in st.session_state:
    st.session_state.history = [st.session_state.df_excel.copy()]

# =========================================================
# 4. YETKİLENDİRME & SOL NAVİGASYON (RBAC)
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 10px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:900; letter-spacing: 1px;">⚡ ŞimşekLog</h2>
            <span style="color: #64748B; font-size: 0.75rem; font-weight:700;">SUPPLY CHAIN OS v4.0</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # "DEPARTMAN MÜDÜRÜ" ROLÜ EKLENDİ
    kullanici_rolu = st.selectbox(
        "👤 AKTİF KULLANICI ROLÜ:",
        [
            "👑 Patron (Yönetici)", 
            "🏢 Departman Müdürü", 
            "💼 Muhasebe Departmanı", 
            "🚚 Sevkiyatçı / Vardiya Amiri", 
            "👮‍♂️ Baş Şoför"
        ],
        index=0
    )
    
    st.markdown("---")
    
    menuler = [
        "📊 Dashboard & Yönetici Özeti",
        "🟢 Canlı Sevkiyat Matrisi (Grid)",
        "📱 WhatsApp Kantar Fişi Akışı",
        "Master Filo & Öz Mal (HR)",
        "👥 Vardiya Amirleri & İK",
        "🚨 Kademe, Muayene & Lastik"
    ]
    
    # FİNANS YETKİSİ: PATRON, DEPARTMAN MÜDÜRÜ VE MUHASEBE
    finans_yetkisi = kullanici_rolu in ["👑 Patron (Yönetici)", "🏢 Departman Müdürü", "💼 Muhasebe Departmanı"]
    
    # PATRON ÖZEL YETKİSİ
    patron_yetkisi = kullanici_rolu == "👑 Patron (Yönetici)"
    
    if finans_yetkisi:
        menuler.append("💼 Finans, Faturalama & Ciro")
    if patron_yetkisi:
        menuler.append("⚙️ WhatsApp Grup Ayarları")
        
    menuler.append("🌐 B2B E-Ticaret & Kurye Ağı")
    
    menu = st.radio("NAVİGASYON", menuler, label_visibility="collapsed")
    
    st.divider()
    if finans_yetkisi:
        st.markdown("""
            <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; padding: 10px; text-align: center;">
                <span style="color: #34d399; font-size: 0.75rem; font-weight: 700;">🔓 FİNANSAL YETKİ AKTİF</span>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
            <div style="background: rgba(244, 63, 94, 0.1); border: 1px solid rgba(244, 63, 94, 0.2); border-radius: 8px; padding: 10px; text-align: center;">
                <span style="color: #f43f5e; font-size: 0.75rem; font-weight: 700;">🔒 SAHA MODU (FİNANS KİLİTLİ)</span>
            </div>
        """, unsafe_allow_html=True)

# Üst Header Banner
st.markdown(f"""
<div class="vip-header">
    <div>
        <h3 style="margin:0; color:#38bdf8; font-weight:800;">{menu.upper()}</h3>
        <span style="color:#94a3b8; font-size:0.85rem;">ŞimşekLog Kurumsal Saha & Filo Yönetim Portalı</span>
    </div>
    <div style="text-align:right;">
        <span style="color:#f8fafc; font-weight:bold; font-size:1.1rem;">{datetime.now().strftime("%d.%m.%Y")}</span><br>
        <span style="color:#34d399; font-size:0.8rem; font-weight:600;">ROL: {kullanici_rolu.upper()}</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 5. DİNAMİK MODÜLLERİN TAMAMI
# =========================================================

# --- MODÜL 1: DASHBOARD ---
if menu == "📊 Dashboard & Yönetici Özeti":
    st.subheader("Günün Lojistik ve Operasyonel Özeti")
    
    df_f = st.session_state.df_filo
    df_s = st.session_state.df_excel
    df_k = st.session_state.df_fisler
    
    toplam_ozmal = len(df_f)
    aktif_ozmal = len(df_f[df_f['durum'] == 'AKTİF']) if 'durum' in df_f.columns and toplam_ozmal > 0 else 0
    pasif_ozmal = toplam_ozmal - aktif_ozmal
    verim = (aktif_ozmal / toplam_ozmal * 100) if toplam_ozmal > 0 else 0.0
    bekleyen_fisler = len(df_k[df_k['durum'] == 'Bekliyor']) if len(df_k) > 0 and 'durum' in df_k.columns else 0

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-card"><span style="color:#94a3b8;">Kayıtlı Öz Mal Filo</span><br><b style="color:#38bdf8; font-size:1.5rem;">{toplam_ozmal} Araç</b></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-card"><span style="color:#94a3b8;">Filo Verimlilik %</span><br><b class="c-ozmal" style="font-size:1.5rem;">%{verim:.1f}</b></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-card"><span style="color:#94a3b8;">Bekleyen Kantar Fişleri</span><br><b style="color:#facc15; font-size:1.5rem;">{bekleyen_fisler} Fiş</b></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-card"><span style="color:#94a3b8;">Matristeki Atama Sayısı</span><br><b style="color:#38bdf8; font-size:1.5rem;">{len(df_s)} Satır</b></div>', unsafe_allow_html=True)
    
    st.divider()
    st.markdown("#### 🚨 Akıllı Saha Uyarısı")
    if bekleyen_fisler > 0:
        st.warning(f"⚠️ **İşlem Bekleyen Kantar Fişleri:** WhatsApp gruplarından gelen **{bekleyen_fisler}** adet kantar fişi onay bekliyor. **WhatsApp Kantar Fişi Akışı** sekmesinden onaylayabilirsiniz.")
    elif toplam_ozmal == 0:
        st.info("ℹ️ **Henüz Veri Girilmedi:** Şirketinize ait araçları eklemek için **Master Filo & Öz Mal (HR)** sekmesini kullanabilirsiniz.")
    else:
        st.success("✅ **Saha Mükemmel:** İşlenmeyen kantar fişi yok ve tüm sistem güncel.")

# --- MODÜL 2: CANLI SEVKİYAT MATRİSİ (FULL EXCEL DÜZENİ) ---
elif menu == "🟢 Canlı Sevkiyat Matrisi (Grid)":
    
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

    # 7. ALT SEKMELER (ORİJİNAL EXCEL ALT SEKME BARI)
    st.markdown("<br>", unsafe_allow_html=True)
    st.caption("📂 EXCEL SAYFA SEKMELERİ:")
    b1, b2, b3, b4, b5 = st.columns(5)
    b1.button("📊 AYLIK ÖZET", use_container_width=True)
    b2.button("👥 ARAÇ GRUP DÜZENİ", use_container_width=True)
    b3.button("VIP ARAÇ VERİTABANI", use_container_width=True)
    b4.button(f"📅 {bugun_str}", use_container_width=True)
    b5.button("🟢 GÜNCEL SEVKİYAT", type="primary", use_container_width=True)

# --- MODÜL 3: WHATSAPP KANTAR FİŞİ AKIŞI ---
elif menu == "📱 WhatsApp Kantar Fişi Akışı":
    st.subheader("📲 WhatsApp Gruplarından Gelen Canlı Kantar Fişi Akışı")
    
    tab_akil, tab_simulasyon = st.tabs(["📩 Gelen Fiş Havuzu & Onay Paneli", "🧪 Canlı WhatsApp Fiş Gönderme Simülatörü"])
    
    with tab_akil:
        df_k = st.session_state.df_fisler
        if len(df_k) == 0:
            st.info("ℹ️ Henüz WhatsApp gruplarından gelen kantar fişi yok. Yan sekmedeki simülatörden test fişi gönderebilirsiniz.")
        else:
            bekleyenler = df_k[df_k['durum'] == 'Bekliyor']
            islenenler = df_k[df_k['durum'] == '✅ İşlendi']
            
            st.markdown(f"#### ⏳ Onay Bekleyen Fişler ({len(bekleyenler)})")
            
            if len(bekleyenler) == 0:
                st.success("✅ Onay bekleyen kantar fişi yok, tüm fişler matrise işlendi.")
            else:
                for idx, row in bekleyenler.iterrows():
                    with st.container():
                        st.markdown(f"""
                        <div class="fis-card">
                            <b style="color:#38bdf8;">🚛 Plaka: {row['plaka']}</b> | 📍 <b>Tesis:</b> {row['tesis']} | ⚖️ <b>Net:</b> {row['net_tonaj']} Ton <br>
                            <small style="color:#94a3b8;">📲 WhatsApp Grubu: {row['grup_adi']} | ⏳ {row['tarih_saat']}</small>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        col_a, col_b = st.columns([2, 2])
                        with col_a:
                            hedef_hat = st.selectbox(f"Hangi Hatta İşlensin? (Fiş #{row['id']})", 
                                                     ["mmk_hat1", "mmk_hat2", "eyap_silis", "guub_cimento", "isken_komur", "tosyali_cevher"], key=f"hat_{row['id']}")
                        with col_b:
                            if st.button(f"⚡ Matrise Aktar (#{row['id']})", type="primary", key=f"btn_{row['id']}"):
                                conn = sqlite3.connect(DB_FILE)
                                c = conn.cursor()
                                c.execute("UPDATE kantar_fisleri SET durum = '✅ İşlendi' WHERE id = ?", (row['id'],))
                                c.execute(f"INSERT INTO excel_matris ({hedef_hat}) VALUES (?)", (row['plaka'],))
                                conn.commit(); conn.close()
                                st.session_state.df_fisler = load_data("kantar_fisleri")
                                st.session_state.df_excel = load_data("excel_matris")
                                st.success(f"✅ **{row['plaka']}** matrise eklendi!")
                                st.rerun()

            if len(islenenler) > 0:
                st.divider()
                st.markdown(f"#### ✅ Geçmişte İşlenen Fişler ({len(islenenler)})")
                st.dataframe(islenenler, use_container_width=True, hide_index=True)

    with tab_simulasyon:
        with st.form("simulasyon_formu"):
            s1, s2, s3 = st.columns(3)
            sim_plaka = s1.text_input("Araç Plakası:", value="31 ANM 999").upper()
            sim_tonaj = s2.number_input("Net Tonaj (Ton):", value=28.5)
            sim_tesis = s3.selectbox("Tesis / Liman:", ["MMK PORT", "EYAP LİMANI", "GÜÜB LİMANI", "İSKEN SANTRAL", "TOSYALI LİMANI"])
            
            if st.form_submit_button("📲 WhatsApp Fişi Olarak Gönder", type="primary", use_container_width=True):
                if sim_plaka.strip():
                    su_an = datetime.now().strftime("%d.%m.%Y %H:%M")
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("INSERT INTO kantar_fisleri (grup_adi, gonderen, plaka, net_tonaj, tesis, tarih_saat, durum) VALUES (?,?,?,?,?,?,?)",
                                 ("Vardiya Grubu", "+90 532 XXX XX XX", sim_plaka.strip(), sim_tonaj, sim_tesis, su_an, "Bekliyor"))
                    conn.commit(); conn.close()
                    st.session_state.df_fisler = load_data("kantar_fisleri")
                    st.success("📲 Fiş WhatsApp havuzuna düştü!")
                    st.rerun()

# --- MODÜL 4: MASTER FİLO & ÖZ MAL ---
elif menu == "Master Filo & Öz Mal (HR)":
    st.subheader("🚍 Şirket Öz Mal Filo Veritabanı & Dorse Tipleri")
    
    df_f = st.session_state.df_filo
    if len(df_f) > 0:
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=350)
    else:
        st.info("ℹ️ Şirketinizin veritabanında henüz kayıtlı araç bulunmamaktadır. Aşağıdaki formdan ilk aracınızı ekleyebilirsiniz.")
    
    st.markdown("#### ➕ Veritabanına Yeni Öz Mal Araç Ekle")
    with st.form("yeni_arac_formu"):
        c1, c2, c3, c4 = st.columns(4)
        np = c1.text_input("Çekici Plaka *").upper()
        nd = c2.text_input("Dorse Plaka").upper()
        nt = c3.selectbox("Dorse Tipi", ["Damper", "Sal", "Lowbed", "Kılçık", "Havuz", "Kapanır Sal", "Kamyon"])
        ng = c4.text_input("Saha Amiri / Grup Adı").upper()
        
        c5, c6, c7 = st.columns(3)
        s1 = c5.text_input("1. Şoför Adı Soyadı")
        s2 = c6.text_input("2. Şoför Adı Soyadı (Çift Şoför)")
        durum_secim = c7.selectbox("Araç Durumu", ["AKTİF", "KADEME", "ŞOFÖRSÜZ", "YEDEK"])
        
        if st.form_submit_button("➕ Aracı Şirket Veritabanına Ekle", type="primary", use_container_width=True):
            if np.strip():
                conn = sqlite3.connect(DB_FILE)
                conn.execute("INSERT OR REPLACE INTO filo (plaka, dorse, tip, sofor_1, sofor_2, grup, durum) VALUES (?,?,?,?,?,?,?)", 
                             (np.strip(), nd.strip(), nt, s1.strip(), s2.strip(), ng.strip(), durum_secim))
                conn.commit(); conn.close()
                st.session_state.df_filo = load_data("filo")
                st.success(f"✅ **{np}** plakalı araç veritabanına eklendi!")
                st.rerun()

# --- MODÜL 5: VARDİYA AMİRLERİ & İK ---
elif menu == "👥 Vardiya Amirleri & İK":
    st.subheader("👥 Saha Amir Grupları & Vardiya Yönetimi")
    df_f = st.session_state.df_filo
    if len(df_f) > 0 and 'grup' in df_f.columns and len(df_f['grup'].replace('', None).dropna()) > 0:
        gruplar = df_f['grup'].replace('', None).dropna().unique()
        cols = st.columns(min(len(gruplar), 4) if len(gruplar) > 0 else 1)
        for i, g in enumerate(gruplar):
            with cols[i % len(cols)]:
                 count = len(df_f[df_f['grup'] == g])
                 st.markdown(f"### 📌 {g}")
                 st.info(f"Gruptaki Araç Sayısı: **{count}**")
                 st.dataframe(df_f[df_f['grup'] == g][['plaka', 'sofor_1', 'durum']], hide_index=True)
    else:
        st.info("ℹ️ Henüz gruplandırılmış araç bulunmamaktadır. **Master Filo** sekmesinden araç eklerken grup adı tanımlayabilirsiniz.")

# --- MODÜL 6: KADEME & MUAYENE ---
elif menu == "🚨 Kademe, Muayene & Lastik":
    st.subheader("🛠️ Kademe Arıza ve Bakım Takip Paneli")
    df_f = st.session_state.df_filo
    if len(df_f) > 0:
        kademede = df_f[df_f['durum'] == 'KADEME']
        if len(kademede) > 0:
            st.error(f"🚨 **Kademede / Arızada Olan Araç Sayısı: {len(kademede)}**")
            st.dataframe(kademede[['plaka', 'dorse', 'grup', 'sofor_1']], use_container_width=True, hide_index=True)
        else:
            st.success("✅ Veritabanınızda kademede veya arızada yatan araç bulunmamaktadır.")
    else:
        st.info("ℹ️ Kayıtlı araç bulunamadı.")

# --- MODÜL 7: FİNANS & FATURALAMA ---
elif menu == "💼 Finans, Faturalama & Ciro":
    if not finans_yetkisi:
        st.error("⛔ **ERİŞİM ENGELLEDİ:** Bu ekrana sadece **Patron**, **Departman Müdürü** veya **Muhasebe** yetkisi olan kullanıcılar erişebilir.")
    else:
        st.subheader("💼 Şirkete Özel Dinamik Maliyet ve Hakediş Paneli")
        
        with st.form("finans_formu"):
            f1, f2, f3 = st.columns(3)
            t_ad = f1.text_input("Tesis / Müşteri Adı:", placeholder="Örn: X Fabrikası")
            t_ton = f2.number_input("Taşınan Toplam Tonaj:", min_value=0.0, value=0.0)
            t_fiyat = f3.number_input("Birim Fiyat (TL/Ton):", min_value=0.0, value=0.0)
            
            if st.form_submit_button("➕ Hakediş Hesabını Veritabanına Kaydet", type="primary", use_container_width=True):
                if t_ad.strip():
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("INSERT INTO finans_tarife (tesis_adi, birim_fiyat, toplam_tonaj) VALUES (?,?,?)",
                                 (t_ad.strip(), t_fiyat, t_ton))
                    conn.commit(); conn.close()
                    st.session_state.df_finans = load_data("finans_tarife")
                    st.success("✅ Hakediş veritabanına işlendi!")
                    st.rerun()

        df_fin = st.session_state.df_finans
        if len(df_fin) > 0:
            df_fin['Tahmini_Ciro_TL'] = df_fin['toplam_tonaj'] * df_fin['birim_fiyat']
            st.divider()
            st.markdown("#### 📊 Kayıtlı Hakedişler ve Tahmini Faturalar")
            st.dataframe(df_fin, use_container_width=True, hide_index=True)
            toplam_ciro = df_fin['Tahmini_Ciro_TL'].sum()
            st.success(f"💰 **Toplam Tahmini Kesilecek Fatura Tutarı: ₺ {toplam_ciro:,.2f}**")

# --- MODÜL 8: WHATSAPP GRUP AYARLARI ---
elif menu == "⚙️ WhatsApp Grup Ayarları":
    if not patron_yetkisi:
        st.error("⛔ **ERİŞİM ENGELLEDİ:** Bu ekrana sadece **Patron (Yönetici)** erişebilir.")
    else:
        st.subheader("⚙️ İsteğe Bağlı WhatsApp Grup Yönetim Paneli")
        with st.form("wa_grup_formu"):
            w1, w2, w3 = st.columns(3)
            g_ad = w1.text_input("Grup / Kanal Adı:", placeholder="Örn: Vardiya & Operasyon Grubu")
            g_id = w2.text_input("WhatsApp Group ID / Tel No:", placeholder="Örn: 90532XXXXXXX veya 120363@g.us")
            g_tip = w3.selectbox("Otomatik Gönderilecek Bildirim Tipi:", [
                "📊 Vardiya Sonu Raporu (08:00)", "🚨 Kademe & Arıza Alarmları",
                "⚖️ Anlık Kantar Fişi Geçişleri", "📢 Tüm Bildirimler (Full Paket)"
            ])
            if st.form_submit_button("➕ WhatsApp Grubu Ekle", type="primary", use_container_width=True):
                if g_ad.strip() and g_id.strip():
                    conn = sqlite3.connect(DB_FILE)
                    conn.execute("INSERT INTO whatsapp_gruplar (grup_adi, grup_id, bildirim_tipi, aktif) VALUES (?,?,?,?)",
                                 (g_ad.strip(), g_id.strip(), g_tip, 1))
                    conn.commit(); conn.close()
                    st.session_state.df_wa = load_data("whatsapp_gruplar")
                    st.success("✅ Grup entegre edildi!")
                    st.rerun()

        df_w = st.session_state.df_wa
        if len(df_w) > 0:
            st.dataframe(df_w[['id', 'grup_adi', 'grup_id', 'bildirim_tipi', 'aktif']], use_container_width=True, hide_index=True)

# --- MODÜL 9: B2B E-TİCARET ---
elif menu == "🌐 B2B E-Ticaret & Kurye Ağı":
    st.subheader("🌐 Son Kilometre (Last-Mile) E-Ticaret Kurye Yönetimi")
    st.info("ℹ️ E-ticaret ve kargo dağıtımı yapan hafif ticari araç yönetimi alanı.")
