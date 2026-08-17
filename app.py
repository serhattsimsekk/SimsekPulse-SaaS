import streamlit as st
import pandas as pd
import sqlite3
import os
import streamlit.components.v1 as components
from datetime import datetime

# =========================================================
# 1. SAYFA YAPILANDIRMASI VE GÜVENLİK
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
# 2. GLOBAL CSS (SOL MENÜYÜ SABİTLEME VE DARALTMAYI ENGELLEME)
# =========================================================
st.markdown("""
<style>
    /* Üst menü, header vevarsayılan çubukları gizle */
    .stAppHeader, #MainMenu, footer, header { display: none !important; }
    
    /* SOL MENÜYÜ SABİTLE VE DARALTMA BUTONUNU GİZLE (KAPANMASINI ENGELLER) */
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {
        display: none !important;
        visibility: hidden !important;
    }
    
    [data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 280px !important;
        background-color: #0a1120 !important;
        border-right: 1px solid #1e293b !important;
    }

    /* Arka plan ve genel yapı */
    .stApp { background-color: #050b14 !important; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }

    /* Sol Sidebar Buton Stilleri */
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

    /* VIP Header Banner */
    .vip-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
        border: 1px solid #334155; border-radius: 12px; padding: 15px 25px;
        margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center;
        box-shadow: 0 8px 16px rgba(0,0,0,0.5);
    }

    /* Metrik Kartları */
    .metric-card {
        background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(10px);
        border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 10px;
        padding: 15px; text-align: center;
    }
    .c-ozmal { color: #34d399; font-weight: bold; }
    .c-alert { color: #f43f5e; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. ŞİRKETE ÖZEL DİNAMİK VERİTABANI MİMARİSİ (SQLite)
# =========================================================
DB_FILE = "simsek_os.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Sevkiyat Matrisi
    c.execute('''
        CREATE TABLE IF NOT EXISTS sevkiyat (
            sira INTEGER PRIMARY KEY AUTOINCREMENT,
            ekinciler_liman TEXT, tosyali_liman TEXT, liman_depo TEXT,
            erw_isdemir TEXT, kademe_soforsuz TEXT
        )
    ''')
    # Filo Envanteri
    c.execute('''
        CREATE TABLE IF NOT EXISTS filo (
            plaka TEXT PRIMARY KEY, dorse TEXT, tip TEXT,
            sofor_1 TEXT, sofor_2 TEXT, grup TEXT, durum TEXT
        )
    ''')
    # Finans & Tarife Ayarları
    c.execute('''
        CREATE TABLE IF NOT EXISTS finans_tarife (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tesis_adi TEXT, birim_fiyat REAL, toplam_tonaj REAL
        )
    ''')
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

if "df_sevkiyat" not in st.session_state: st.session_state.df_sevkiyat = load_data("sevkiyat")
if "df_filo" not in st.session_state: st.session_state.df_filo = load_data("filo")
if "df_finans" not in st.session_state: st.session_state.df_finans = load_data("finans_tarife")

# =========================================================
# 4. SOL NAVİGASYON (SABİTLENMİŞ PANOSUN)
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:900; letter-spacing: 1px;">⚡ ŞimşekLog</h2>
            <span style="color: #64748B; font-size: 0.75rem; font-weight:700;">SUPPLY CHAIN OS v4.0</span>
        </div>
    """, unsafe_allow_html=True)
    
    menu = st.radio(
        "NAVİGASYON",
        [
            "📊 Dashboard & Yönetici Özeti",
            "🟢 Canlı Sevkiyat Matrisi (Grid)",
            "Master Filo & Öz Mal (HR)",
            "👥 Vardiya Amirleri & İK",
            "🚨 Kademe, Muayene & Lastik",
            "💼 Finans, Faturalama & Ciro",
            "🌐 B2B E-Ticaret & Kurye Ağı"
        ],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.markdown("""
        <div style="background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.2); border-radius: 8px; padding: 10px; text-align: center;">
            <span style="color: #34d399; font-size: 0.75rem; font-weight: 700;">● CANLI VERİTABANI AKTİF</span>
        </div>
    """, unsafe_allow_html=True)

# Üst Header
st.markdown(f"""
<div class="vip-header">
    <div>
        <h3 style="margin:0; color:#38bdf8; font-weight:800;">{menu.upper()}</h3>
        <span style="color:#94a3b8; font-size:0.85rem;">ŞimşekLog Kurumsal Saha & Filo Yönetim Portalı</span>
    </div>
    <div style="text-align:right;">
        <span style="color:#f8fafc; font-weight:bold; font-size:1.1rem;">{datetime.now().strftime("%d.%m.%Y")}</span><br>
        <span style="color:#34d399; font-size:0.8rem; font-weight:600;">ŞİRKET VERİTABANI BAĞLI</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 5. DİNAMİK MODÜLLER (VERİTABANINDAN BESLENİR)
# =========================================================

# --- MODÜL 1: DASHBOARD ---
if menu == "📊 Dashboard & Yönetici Özeti":
    st.subheader("Günün Lojistik ve Finansal Röntgeni")
    
    df_f = st.session_state.df_filo
    df_s = st.session_state.df_sevkiyat
    
    toplam_ozmal = len(df_f)
    aktif_ozmal = len(df_f[df_f['durum'] == 'AKTİF']) if 'durum' in df_f.columns else 0
    pasif_ozmal = toplam_ozmal - aktif_ozmal
    verim = (aktif_ozmal / toplam_ozmal * 100) if toplam_ozmal > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown(f'<div class="metric-card"><span style="color:#94a3b8;">Kayıtlı Öz Mal Filo</span><br><b style="color:#38bdf8; font-size:1.5rem;">{toplam_ozmal} Araç</b></div>', unsafe_allow_html=True)
    with m2: st.markdown(f'<div class="metric-card"><span style="color:#94a3b8;">Filo Verimlilik %</span><br><b class="c-ozmal" style="font-size:1.5rem;">%{verim:.1f}</b></div>', unsafe_allow_html=True)
    with m3: st.markdown(f'<div class="metric-card"><span style="color:#94a3b8;">Aktif / Pasif Araç</span><br><b style="color:#e2e8f0; font-size:1.5rem;">{aktif_ozmal} / <span class="c-alert">{pasif_ozmal}</span></b></div>', unsafe_allow_html=True)
    with m4: st.markdown(f'<div class="metric-card"><span style="color:#94a3b8;">Matristeki Atama Sayısı</span><br><b style="color:#facc15; font-size:1.5rem;">{len(df_s)} Satır</b></div>', unsafe_allow_html=True)
    
    st.divider()
    st.markdown("#### 🚨 Akıllı Uyarılar & Canlı Saha Durumu")
    if pasif_ozmal > 0:
        st.warning(f"⚠️ **Atıl Araç Uyarısı:** Veritabanında pasif/kademede görünen **{pasif_ozmal}** adet araç bulunmaktadır.")
    else:
        st.success("✅ **Saha Mükemmel:** Şirketinize ait tüm araçlar aktif olarak görevdedir.")

# --- MODÜL 2: CANLI SEVKİYAT MATRİSİ ---
elif menu == "🟢 Canlı Sevkiyat Matrisi (Grid)":
    
    t1, t2, t3, t4 = st.columns([3, 1, 1, 1])
    with t1:
        arama = st.text_input("🔍 Hızlı Plaka / Tesis Arama:", placeholder="Plaka veya tesis adı yazın...").upper()
    with t2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        csv = st.session_state.df_sevkiyat.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Excel İndir", csv, "Canli_Sevkiyat.csv", "text/csv", use_container_width=True)
    with t3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ 5 Satır Ekle", use_container_width=True):
            boslar = pd.DataFrame([{"sira": None, "ekinciler_liman": "", "tosyali_liman": "", "liman_depo": "", "erw_isdemir": "", "kademe_soforsuz": ""} for _ in range(5)])
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

    config = {
        "sira": st.column_config.NumberColumn("SIRA", disabled=True),
        "ekinciler_liman": st.column_config.TextColumn("EKİNCİLER LİMANI", width="medium"),
        "tosyali_liman": st.column_config.TextColumn("TOSYALI LİMANI", width="medium"),
        "liman_depo": st.column_config.TextColumn("LİMAN DEPO / FAZLAR", width="medium"),
        "erw_isdemir": st.column_config.TextColumn("ERW / İSDEMİR / OSM", width="medium"),
        "kademe_soforsuz": st.column_config.TextColumn("🚨 KADEME / ŞOFÖRSÜZ", width="medium"),
    }
    
    edited = st.data_editor(df_disp, column_config=config, num_rows="dynamic", use_container_width=True, height=480, hide_index=True)
    
    if st.button("💾 Sevkiyat Matrisini Kaydet", type="primary", use_container_width=True):
        if not arama:
            st.session_state.df_sevkiyat = edited
            save_data(edited, "sevkiyat")
            st.success("✅ Sevkiyat veritabanına kaydedildi!")
            st.rerun()
        else:
            st.warning("Arama yaparken kaydetme yapılamaz. Lütfen aramayı temizleyin.")

# --- MODÜL 3: MASTER FİLO & ÖZ MAL ---
elif menu == "Master Filo & Öz Mal (HR)":
    st.subheader("🚍 Şirket Öz Mal Filo Veritabanı")
    
    df_f = st.session_state.df_filo
    if len(df_f) > 0:
        st.dataframe(df_f, use_container_width=True, hide_index=True, height=350)
    else:
        st.info("ℹ️ Şirketinizin veritabanında henüz kayıtlı araç yok. Aşağıdaki formdan araç ekleyebilirsiniz.")
    
    st.markdown("#### ➕ Veritabanına Yeni Öz Mal Araç Ekle")
    with st.form("yeni_arac_formu"):
        c1, c2, c3, c4 = st.columns(4)
        np = c1.text_input("Çekici Plaka *").upper()
        nd = c2.text_input("Dorse Plaka").upper()
        nt = c3.selectbox("Dorse Tipi", ["Damper", "Sal", "Lowbed", "Havuz", "Kılçık", "Kapanır Sal", "Kamyon"])
        ng = c4.text_input("Saha Amiri / Grup", value="MUHİTTİN BEY").upper()
        
        c5, c6 = st.columns(2)
        s1 = c5.text_input("1. Şoför Adı Soyadı")
        s2 = c6.text_input("2. Şoför Adı Soyadı (Çift Şoför)")
        
        if st.form_submit_button("➕ Aracı Şirket Veritabanına Ekle", type="primary", use_container_width=True):
            if np.strip():
                conn = sqlite3.connect(DB_FILE)
                conn.execute("INSERT OR REPLACE INTO filo (plaka, dorse, tip, sofor_1, sofor_2, grup, durum) VALUES (?,?,?,?,?,?,?)", 
                             (np.strip(), nd.strip(), nt, s1.strip(), s2.strip(), ng.strip(), "AKTİF"))
                conn.commit(); conn.close()
                st.session_state.df_filo = load_data("filo")
                st.success(f"✅ **{np}** plakalı araç veritabanına eklendi!")
                st.rerun()
            else:
                st.warning("Lütfen plaka alanını doldurun.")

# --- MODÜL 4: VARDİYA AMİRLERİ & İK ---
elif menu == "👥 Vardiya Amirleri & İK":
    st.subheader("👥 Saha Amir Grupları & Vardiya Yönetimi")
    
    df_f = st.session_state.df_filo
    if len(df_f) > 0 and 'grup' in df_f.columns:
        gruplar = df_f['grup'].unique()
        cols = st.columns(min(len(gruplar), 4) if len(gruplar) > 0 else 1)
        for i, g in enumerate(gruplar):
            with cols[i % len(cols)]:
                 count = len(df_f[df_f['grup'] == g])
                 st.markdown(f"### 📌 {g}")
                 st.info(f"Toplu Araç Sayısı: **{count}**")
                 st.dataframe(df_f[df_f['grup'] == g][['plaka', 'sofor_1', 'durum']], hide_index=True)
    else:
        st.caption("Veritabanında grup kaydı bulunduğunda gruplar burada listelenir.")

# --- MODÜL 5: KADEME & MUAYENE ---
elif menu == "🚨 Kademe, Muayene & Lastik":
    st.subheader("🛠️ Kademe Arıza ve Bakım Takip Paneli")
    df_f = st.session_state.df_filo
    
    if len(df_f) > 0:
        kademede = df_f[df_f['durum'] == 'KADEME']
        if len(kademede) > 0:
            st.error(f"🚨 **Kademede / Arızada Olan Araç Sayısı: {len(kademede)}**")
            st.dataframe(kademede[['plaka', 'dorse', 'grup', 'sofor_1']], use_container_width=True)
        else:
            st.success("✅ Kademede veya arızada yatan araç bulunmamaktadır.")
    else:
        st.info("Kayıtlı araç bulunamadı.")

# --- MODÜL 6: FİNANS & FATURALAMA (DİNAMİK HESAPLAMA) ---
elif menu == "💼 Finans, Faturalama & Ciro":
    st.subheader("💼 Şirkete Özel Dinamik Maliyet ve Hakediş Paneli")
    
    st.markdown("#### 📐 Tesis / Fabrika Birim Fiyat ve Tonaj Tanımlama")
    with st.form("finans_formu"):
        f1, f2, f3 = st.columns(3)
        t_ad = f1.text_input("Tesis / Müşteri Adı:", placeholder="Örn: Tosyalı Demir Çelik")
        t_ton = f2.number_input("Taşınan Toplam Tonaj:", min_value=0.0, value=1000.0)
        t_fiyat = f3.number_input("Birim Fiyat (TL/Ton):", min_value=0.0, value=180.0)
        
        if st.form_submit_button("➕ Hakediş Hesabını Veritabanına Kaydet", type="primary"):
            if t_ad.strip():
                conn = sqlite3.connect(DB_FILE)
                conn.execute("INSERT INTO finans_tarife (tesis_adi, birim_fiyat, toplam_tonaj) VALUES (?,?,?)",
                             (t_ad.strip(), t_fiyat, t_ton))
                conn.commit(); conn.close()
                st.session_state.df_finans = load_data("finans_tarife")
                st.success("✅ Hakediş verisi eklendi!")
                st.rerun()

    df_fin = st.session_state.df_finans
    if len(df_fin) > 0:
        df_fin['Tahmini_Ciro_TL'] = df_fin['toplam_tonaj'] * df_fin['birim_fiyat']
        st.divider()
        st.markdown("#### 📊 Kayıtlı Hakedişler ve Tahmini Faturalar")
        st.dataframe(df_fin, use_container_width=True, hide_index=True)
        
        toplam_ciro = df_fin['Tahmini_Ciro_TL'].sum()
        st.success(f"💰 **Toplam Tahmini Kesilecek Fatura Tutarı: ₺ {toplam_ciro:,.2f}**")
        
        st.divider()
        st.markdown("📲 **Patron WhatsApp Vardiya Sonu Özeti (Canlı Üretilen Format):**")
        
        ozet_metni = f"""[ŞimşekLog Otomatik Özet - {datetime.now().strftime('%d.%m.%Y %H:%M')}]\nSayın Yönetici, vardiya hakediş özeti aşağıdadır:\n"""
        for _, r in df_fin.iterrows():
            ozet_metni += f"• {r['tesis_adi']}: {r['toplam_tonaj']} Ton (Tutar: ₺{r['Tahmini_Ciro_TL']:,.2f})\n"
        ozet_metni += f"\nTOPLAM HAKEDİŞ: ₺{toplam_ciro:,.2f}\nSistem: app.simseklog.com"
        
        st.code(ozet_metni, language="text")
    else:
        st.info("Henüz hakediş tanımı girilmedi. Yukarıdaki formdan ekleyebilirsiniz.")

# --- MODÜL 7: B2B E-TİCARET ---
elif menu == "🌐 B2B E-Ticaret & Kurye Ağı":
    st.subheader("🌐 Son Kilometre (Last-Mile) E-Ticaret Kurye Yönetimi")
    st.info("E-ticaret ve kargo dağıtımı yapan hafif ticari araç yönetimi alanı.")
