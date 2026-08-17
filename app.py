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
    page_title="ŞimşekLog | Multi-Tenant Enterprise OS",
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
# 2. GLOBAL CSS (EXECUTIVE TEMA & KOLON SAYAÇ KARTLARI)
# =========================================================
st.markdown("""
<style>
    .stAppHeader, #MainMenu, footer, header { display: none !important; }
    
    [data-testid="stSidebar"] {
        background-color: #0a1120 !important;
        border-right: 1px solid #1e293b !important;
    }

    .stApp { background-color: #050b14 !important; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }

    div[data-testid="stRadio"] > div { gap: 8px; }
    div[data-testid="stRadio"] label {
        background-color: #111827; border: 1px solid #1f2937; border-radius: 8px;
        padding: 12px 15px; color: #94a3b8; font-weight: 600; cursor: pointer; transition: all 0.2s ease;
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

    /* KOLON SAYAÇ KARTLARI */
    .col-counter-card {
        background: #0f172a; border: 1px solid #334155; border-radius: 8px;
        padding: 10px; text-align: center; margin-bottom: 8px;
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
        CREATE TABLE IF NOT EXISTS sevkiyat (
            sira INTEGER PRIMARY KEY AUTOINCREMENT,
            hat_1 TEXT, hat_2 TEXT, hat_3 TEXT,
            hat_4 TEXT, kademe_soforsuz TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS filo (
            plaka TEXT PRIMARY KEY, dorse TEXT, tip TEXT,
            sofor_1 TEXT, sofor_2 TEXT, grup TEXT, durum TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS matris_basliklar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT UNIQUE, baslik_adi TEXT
        )
    ''')
    
    # Basliklar bos ise varsayilanlari at
    c.execute("SELECT COUNT(*) FROM matris_basliklar")
    if c.fetchone()[0] == 0:
        varsayilan = [
            ("hat_1", "EKİNCİLER LİMANI"),
            ("hat_2", "TOSYALI LİMANI"),
            ("hat_3", "LİMAN DEPO / FAZLAR"),
            ("hat_4", "ERW / İSDEMİR / OSM"),
            ("kademe_soforsuz", "🚨 KADEME / ŞOFÖRSÜZ")
        ]
        c.executemany("INSERT INTO matris_basliklar (kod, baslik_adi) VALUES (?,?)", varsayilan)
    
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

def get_basliklar():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM matris_basliklar", conn)
    conn.close()
    return dict(zip(df['kod'], df['baslik_adi']))

if "df_sevkiyat" not in st.session_state: st.session_state.df_sevkiyat = load_data("sevkiyat")
if "df_filo" not in st.session_state: st.session_state.df_filo = load_data("filo")

# =========================================================
# 4. YETKİLENDİRME & NAVİGASYON
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
        "📊 Dashboard & Yönetici Özeti",
        "🟢 Canlı Sevkiyat Matrisi (Grid)",
        "Master Filo & Öz Mal (HR)",
        "👥 Vardiya Amirleri & İK",
        "🚨 Kademe, Muayene & Lastik"
    ]
    
    menu = st.radio("NAVİGASYON", menuler, label_visibility="collapsed")

# Header
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
# 5. DİNAMİK MODÜLLER
# =========================================================

# --- MODÜL 1: CANLI SEVKİYAT MATRİSİ (Geliştirilmiş) ---
if menu == "🟢 Canlı Sevkiyat Matrisi (Grid)":
    
    baslik_dict = get_basliklar()
    df_f = st.session_state.df_filo
    
    # DORSE RENK/İKON EŞLEŞTİRME HARİTASI
    dorse_map = {}
    if len(df_f) > 0 and 'tip' in df_f.columns:
        for _, r in df_f.iterrows():
            tip = str(r['tip']).lower()
            if 'damper' in tip: dorse_map[r['plaka']] = "🟨 [Damper]"
            elif 'sal' in tip: dorse_map[r['plaka']] = "🟦 [Sal]"
            elif 'lowbed' in tip: dorse_map[r['plaka']] = "🟥 [Lowbed]"
            elif 'kılçık' in tip: dorse_map[r['plaka']] = "🟪 [Kılçık]"
            else: dorse_map[r['plaka']] = "🟩 [Diğer]"

    # ÜST BAŞLIKLARI DEĞİŞTİRME PANELİ (Açılır-Kapanır)
    with st.expander("🛠️ Matris Üst Başlıklarını / Tesis İsimlerini Düzenle"):
        with st.form("baslik_formu"):
            b1, b2, b3, b4, b5 = st.columns(5)
            nb1 = b1.text_input("Kolon 1 İsmi:", value=baslik_dict.get("hat_1", "HAT 1"))
            nb2 = b2.text_input("Kolon 2 İsmi:", value=baslik_dict.get("hat_2", "HAT 2"))
            nb3 = b3.text_input("Kolon 3 İsmi:", value=baslik_dict.get("hat_3", "HAT 3"))
            nb4 = b4.text_input("Kolon 4 İsmi:", value=baslik_dict.get("hat_4", "HAT 4"))
            nb5 = b5.text_input("Kolon 5 İsmi:", value=baslik_dict.get("kademe_soforsuz", "KADEME"))
            
            if st.form_submit_button("💾 Başlıkları Güncelle ve Kaydet", type="primary"):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                c.execute("UPDATE matris_basliklar SET baslik_adi = ? WHERE kod = 'hat_1'", (nb1,))
                c.execute("UPDATE matris_basliklar SET baslik_adi = ? WHERE kod = 'hat_2'", (nb2,))
                c.execute("UPDATE matris_basliklar SET baslik_adi = ? WHERE kod = 'hat_3'", (nb3,))
                c.execute("UPDATE matris_basliklar SET baslik_adi = ? WHERE kod = 'hat_4'", (nb4,))
                c.execute("UPDATE matris_basliklar SET baslik_adi = ? WHERE kod = 'kademe_soforsuz'", (nb5,))
                conn.commit(); conn.close()
                st.success("✅ Kolon üst başlıkları güncellendi!")
                st.rerun()

    # HER KOLON İÇİN ANLIK ARAÇ SAYDIRMA ALANI (KOLON SAYAÇLARI)
    df_s = st.session_state.df_sevkiyat
    cols_key = ["hat_1", "hat_2", "hat_3", "hat_4", "kademe_soforsuz"]
    
    st.markdown("#### 📊 Tesis / Hat Bazlı Anlık Araç Sayıları")
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    s_cols = [sc1, sc2, sc3, sc4, sc5]
    
    for i, ck in enumerate(cols_key):
        b_adi = baslik_dict.get(ck, ck)
        count = df_s[ck].replace('', None).dropna().count() if ck in df_s.columns else 0
        s_cols[i].markdown(f"""
        <div class="col-counter-card">
            <span style="color:#94a3b8; font-size:0.75rem;">{b_adi[:20]}</span><br>
            <b style="color:#38bdf8; font-size:1.2rem;">{count} Araç</b>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # DÜZENLEME ARAÇ ÇUBUĞU
    t1, t2, t3, t4 = st.columns([3, 1, 1, 1])
    with t1:
        arama = st.text_input("🔍 Hızlı Plaka / Tesis Arama:", placeholder="Plaka yazın...").upper()
    with t2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        csv = st.session_state.df_sevkiyat.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Excel İndir", csv, "Canli_Sevkiyat.csv", "text/csv", use_container_width=True)
    with t3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ 5 Satır Ekle", use_container_width=True):
            boslar = pd.DataFrame([{"sira": None, "hat_1": "", "hat_2": "", "hat_3": "", "hat_4": "", "kademe_soforsuz": ""} for _ in range(5)])
            st.session_state.df_sevkiyat = pd.concat([st.session_state.df_sevkiyat, boslar], ignore_index=True)
            st.rerun()
    with t4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("🧹 Boşları Temizle", use_container_width=True):
            cols_check = [c for c in st.session_state.df_sevkiyat.columns if c != 'sira']
            st.session_state.df_sevkiyat = st.session_state.df_sevkiyat.dropna(how='all', subset=cols_check)
            save_data(st.session_state.df_sevkiyat, "sevkiyat")
            st.rerun()

    df_disp = st.session_state.df_sevkiyat.copy()
    if arama:
        mask = df_disp.apply(lambda r: r.astype(str).str.contains(arama, case=False).any(), axis=1)
        df_disp = df_disp[mask]

    # DİNAMİK BAŞLIK BİNDİRME VE EDİTÖR
    config = {
        "sira": st.column_config.NumberColumn("SIRA", disabled=True),
        "hat_1": st.column_config.TextColumn(baslik_dict.get("hat_1", "HAT 1"), width="medium"),
        "hat_2": st.column_config.TextColumn(baslik_dict.get("hat_2", "HAT 2"), width="medium"),
        "hat_3": st.column_config.TextColumn(baslik_dict.get("hat_3", "HAT 3"), width="medium"),
        "hat_4": st.column_config.TextColumn(baslik_dict.get("hat_4", "HAT 4"), width="medium"),
        "kademe_soforsuz": st.column_config.TextColumn(baslik_dict.get("kademe_soforsuz", "KADEME"), width="medium"),
    }
    
    edited = st.data_editor(df_disp, column_config=config, num_rows="dynamic", use_container_width=True, height=450, hide_index=True)
    
    if st.button("💾 Sevkiyat Matrisini Kaydet", type="primary", use_container_width=True):
        if not arama:
            st.session_state.df_sevkiyat = edited
            save_data(edited, "sevkiyat")
            st.success("✅ Sevkiyat veritabanına kaydedildi!")
            st.rerun()
        else:
            st.warning("Arama yaparken kaydetme yapılamaz. Lütfen aramayı temizleyin.")

# --- MODÜL 2: MASTER FİLO & ÖZ MAL (Dorse Tipi Kodlaması) ---
elif menu == "Master Filo & Öz Mal (HR)":
    st.subheader("🚍 Şirket Öz Mal Filo Veritabanı & Dorse Tipleri")
    st.caption("Dorse tipleri Canlı Sevkiyat Matrisindeki araç etiketlerini ve renk kodlamalarını belirler.")
    
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
        nt = c3.selectbox("Dorse Tipi (Renk Etiketi Belirler)", ["Damper (🟨)", "Sal (🟦)", "Lowbed (🟥)", "Kılçık (🟪)", "Havuz", "Kapanır Sal", "Kamyon"])
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

# --- DİĞER MODÜLLER ---
else:
    st.info(f"ℹ️ **{menu}** modülü aktif ve kullanıma hazırdır.")
