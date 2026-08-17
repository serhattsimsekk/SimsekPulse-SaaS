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
# 2. GLOBAL CSS VE EXECUTIVE DARK TEMA
# =========================================================
st.markdown("""
<style>
    /* Üst menü ve default ayarları gizle */
    .stAppHeader, #MainMenu, footer, header { display: none !important; }
    
    /* Arka plan ve genel yapı */
    .stApp { background-color: #050b14 !important; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }

    /* Sol Sidebar Tasarımı (Dark Executive) */
    [data-testid="stSidebar"] { background-color: #0a1120 !important; border-right: 1px solid #1e293b !important; }
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

    /* Metrik Kartları (Glassmorphism) */
    .metric-card {
        background: rgba(15, 23, 42, 0.7); backdrop-filter: blur(10px);
        border: 1px solid rgba(51, 65, 85, 0.5); border-radius: 10px;
        padding: 15px; text-align: center; transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-3px); border-color: #38bdf8; }
    
    /* Renk Kodları */
    .c-ozmal { color: #34d399; font-weight: bold; }
    .c-tedarik { color: #f97316; font-weight: bold; }
    .c-alert { color: #f43f5e; font-weight: bold; }
    .c-info { color: #38bdf8; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. VERİTABANI VE İLK KURULUM (SQLite)
# =========================================================
DB_FILE = "simsek_os.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    # Canlı Sevkiyat Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS sevkiyat (
            sira INTEGER PRIMARY KEY AUTOINCREMENT,
            ekinciler_liman TEXT, tosyali_liman TEXT, liman_depo TEXT,
            erw_isdemir TEXT, kademe_soforsuz TEXT
        )
    ''')
    # Öz Mal Filo & Şoför Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS filo (
            plaka TEXT PRIMARY KEY, dorse TEXT, tip TEXT,
            sofor_1 TEXT, sofor_2 TEXT, grup TEXT, durum TEXT
        )
    ''')
    
    c.execute("SELECT COUNT(*) FROM sevkiyat")
    if c.fetchone()[0] == 0:
        ornek_sevk = [
            ("31 ANM 573", "31 ANM 598", "31 AHA 468", "31 AKL 543", "31 ANM 257"),
            ("31 ANN 019", "31 AIU 808", "31 ANB 271", "31 AAG 303", "31 ANM 569"),
            ("31 ANM 150", "31 ANN 331", "31 ALT 641", "31 AJG 461", "31 ASZ 257")
        ]
        c.executemany("INSERT INTO sevkiyat (ekinciler_liman, tosyali_liman, liman_depo, erw_isdemir, kademe_soforsuz) VALUES (?,?,?,?,?)", ornek_sevk)
        
        ornek_filo = [
            ("31 AIU 820", "31 KOD 50", "Damper", "ABDİL BAYRAMBEĞ", "MEHMET KAYA", "MUHİTTİN ERGAN", "AKTİF"),
            ("31 ANK 374", "31 KNS 14", "Damper", "MEHMET BOZOK", "SERVET ÖZSOY", "MUHİTTİN ERGAN", "AKTİF"),
            ("31 ANM 257", "31 KNS 37", "Sal", "HÜSEYİN TEMİZ", "HARUN KAHLAR", "KEMAL UZUNOĞLU", "KADEME"),
            ("31 ANF 677", "31 KMN 88", "Lowbed", "HÜSEYİN F. PARLAK", "CUMALİ BUZ", "FATİH MAHMUTOĞLU", "AKTİF")
        ]
        c.executemany("INSERT INTO filo (plaka, dorse, tip, sofor_1, sofor_2, grup, durum) VALUES (?,?,?,?,?,?,?)", ornek_filo)
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

# =========================================================
# 4. SOL NAVİGASYON (SİDEBAR)
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:900; letter-spacing: 1px;">⚡ ŞimşekLog</h2>
            <span style="color: #64748B; font-size: 0.75rem; font-weight:700;">SUPPLY CHAIN OS v4.0</span>
        </div>
    """, unsafe_allow_html=True)
    
    menu = st.radio(
        "MODÜLLER",
        [
            "📊 Dashboard & Yönetici Özeti",
            "🟢 Canlı Sevkiyat Matrisi (Grid)",
            "🚍 Master Filo & Öz Mal (HR)",
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
            <span style="color: #34d399; font-size: 0.75rem; font-weight: 700;">● CLOUD SYNCED | 08:00 - 08:00</span>
        </div>
    """, unsafe_allow_html=True)

# Üst Header
st.markdown(f"""
<div class="vip-header">
    <div>
        <h3 style="margin:0; color:#38bdf8; font-weight:800;">{menu.upper()}</h3>
        <span style="color:#94a3b8; font-size:0.85rem;">ŞimşekLog Merkezi Karar Destek & Lojistik ERP Sistemi</span>
    </div>
    <div style="text-align:right;">
        <span style="color:#f8fafc; font-weight:bold; font-size:1.1rem;">{datetime.now().strftime("%d.%m.%Y")}</span><br>
        <span style="color:#34d399; font-size:0.8rem; font-weight:600;">API BAĞLANTISI AKTİF</span>
    </div>
</div>
""", unsafe_allow_html=True)

# =========================================================
# 5. MODÜLLERİN İŞLEVSELLİĞİ
# =========================================================

# ---------------------------------------------------------
# MODÜL 1: DASHBOARD
# ---------------------------------------------------------
if menu == "📊 Dashboard & Yönetici Özeti":
    st.subheader("Günün Lojistik ve Finansal Röntgeni")
    
    m1, m2, m3, m4 = st.columns(4)
    with m1: st.markdown('<div class="metric-card"><span style="color:#94a3b8;">Günlük Çekilen Tonaj</span><br><b style="color:#38bdf8; font-size:1.5rem;">4,250 Ton</b></div>', unsafe_allow_html=True)
    with m2: st.markdown('<div class="metric-card"><span style="color:#94a3b8;">Öz Mal Verimlilik %</span><br><b class="c-ozmal" style="font-size:1.5rem;">%84.5</b></div>', unsafe_allow_html=True)
    with m3: st.markdown('<div class="metric-card"><span style="color:#94a3b8;">Aktif / Yatan Araç</span><br><b style="color:#e2e8f0; font-size:1.5rem;">159 / <span class="c-alert">5</span></b></div>', unsafe_allow_html=True)
    with m4: st.markdown('<div class="metric-card"><span style="color:#94a3b8;">Est. Günlük Hakediş</span><br><b style="color:#facc15; font-size:1.5rem;">₺ 850,000</b></div>', unsafe_allow_html=True)
    
    st.divider()
    st.markdown("#### 🚨 Akıllı Uyarılar & Darboğazlar")
    st.warning("⚠️ **Tosyalı Limanı (Matilda GS):** Son 1 saatte kantar bekleme süresi ortalama 42 dakikaya çıktı! Araçları Fazlara yönlendirin.")
    st.error("🚨 **Eksik Vardiya:** 31 ANM 569 (Şoförsüz) ve 31 ANM 257 (Arızalı) bugün sahaya çıkamadı. Günlük Ziyan Maliyeti: ~₺8,500.")
    st.info("📲 **08:00 Raporu Hazır:** Vardiya sonu özet raporu patronların WhatsApp hattına gönderilmek üzere kuyrukta.")

# ---------------------------------------------------------
# MODÜL 2: CANLI SEVKİYAT MATRİSİ (MAX DÜZEY GRID)
# ---------------------------------------------------------
elif menu == "🟢 Canlı Sevkiyat Matrisi (Grid)":
    
    # Tool Bar
    t1, t2, t3, t4 = st.columns([3, 1, 1, 1])
    with t1:
        arama = st.text_input("🔍 Hızlı Plaka / Tesis Arama:", placeholder="Araç veya dorse yazın...").upper()
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
            cols_check = ['ekinciler_liman', 'tosyali_liman', 'liman_depo', 'erw_isdemir', 'kademe_soforsuz']
            st.session_state.df_sevkiyat = st.session_state.df_sevkiyat.dropna(how='all', subset=cols_check)
            st.rerun()

    # Filtreleme
    df_disp = st.session_state.df_sevkiyat.copy()
    if arama:
        mask = df_disp.apply(lambda r: r.astype(str).str.contains(arama, case=False).any(), axis=1)
        df_disp = df_disp[mask]

    st.caption("💡 *Tedarikçi araçları eklediğinizde sistem renk kodunu otomatik atar. OCR ile fiş okumak için mobil girişi kullanın.*")
    
    config = {
        "sira": st.column_config.NumberColumn("SIRA", disabled=True),
        "ekinciler_liman": st.column_config.TextColumn("EKİNCİLER (HURDA)", width="medium"),
        "tosyali_liman": st.column_config.TextColumn("TOSYALI (MATILDA/EVA)", width="medium"),
        "liman_depo": st.column_config.TextColumn("LİMAN DEPO (FAZLAR)", width="medium"),
        "erw_isdemir": st.column_config.TextColumn("ERW / İSDEMİR / OSM", width="medium"),
        "kademe_soforsuz": st.column_config.TextColumn("🚨 KADEME / ŞOFÖRSÜZ", width="medium"),
    }
    
    edited = st.data_editor(df_disp, column_config=config, num_rows="dynamic", use_container_width=True, height=450, hide_index=True)
    
    if st.button("💾 Matrisi Veritabanına Senkronize Et", type="primary"):
        if not arama:
            st.session_state.df_sevkiyat = edited
            save_data(edited, "sevkiyat")
            st.success("Bulut Senkronizasyonu Başarılı!")
            st.rerun()
        else:
            st.warning("Arama yaparken kaydetme yapılamaz.")

# ---------------------------------------------------------
# MODÜL 3: MASTER FİLO & ÖZ MAL (HR)
# ---------------------------------------------------------
elif menu == "🚍 Master Filo & Öz Mal (HR)":
    st.subheader("Öz Mal Envanteri & Çift Şoför Zimmetleri")
    st.caption("Amortismanı ve kaskosu ödenen demirbaş araçlar. **Dorse tipleri:** Damper (Sarı), Sal (Mavi), Lowbed (Kırmızı).")
    
    df_f = st.session_state.df_filo
    st.dataframe(df_f, use_container_width=True, hide_index=True, height=400)
    
    st.markdown("#### ➕ Öz Mal Garajına Yeni Araç Ekle")
    with st.form("yeni_arac"):
        c1, c2, c3, c4 = st.columns(4)
        np = c1.text_input("Çekici Plaka").upper()
        nd = c2.text_input("Dorse Plaka").upper()
        nt = c3.selectbox("Dorse Tipi", ["Damper", "Sal", "Lowbed", "Havuz", "Kılçık", "Kamyon"])
        ng = c4.selectbox("Bağlı Olduğu Amir", ["MUHİTTİN ERGAN", "BİLAL YOLDAŞ", "KEMAL UZUNOĞLU", "FATİH MAHMUTOĞLU"])
        
        if st.form_submit_button("Garaja Ekle", type="primary"):
            if np:
                conn = sqlite3.connect(DB_FILE)
                conn.execute("INSERT INTO filo (plaka, dorse, tip, grup, durum) VALUES (?,?,?,?,?)", (np, nd, nt, ng, "AKTİF"))
                conn.commit(); conn.close()
                st.session_state.df_filo = load_data("filo")
                st.rerun()

# ---------------------------------------------------------
# MODÜL 4: VARDİYA AMİRLERİ & İK
# ---------------------------------------------------------
elif menu == "👥 Vardiya Amirleri & İK":
    st.subheader("Saha Amiri Grupları ve Şoför Disiplini")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("### 🔴 Muhittin Ergan")
        st.info("Aktif Araç: 36 | Şoförsüz: 1")
    with col2:
        st.markdown("### 🔵 Bilal Yoldaş")
        st.info("Aktif Araç: 42 | Şoförsüz: 0")
    with col3:
        st.markdown("### 🟢 Kemal Uzunoğlu")
        st.info("Aktif Araç: 39 | Kademe: 2")
        
    st.divider()
    st.markdown("#### 🔄 Geçici Şoför / İzin Girişi")
    st.write("Vardiyada asıl şoför yerine direksiyona geçen yedek şoförü sisteme işleyin. Performans karnesi yedek şoföre yazılır.")
    c_p, c_s = st.columns(2)
    c_p.selectbox("İlgili Araç", ["31 AIU 820", "31 ANM 150", "31 ANK 374"])
    c_s.text_input("Yedek Şoför Adı Soyadı")
    st.button("Vardiya Şoförünü Güncelle")

# ---------------------------------------------------------
# MODÜL 5: KADEME, MUAYENE & LASTİK
# ---------------------------------------------------------
elif menu == "🚨 Kademe, Muayene & Lastik":
    st.subheader("Araç Sağlığı, Arıza Talepleri ve Lastik Yönetimi")
    
    tab1, tab2 = st.tabs(["🚨 TÜVTÜRK & Evrak Alarmları", "🛠️ Kademe Arıza Talepleri"])
    with tab1:
        st.error("🚨 **31 ANK 374** - Çekici Muayenesi **2 GÜN** geçti! Trafiğe çıkması riskli.")
        st.warning("⚠️ **31 ANM 598** - Dorse (31 KNS 14) Muayenesine son 12 gün.")
        st.info("✅ Diğer 162 aracın evrak ve sigortaları tam.")
    with tab2:
        st.write("**Açık Arıza Kayıtları:**")
        st.write("- **31 ANM 257 (Kemal Usta Grubu):** Sağ arka dingil makası kırık. (Durum: Bekliyor)")
        st.write("- **31 ANM 221 (Muhittin Usta Grubu):** Yağ bakımı ve filtre değişimi. (Durum: İşlemde)")
        st.button("Yeni Arıza / Bakım Talebi Oluştur")

# ---------------------------------------------------------
# MODÜL 6: FİNANS & CİRO
# ---------------------------------------------------------
elif menu == "💼 Finans, Faturalama & Ciro":
    st.subheader("Maliyet Kontrol, Yakıt ve Hak Ediş Merkezi")
    
    f1, f2 = st.columns(2)
    with f1:
        st.markdown("""
        **🏭 Tosyalı Demir Çelik Ağustos Ayı**
        * Toplam Hurda: 15,256 Ton
        * Birim Fiyat: 180 TL/Ton
        * **Tahmini Kesilecek Fatura: ₺ 2,746,080**
        """)
        st.button("📄 Fatura Altlığı İndir (PDF)")
    with f2:
        st.markdown("""
        **⛽ Yakıt Verimlilik Uyarıları**
        * 31 ANM 112: Ton başına 0.65L (Ortalamanın %15 üstünde! - Şoför uyarıldı)
        * 31 AIU 820: Ton başına 0.45L (Mükemmel verim - Şoför Prim: +500 TL)
        """)
        
    st.divider()
    st.write("📲 **Patron WhatsApp Vardiya Özeti (Önizleme):**")
    st.code("""
    [ŞimşekLog Otomatik Özet - 12.08.2026 08:05]
    Sayın Yönetici, gece vardiyası tamamlandı.
    Tosyalı Hurda: 1.250 Ton
    Ekinciler Kütük: 850 Ton
    Filo Verimi: %84.5
    Yatan Araç: 5 (Zarar: ~8.500 TL)
    Detaylar panele yüklenmiştir.
    """, language="markdown")

# ---------------------------------------------------------
# MODÜL 7: B2B E-TİCARET & KURYE AĞI
# ---------------------------------------------------------
elif menu == "🌐 B2B E-Ticaret & Kurye Ağı":
    st.subheader("Son Kilometre (Last-Mile) E-Ticaret Teslimatları")
    st.caption("Ağır vasıta dışındaki hafif ticari araçlar ve e-ticaret depo çıkışları.")
    
    st.success("✅ **Trendyol API** ve **Hepsiburada API** Bağlantıları Aktif.")
    st.write("**Aktif Dağıtım Rotası (Yapay Zeka Optimizasyonu):**")
    st.write("🚚 Araç: 31 ABC 123 (Panelvan) | Kurye: Ahmet Y.")
    st.write("📦 Toplam Kargo: 45 | Teslim Edilen: 12 | İade: 0")
    st.progress(12/45)
    st.button("Rota Optimizasyonunu Yeniden Çalıştır (Trafik Var)")
