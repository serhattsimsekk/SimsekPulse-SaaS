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
    page_title="Şimşek Lojistik | Canlı Saha E-Tablosu",
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
# 2. GLOBAL CSS (SABİT / AÇILIR SOL MENÜ VE TEMA)
# =========================================================
st.markdown("""
<style>
    /* Sadece footer ve marka izlerini gizle, sidebar toggle butonunu SERBEST BIRAK */
    #MainMenu, footer { visibility: hidden !important; }
    
    .stApp { background-color: #050b14 !important; color: #f8fafc; font-family: 'Segoe UI', sans-serif; }
    .block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }

    /* YAN MENÜ STİLLERİ */
    [data-testid="stSidebar"] {
        background-color: #0a1120 !important;
        border-right: 1px solid #1e293b !important;
    }

    /* HEADER BANNER */
    .excel-main-title {
        background: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 10px 20px;
        color: #38bdf8;
        font-weight: 800;
        font-size: 1.1rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }

    .counter-bar {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 6px;
        padding: 8px;
        text-align: center;
        font-size: 0.85rem;
    }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. VERİTABANI VE GEÇMİŞ (UNDO / REDO) MİMARİSİ
# =========================================================
DB_FILE = "simsek_os.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS excel_matris (
            sira INTEGER PRIMARY KEY AUTOINCREMENT,
            col_1 TEXT, col_2 TEXT, col_3 TEXT,
            col_4 TEXT, col_5 TEXT, col_6 TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS matris_basliklar (
            kod TEXT PRIMARY KEY, baslik_adi TEXT
        )
    ''')
    
    # Varsayılan Başlıklar
    c.execute("SELECT COUNT(*) FROM matris_basliklar")
    if c.fetchone()[0] == 0:
        basliklar = [
            ("col_1", "MMK - HAT 1 (ÖZEL)"),
            ("col_2", "MMK - HAT 2 (GENEL)"),
            ("col_3", "SAHA A (EYAP)"),
            ("col_4", "SAHA B (GÜUB)"),
            ("col_5", "SAHA C (İSKEN)"),
            ("col_6", "SAHA D (TOSYALI)")
        ]
        c.executemany("INSERT INTO matris_basliklar (kod, baslik_adi) VALUES (?,?)", basliklar)

    # Varsayılan Veri
    c.execute("SELECT COUNT(*) FROM excel_matris")
    if c.fetchone()[0] == 0:
        ornek = [
            ("31 ANM 573", "31 ANM 593", "31 ANK 374", "31 AAG 291", "31 ANM 598", "31 ANN 331"),
            ("31 ANN 019", "31 ANN 168", "31 ANL 936", "31 AKL 553", "31 AIU 808", "31 AOK 866"),
            ("31 ANM 150", "31 ANN 304", "31 ANM 576", "31 AKL 554", "31 AIU 869", "31 AKL 556"),
            ("31 AOB 800", "31 ANN 312", "31 ANN 284", "31 AKL 852", "31 ANK 278", "31 ANM 210"),
            ("31 AIU 820", "31 ANV 235", "31 ANR 925", "31 AKL 862", "31 ANM 584", "31 AIY 548")
        ]
        c.executemany("INSERT INTO excel_matris (col_1, col_2, col_3, col_4, col_5, col_6) VALUES (?,?,?,?,?,?)", ornek)
    
    conn.commit()
    conn.close()

init_db()

def load_data():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM excel_matris", conn)
    conn.close()
    return df

def save_data(df):
    conn = sqlite3.connect(DB_FILE)
    df.to_sql("excel_matris", conn, if_exists="replace", index=False)
    conn.commit()
    conn.close()

def get_basliklar():
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM matris_basliklar", conn)
    conn.close()
    return dict(zip(df['kod'], df['baslik_adi']))

if "df_matris" not in st.session_state:
    st.session_state.df_matris = load_data()

# 10 Adımlık Undo (Geri Al) Hafızası
if "history" not in st.session_state:
    st.session_state.history = [st.session_state.df_matris.copy()]

# =========================================================
# 4. SOL NAVİGASYON (AÇILIR / KAPANIR SIDEBAR)
# =========================================================
with st.sidebar:
    st.markdown("""
        <div style="text-align: center; margin-bottom: 15px;">
            <h2 style="color: #38bdf8; margin:0; font-weight:900;">⚡ ŞimşekLog</h2>
            <span style="color: #64748B; font-size: 0.75rem;">CANLI LOJİSTİK MATRİSİ</span>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    kullanici_rolu = st.selectbox(
        "👤 Kullanıcı Rolü:",
        ["👑 Patron (Yönetici)", "💼 Muhasebe Departmanı", "🚚 Sevkiyatçı / Vardiya Amiri"],
        index=0
    )
    st.markdown("---")
    
    menu = st.radio("SAYFALAR", ["🟢 GÜNCEL SEVKİYAT MATRİSİ", "📊 Genel İstatistikler", "⚙️ Sütun & Sistem Ayarları"])

# =========================================================
# 5. DİNAMİK E-TABLO MODÜLÜ
# =========================================================
if menu == "🟢 GÜNCEL SEVKİYAT MATRİSİ":
    
    baslik_dict = get_basliklar()
    bugun_str = datetime.now().strftime("%d.%m.%Y")
    
    st.markdown(f"""
    <div class="excel-main-title">
        <span>⚡ CANLI SEVKİYAT E-TABLOSU ({bugun_str})</span>
        <span style="color:#34d399; font-size:0.85rem;">● OTOMATİK VERİTABANI SENKRONİZASYONU</span>
    </div>
    """, unsafe_allow_html=True)

    # DİNAMİK BAŞLIK DÜZENLEME PANELİ
    with st.expander("✏️ Sütun Başlıklarının Adını Değiştir (Excel Kolon İsimleri)"):
        with st.form("baslik_degistir_formu"):
            c1, c2, c3, c4, c5, c6 = st.columns(6)
            b1 = c1.text_input("1. Sütun", value=baslik_dict.get("col_1", ""))
            b2 = c2.text_input("2. Sütun", value=baslik_dict.get("col_2", ""))
            b3 = c3.text_input("3. Sütun", value=baslik_dict.get("col_3", ""))
            b4 = c4.text_input("4. Sütun", value=baslik_dict.get("col_4", ""))
            b5 = c5.text_input("5. Sütun", value=baslik_dict.get("col_5", ""))
            b6 = c6.text_input("6. Sütun", value=baslik_dict.get("col_6", ""))
            
            if st.form_submit_button("💾 Sütun İsimlerini Kaydet", type="primary", use_container_width=True):
                conn = sqlite3.connect(DB_FILE)
                c = conn.cursor()
                updates = [("col_1", b1), ("col_2", b2), ("col_3", b3), ("col_4", b4), ("col_5", b5), ("col_6", b6)]
                for k, v in updates:
                    c.execute("UPDATE matris_basliklar SET baslik_adi = ? WHERE kod = ?", (v, k))
                conn.commit(); conn.close()
                st.success("✅ Sütun başlıkları başarıyla değiştirildi!")
                st.rerun()

    # ANLIK SAYAÇ KARTLARI
    df_m = st.session_state.df_matris
    cols = ["col_1", "col_2", "col_3", "col_4", "col_5", "col_6"]
    
    st.markdown("##### 📊 Sütun Bazlı Araç Sayıları")
    sc = st.columns(6)
    for i, col_k in enumerate(cols):
        count = df_m[col_k].replace('', None).dropna().count() if col_k in df_m.columns else 0
        b_name = baslik_dict.get(col_k, col_k)
        sc[i].markdown(f"""
        <div class="counter-bar">
            <span style="color:#94a3b8; font-size:0.7rem;">{b_name[:18]}</span><br>
            <b style="color:#38bdf8; font-size:1.1rem;">{count} Araç</b>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # E-TABLO ARAÇ ÇUBUĞU
    tb1, tb2, tb3, tb4, tb5 = st.columns([2.5, 1, 1, 1, 1])
    with tb1:
        arama = st.text_input("🔍 Plaka Arama:", placeholder="Örn: 31 ANM...").upper()
    with tb2:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("↩️ Geri Al (Undo)", use_container_width=True):
            if len(st.session_state.history) > 1:
                st.session_state.history.pop()
                st.session_state.df_matris = st.session_state.history[-1].copy()
                st.toast("↩️ Son işlem geri alındı!")
                st.rerun()
            else:
                st.toast("⚠️ Geri alınacak işlem geçmişi yok.")
    with tb3:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        csv = df_m.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Excel İndir", csv, "Canli_Matris.csv", "text/csv", use_container_width=True)
    with tb4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ 5 Satır Ekle", use_container_width=True):
            boslar = pd.DataFrame([{"sira": None, "col_1": "", "col_2": "", "col_3": "", "col_4": "", "col_5": "", "col_6": ""} for _ in range(5)])
            st.session_state.df_matris = pd.concat([st.session_state.df_matris, boslar], ignore_index=True)
            st.session_state.history.append(st.session_state.df_matris.copy())
            st.rerun()
    with tb5:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("🧹 Boşları Temizle", use_container_width=True):
            st.session_state.df_matris = df_m.dropna(how='all', subset=cols)
            st.session_state.history.append(st.session_state.df_matris.copy())
            save_data(st.session_state.df_matris)
            st.rerun()

    # DİNAMİK BAŞLIK BİNDİRME
    config = {
        "sira": st.column_config.NumberColumn("SIRA", disabled=True),
        "col_1": st.column_config.TextColumn(baslik_dict.get("col_1", "1. SÜTUN"), width="medium"),
        "col_2": st.column_config.TextColumn(baslik_dict.get("col_2", "2. SÜTUN"), width="medium"),
        "col_3": st.column_config.TextColumn(baslik_dict.get("col_3", "3. SÜTUN"), width="medium"),
        "col_4": st.column_config.TextColumn(baslik_dict.get("col_4", "4. SÜTUN"), width="medium"),
        "col_5": st.column_config.TextColumn(baslik_dict.get("col_5", "5. SÜTUN"), width="medium"),
        "col_6": st.column_config.TextColumn(baslik_dict.get("col_6", "6. SÜTUN"), width="medium"),
    }

    df_display = st.session_state.df_matris.copy()
    if arama:
        mask = df_display.apply(lambda r: r.astype(str).str.contains(arama, case=False).any(), axis=1)
        df_display = df_display[mask]

    edited = st.data_editor(
        df_display,
        column_config=config,
        num_rows="dynamic",
        use_container_width=True,
        height=480,
        hide_index=True
    )

    # Değişiklik Kontrolü & Geçmişe Ekleme
    if not edited.equals(st.session_state.df_matris) and not arama:
        st.session_state.df_matris = edited
        st.session_state.history.append(edited.copy())
        if len(st.session_state.history) > 10:
            st.session_state.history.pop(0)

    if st.button("💾 Değişiklikleri Veritabanına Kaydet", type="primary", use_container_width=True):
        if not arama:
            save_data(edited)
            st.success("✅ Veritabanı başarıyla senkronize edildi!")
            st.rerun()
        else:
            st.warning("Arama yaparken kaydetme yapılamaz. Lütfen önce arama kutusunu temizleyin.")

elif menu == "📊 Genel İstatistikler":
    st.subheader("📊 Toplam Matris İstatistikleri")
    st.write(f"Toplam Aktif Kayıt Satırı: **{len(st.session_state.df_matris)}**")

elif menu == "⚙️ Sütun & Sistem Ayarları":
    st.subheader("⚙️ Veritabanı Ayarları")
    if st.button("🚨 Matrisi Sıfırla"):
        os.remove(DB_FILE)
        init_db()
        st.session_state.df_matris = load_data()
        st.success("Sistem sıfırlandı!")
        st.rerun()
