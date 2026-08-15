import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

# --- BULUT VERİTABANI YOLU ---
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(DATA_DIR, 'saha_operasyon.db')

# --- SAYFA YAPILANDIRMASI ---
st.set_page_config(
    page_title="SimsekPulse Pro | Fleet & Dispatch Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 10 Saniyede Bir Otomatik Yenileme
st_autorefresh(interval=10000, key="cloud_refresh")

# --- ÖZEL VIP EXECUTIVE & EXCEL STİLİ CSS ---
st.markdown("""
    <style>
    .main { background-color: #080c14; }
    div[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 800; color: #38bdf8; }
    div[data-testid="stMetricLabel"] { font-size: 13px !important; color: #94a3b8; font-weight: 600; }
    .stDataFrame { border: 1px solid #1e293b; border-radius: 10px; }
    
    /* EXCEL MATRİS STİLLERİ */
    .excel-header-banner {
        background: #1e293b;
        color: #f8fafc;
        padding: 10px 15px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 14px;
        text-align: right;
        border-bottom: 3px solid #0284c7;
        margin-bottom: 15px;
    }
    .excel-col-box {
        background-color: #0f172a;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 8px;
        margin-bottom: 10px;
    }
    .excel-col-title {
        background-color: #1e293b;
        color: #f1f5f9;
        padding: 8px;
        font-size: 12px;
        font-weight: bold;
        text-align: center;
        border-radius: 4px;
        min-height: 48px;
        display: flex;
        align-items: center;
        justify-content: center;
        border: 1px solid #475569;
    }
    .excel-count-ozmal {
        background-color: #1e3a8a;
        color: #93c5fd;
        font-weight: bold;
        font-size: 13px;
        text-align: center;
        padding: 4px;
        margin-top: 4px;
        border-radius: 4px;
    }
    .excel-count-destek {
        background-color: #7f1d1d;
        color: #fca5a5;
        font-weight: bold;
        font-size: 13px;
        text-align: center;
        padding: 4px;
        margin-top: 2px;
        margin-bottom: 8px;
        border-radius: 4px;
    }
    .plate-pill {
        padding: 5px 8px;
        margin-bottom: 4px;
        border-radius: 4px;
        font-weight: bold;
        font-size: 12px;
        text-align: center;
        color: #ffffff;
        font-family: 'Courier New', Courier, monospace;
    }
    .pill-green { background-color: #16a34a; }
    .pill-blue { background-color: #2563eb; }
    .pill-purple { background-color: #9333ea; }
    .pill-cyan { background-color: #0891b2; }
    .pill-orange { background-color: #ea580c; }
    .pill-gray { background-color: #4b5563; }
    </style>
""", unsafe_allow_html=True)

# --- TÜM DORSE VE EKİPMAN TİPLERİ ---
DORSE_VE_EKIPMAN_TIPLERI = [
    "🏗️ Junior Dorse (Hurda)",
    "🏗️ Uzun Dorse (Hurda)",
    "🌊 Havuz Dorse",
    "🪗 Akordiyon Dorse",
    "📐 Sal Babalı Dorse",
    "📐 Sal Düz Dorse",
    "📦 20'lik Kılçık Dorse",
    "📦 40'lık Kılçık Dorse",
    "🌾 Kuru Yük Dorsesi",
    "🚪 Kapaklı Dorse",
    "🚚 Kamyon (Kırkayak / Onteker)",
    "🚜 İş Makinesi (Loder / Ekskavatör / Vinç)"
]

# --- SESSION STATE (GARAJ ENVANTERİ VE DEĞİŞİKLİKLER) ---
if 'ozmal_garaj' not in st.session_state:
    st.session_state.ozmal_garaj = []

if 'sofor_degisiklikleri' not in st.session_state:
    st.session_state.sofor_degisiklikleri = {}

if 'vardiya_amiri' not in st.session_state:
    st.session_state.vardiya_amiri = "SİNAN GÜL // MUSTAFA ÇETİN"

# --- HELPER FONKSİYONLAR ---
def operasyonel_tarih_hesapla(dt_val):
    if pd.isnull(dt_val):
        return '2026-08-14'
    try:
        dt = pd.to_datetime(dt_val)
        if dt.hour < 8:
            return (dt - timedelta(days=1)).strftime('%Y-%m-%d')
        else:
            return dt.strftime('%Y-%m-%d')
    except:
        return str(dt_val).split(' ')[0]

def sofor_bul(op_tarih, plaka):
    plk = str(plaka).replace(' ', '').upper()
    key = f"{op_tarih}_{plk}"
    
    if key in st.session_state.sofor_degisiklikleri:
        return f"🔄 {st.session_state.sofor_degisiklikleri[key]}"
    
    for item in st.session_state.ozmal_garaj:
        if item["Plaka"] == plk:
            return f"👤 {item.get('Asıl_Şoför', 'Tanımsız')}"
            
    return "🚚 Taşeron / Tanımsız Şoför"

def filo_kategorisi_bul(plaka):
    plk = str(plaka).replace(' ', '').upper()
    aktif_ozmal_plakalar = [item["Plaka"] for item in st.session_state.ozmal_garaj if item.get("Durum") == "🟢 Aktif Envanter"]
    if plk in aktif_ozmal_plakalar:
        return '🟢 Öz Mal Filo'
    else:
        return '🟣 Dış Taşeron / Tedarikçi'

def dorse_tipi_bul(plaka):
    plk = str(plaka).replace(' ', '').upper()
    for item in st.session_state.ozmal_garaj:
        if item["Plaka"] == plk:
            return item.get("Dorse_Tipi", "🚛 Standart Dorse")
    return "🚛 Standart Dorse"

def verileri_yukle():
    if not os.path.exists(DB_NAME):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM sefer_kayitlari", conn)
    conn.close()

    if not df.empty:
        if 'op_tarih' not in df.columns or df['op_tarih'].isnull().all():
            if 'yukleme_zamani' in df.columns:
                df['op_tarih'] = df['yukleme_zamani'].apply(operasyonel_tarih_hesapla)
            else:
                df['op_tarih'] = '2026-08-14'

        if 'plaka' in df.columns:
            df = df[df['plaka'].notnull() & (df['plaka'] != 'nan') & (df['plaka'] != 'None') & (df['plaka'] != '31XX000')]
            df['plaka_clean'] = df['plaka'].astype(str).str.replace(' ', '').str.upper()
            df['filo_kategorisi'] = df['plaka_clean'].apply(filo_kategorisi_bul)
            df['dorse_tipi'] = df['plaka_clean'].apply(dorse_tipi_bul)

        df['giris_dt'] = pd.to_datetime(df['yukleme_zamani'], errors='coerce')
        df['cikis_dt'] = pd.to_datetime(df['bosaltma_zamani'], errors='coerce')

        df['tur_suresi_dk'] = (df['cikis_dt'] - df['giris_dt']).dt.total_seconds() / 60.0
        df.loc[df['tur_suresi_dk'] < 0, 'tur_suresi_dk'] += 1440.0

        df = df.sort_values(by=['plaka', 'giris_dt'])
        df['onceki_cikis_dt'] = df.groupby('plaka')['cikis_dt'].shift(1)
        df['seferler_arasi_dk'] = (df['giris_dt'] - df['onceki_cikis_dt']).dt.total_seconds() / 60.0
        df.loc[df['seferler_arasi_dk'] < 0, 'seferler_arasi_dk'] = np.nan

        df['Aktif_Şoför'] = df.apply(lambda r: sofor_bul(r['op_tarih'], r['plaka_clean']), axis=1)

    return df

# --- BAŞLIK ---
st.title("⚡ SimsekPulse Pro | Fleet, Dispatch & ERP Intelligence")
st.caption("🌐 Canlı Excel Matris Sevkiyat Tablosu, Çoklu Araç Ekleme & Vardiya Yönetimi")
st.markdown("---")

df = verileri_yukle()

if df.empty:
    st.info("ℹ️ Henüz veritabanında aktif sefer kaydı bulunmuyor.")
else:
    tarihler = sorted([str(t) for t in df['op_tarih'].dropna().unique() if str(t) not in ['NaT', 'None']], reverse=True)
    secilen_tarih = st.sidebar.selectbox("📅 Çalışma Günü (08:00 - 08:00):", tarihler, key="tab_main_tarih")
    f_df = df[df['op_tarih'] == secilen_tarih]

    # SEKMELER
    tab_excel, tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📋 GÜNCEL SEVKİYAT (Excel Matris)",
        "📊 24 Saatlik Şoför Karnesi", 
        "🎨 Tedarikçi & Dorse Renk Matrisi", 
        "🏛️ Öz Mal Garaj & Toplu Ekleme", 
        "🔄 Vardiya Şoför Değişimi", 
        "💰 Finans & Hak Ediş"
    ])

    # -------------------------------------------------------------
    # TAB 0: GÜNCEL SEVKİYAT (EXCEL MATRİS SÜTÜNLARI - YENİ MODÜL!)
    # -------------------------------------------------------------
    with tab_excel:
        # VARDİYA AMİRİ BANNERI
        col_am1, col_am2 = st.columns([2, 1])
        with col_am1:
            st.markdown(f"""
                <div class="excel-header-banner">
                    📋 {secilen_tarih} VARDİYA AMİRLERİ: {st.session_state.vardiya_amiri}
                </div>
            """, unsafe_allow_html=True)
        with col_am2:
            yeni_amirlerr = st.text_input("✏️ Vardiya Amirlerini Güncelle:", st.session_state.vardiya_amiri)
            if yeni_amirlerr != st.session_state.vardiya_amiri:
                st.session_state.vardiya_amiri = yeni_amirlerr
                st.rerun()

        if not f_df.empty:
            # Tesis / Gemi Listesi
            tesisler = sorted(f_df['bosaltma_yeri'].dropna().unique().tolist())
            
            if not tesisler:
                tesisler = f_df['gemi_adi'].dropna().unique().tolist()

            # Renk Paleti Döngüsü
            renk_siniflari = ['pill-green', 'pill-blue', 'pill-cyan', 'pill-purple', 'pill-orange', 'pill-gray']

            # Streamlit Sütunları
            cols = st.columns(len(tesisler) if len(tesisler) > 0 else 1)

            for idx, tesis_adi in enumerate(tesisler):
                tesis_df = f_df[f_df['bosaltma_yeri'] == tesis_adi]
                
                plakalar = tesis_df['plaka_clean'].unique().tolist()
                
                # Öz mal ve destek sayımı
                ozmal_count = len(tesis_df[tesis_df['filo_kategorisi'] == '🟢 Öz Mal Filo']['plaka_clean'].unique())
                destek_count = len(plakalar) - ozmal_count

                with cols[idx % len(cols)]:
                    # Sütun Başlığı ve Sayım Kutuları
                    st.markdown(f"""
                        <div class="excel-col-box">
                            <div class="excel-col-title">{tesis_adi}</div>
                            <div class="excel-count-ozmal">ÖZ MAL (FİLO): {ozmal_count}</div>
                            <div class="excel-count-destek">DESTEK (DİŞ): {destek_count}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    # Plaka Listesi (Renk Bloklu)
                    for p_idx, plk in enumerate(plakalar):
                        color_cls = renk_siniflari[p_idx % len(renk_siniflari)]
                        st.markdown(f"""
                            <div class="plate-pill {color_cls}">
                                {plk}
                            </div>
                        """, unsafe_allow_html=True)

    # -------------------------------------------------------------
    # TAB 1: 24 SAATLİK ŞOFÖR KARNESİ
    # -------------------------------------------------------------
    with tab1:
        st.subheader(f"📊 {secilen_tarih} Operasyonel Günlük Araç & Şoför Karnesi")
        
        if not f_df.empty:
            karne_df = f_df.groupby(['plaka_clean', 'filo_kategorisi', 'dorse_tipi', 'Aktif_Şoför']).agg(
                Toplam_Sefer=('id', 'count'),
                Toplam_Tonaj=('net_tonaj', 'sum'),
                Ort_Tur_Suresi_Dk=('tur_suresi_dk', 'mean'),
                Ort_Bekleme_Dk=('seferler_arasi_dk', 'mean')
            ).reset_index().sort_values(by='Toplam_Tonaj', ascending=False)

            karne_df.columns = ['Plaka / Ekipman', 'Filo Aidiyeti', 'Dorse / Araç Tipi', 'Direksiyondaki Şoför / Operatör', 'Sefer Sayısı', 'Toplam Tonaj', 'Ort. Tur Süresi (Dk)', 'Ort. Bekleme (Dk)']

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📊 Günlük Toplam Tonaj", f"{f_df['net_tonaj'].sum():,.2f} Ton")
            c2.metric("🚛 Toplam Attığı Sefer", f"{len(f_df)} Sefer")
            c3.metric("🛞 Sahadaki Aktif Ekipman", f"{f_df['plaka_clean'].nunique()} Birim")
            c4.metric("👨‍✈️ Aktif Şoför / Operatör", f"{f_df['Aktif_Şoför'].nunique()} Kişi")

            st.markdown("---")
            st.dataframe(karne_df, use_container_width=True, height=350)

    # -------------------------------------------------------------
    # TAB 2: TEDARİKÇİ & DORSE RENK MATRİSİ
    # -------------------------------------------------------------
    with tab2:
        st.subheader("🎨 Tedarikçi & Dorse Tipi Görsel Dağılım Matrisi")
        
        if not f_df.empty:
            renkli_df = f_df.sort_values('giris_dt').groupby('plaka_clean').last().reset_index()
            renkli_df = renkli_df[['plaka_clean', 'filo_kategorisi', 'dorse_tipi', 'Aktif_Şoför', 'gemi_adi', 'tesis', 'bosaltma_yeri', 'net_tonaj']]
            renkli_df.columns = ['Plaka / Ekipman', 'Filo Sınıfı', '🚛 Dorse / Araç Tipi', 'Görevli Şoför', 'Aktif Gemi', 'Yükleme Tesis', 'Boşaltma Yeri', 'Son Tonaj']

            st.dataframe(renkli_df, use_container_width=True, height=350)

    # -------------------------------------------------------------
    # TAB 3: ÖZ MAL GARAJ & TOPLU EKLEME
    # -------------------------------------------------------------
    with tab3:
        st.subheader("🏛️ Öz Mal Garaj Envanteri & Toplu Araç/Ekipman Ekleme")
        
        garaj_df = pd.DataFrame(st.session_state.ozmal_garaj) if st.session_state.ozmal_garaj else pd.DataFrame(columns=["Plaka", "Asıl_Şoför", "Dorse_Tipi", "Araç_Tipi", "Durum"])
        toplam_ozmal = len(garaj_df[garaj_df['Durum'] == '🟢 Aktif Envanter']) if not garaj_df.empty else 0
        
        c_m1, c_m2 = st.columns(2)
        c_m1.metric("🏛️ Garajdaki Toplam Öz Mal Ekipman", f"{toplam_ozmal} Birim")
        
        st.markdown("---")
        
        col_g1, col_g2 = st.columns([1, 1])

        with col_g1:
            st.write("📋 **Garajdaki Mevcut Öz Mal Listesi:**")
            st.dataframe(garaj_df, use_container_width=True, height=320)

        with col_g2:
            st.write("📋 **Toplu Araç / Ekipman Ekleme:**")
            with st.form("toplu_arac_formu"):
                toplu_plakalar = st.text_area("Plakaları Alt Alta Yazın:", height=120)
                secilen_dorse = st.selectbox("Dorse / Ekipman Tipi:", DORSE_VE_EKIPMAN_TIPLERI)
                secilen_arac_tipi = st.selectbox("Araç Tipi:", ["🚛 Çekici / Tır", "🚚 Kamyon (Kırkayak/Onteker)", "🚜 İş Makinesi"])
                varsayilan_sofor = st.text_input("Ortak / Varsayılan Şoför-Operatör:", "Tanımsız")
                
                toplu_btn = st.form_submit_button("➕ Toplu Olarak Garaja Ekle")
                
                if toplu_btn and toplu_plakalar.strip():
                    plaka_listesi = [p.strip().upper() for p in toplu_plakalar.split('\n') if p.strip()]
                    eklenen_sayi = 0
                    for plk in plaka_listesi:
                        if not any(item['Plaka'] == plk for item in st.session_state.ozmal_garaj):
                            st.session_state.ozmal_garaj.append({
                                "Plaka": plk,
                                "Asıl_Şoför": varsayilan_sofor,
                                "Dorse_Tipi": secilen_dorse,
                                "Araç_Tipi": secilen_arac_tipi,
                                "Durum": "🟢 Aktif Envanter"
                            })
                            eklenen_sayi += 1
                    st.success(f"✅ Toplam {eklenen_sayi} adet araç/ekipman Öz Mal garajına eklendi!")
                    st.rerun()

    # -------------------------------------------------------------
    # TAB 4: VARDİYA ŞOFÖR DEĞİŞİMİ
    # -------------------------------------------------------------
    with tab4:
        st.subheader("🔄 Günlük Vardiya Şoför / Operatör Değişim Formu")
        
        col_d1, col_d2 = st.columns([1, 1])
        with col_d1:
            with st.form("sofor_degisim_formu"):
                tarih_degisim = st.selectbox("📅 İşlem Yapılacak Tarih:", tarihler)
                aktif_plakalar = f_df['plaka_clean'].unique().tolist()
                
                secilen_plaka = st.selectbox("🚛 Araç / Ekipman Seçin:", aktif_plakalar)
                yeni_sofor_adi = st.text_input("👨‍✈️ O Günkü Şoför / Operatör:", "Ahmet Yılmaz (Yedek)")
                sebep = st.selectbox("📌 Sebep:", ["İzinli Asıl Şoför", "Hastalık / Rapor", "Çift Vardiya Değişimi", "Geçici Görev"])

                degistir_btn = st.form_submit_button("💾 Şoför / Operatör Kaydını Güncelle")
                if degistir_btn:
                    key = f"{tarih_degisim}_{secilen_plaka}"
                    st.session_state.sofor_degisiklikleri[key] = f"{yeni_sofor_adi} [{sebep}]"
                    st.success(f"✅ {secilen_plaka} için {tarih_degisim} tarihinde personel '{yeni_sofor_adi}' olarak güncellendi!")
                    st.rerun()

        with col_d2:
            st.write("📋 **Oluşturulan Geçici Değişim Kayıtları:**")
            if st.session_state.sofor_degisiklikleri:
                degisim_list = []
                for k, v in st.session_state.sofor_degisiklikleri.items():
                    t, p = k.split('_')
                    degisim_list.append({"Tarih": t, "Plaka": p, "Geçici Şoför/Operatör": v})
                st.dataframe(pd.DataFrame(degisim_list), use_container_width=True, height=280)

    # -------------------------------------------------------------
    # TAB 5: FİNANS VE HAK EDİŞ
    # -------------------------------------------------------------
    with tab5:
        st.subheader("💰 Finansal Ciro & Mazot Kayıp Hesaplayıcı")
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            birim_fiyat = st.number_input("💵 Birim Taşıma Fiyatı (TL / Ton):", value=180.0, step=10.0)
            mazot_fiyati = st.number_input("⛽ Mazot Litre Fiyatı (TL):", value=45.0, step=1.0)

        toplam_ton = f_df['net_tonaj'].sum()
        toplam_ciro = toplam_ton * birim_fiyat

        toplam_kayip_saat = f_df['seferler_arasi_dk'].sum() / 60.0
        tahmini_yakit_kaybi_litre = toplam_kayip_saat * 3.5
        tahmini_yakit_maliyeti = tahmini_yakit_kaybi_litre * mazot_fiyati

        st.markdown("---")
        m1, m2, m3 = st.columns(3)
        m1.metric("💵 Toplam Brüt Hak Ediş", f"{toplam_ciro:,.2f} TL")
        m2.metric("⛽ Bekleme Kaynaklı Yakıt İsrafı", f"{tahmini_yakit_kaybi_litre:,.1f} Litre")
        m3.metric("🔥 Boşa Giden Mazot Maliyeti", f"{tahmini_yakit_maliyeti:,.2f} TL", delta=f"-{tahmini_yakit_maliyeti:,.0f} TL", delta_color="inverse")
