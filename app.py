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
    page_title="SimsekPulse SaaS | Ultimate Fleet & Driver Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 10 Saniyede Bir Otomatik Yenileme
st_autorefresh(interval=10000, key="cloud_refresh")

# --- ÖZEL EXECUTIVE DARK THEME & RENKLENDİRME CSS ---
st.markdown("""
    <style>
    .main { background-color: #080c14; }
    div[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 800; color: #38bdf8; }
    div[data-testid="stMetricLabel"] { font-size: 13px !important; color: #94a3b8; font-weight: 600; }
    .stDataFrame { border: 1px solid #1e293b; border-radius: 10px; }
    .status-card {
        background: #0f172a;
        border-left: 5px solid #38bdf8;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# --- SESSION STATE İLE DİNAMİK ÖZ MAL GARAJ ENVANTERİ ---
if 'ozmal_garaj' not in st.session_state:
    st.session_state.ozmal_garaj = [
        {"Plaka": "31AOV941", "Asıl_Şoför": "Ahmet Yılmaz", "Dorse": "🏗️ Damper Dorse (Hurda/Dökme)", "Durum": "🟢 Aktif Envanter"},
        {"Plaka": "31ANK278", "Asıl_Şoför": "Mehmet Kaya", "Dorse": "📐 Kapaklı/Sal Dorse (Kütük/Sac)", "Durum": "🟢 Aktif Envanter"},
        {"Plaka": "31K3200",  "Asıl_Şoför": "Mustafa Demir", "Dorse": "🏗️ Damper Dorse (Hurda/Dökme)", "Durum": "🟢 Aktif Envanter"},
        {"Plaka": "31P888",   "Asıl_Şoför": "Hasan Şahin", "Dorse": "🚜 Lowbed/Platform (Ağır Yük)", "Durum": "🟢 Aktif Envanter"},
        {"Plaka": "31AGH102", "Asıl_Şoför": "Ali Öztürk", "Dorse": "📦 Konteyner Şasi", "Durum": "🟢 Aktif Envanter"}
    ]

# --- TEDARİKÇİ & SPOT ARAÇ BİLİŞİM HARİTASI ---
TEDARIKCI_DORSE_HARITASI = {
    "31K8900": {"Filo": "🟧 Sözleşmeli Tedarikçi (Öz-İş)", "Dorse": "🏗️ Damper Dorse (Hurda/Dökme)"},
    "31K7100": {"Filo": "🟧 Sözleşmeli Tedarikçi (Öz-İş)", "Dorse": "📐 Kapaklı/Sal Dorse (Kütük/Sac)"},
    "31P900":  {"Filo": "🟣 Spot Taşeron", "Dorse": "🏗️ Damper Dorse (Hurda/Dökme)"},
    "31AG110": {"Filo": "🟣 Spot Taşeron", "Dorse": "📐 Kapaklı/Sal Dorse (Kütük/Sac)"},
    "31K5500": {"Filo": "🟣 Spot Taşeron", "Dorse": "📦 Konteyner Şasi"}
}

# --- GÜNLÜK YEDEK / GEÇİCİ ŞOFÖR DEĞİŞİKLİK DİZİNİ ---
if 'sofor_degisiklikleri' not in st.session_state:
    st.session_state.sofor_degisiklikleri = {}

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
    
    # 1. Geçici / Yedek Şoför Bindi mi?
    if key in st.session_state.sofor_degisiklikleri:
        return f"🔄 {st.session_state.sofor_degisiklikleri[key]}"
    
    # 2. Sabit Asıl Şoför Kim?
    for item in st.session_state.ozmal_garaj:
        if item["Plaka"] == plk:
            return f"👤 {item['Asıl_Şoför']}"
            
    return "🚚 Taşeron / Tanımsız Şoför"

def filo_kategorisi_bul(plaka):
    plk = str(plaka).replace(' ', '').upper()
    aktif_ozmal_plakalar = [item["Plaka"] for item in st.session_state.ozmal_garaj if item["Durum"] == "🟢 Aktif Envanter"]
    if plk in aktif_ozmal_plakalar:
        return '🟢 Öz Mal Filo'
    elif plk in TEDARIKCI_DORSE_HARITASI:
        return TEDARIKCI_DORSE_HARITASI[plk]["Filo"]
    else:
        return '⚪ Diğer Taşeron'

def dorse_tipi_bul(plaka):
    plk = str(plaka).replace(' ', '').upper()
    for item in st.session_state.ozmal_garaj:
        if item["Plaka"] == plk:
            return item["Dorse"]
    if plk in TEDARIKCI_DORSE_HARITASI:
        return TEDARIKCI_DORSE_HARITASI[plk]["Dorse"]
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

        # ŞOFÖR BİLGİSİ
        df['Aktif_Şoför'] = df.apply(lambda r: sofor_bul(r['op_tarih'], r['plaka_clean']), axis=1)

    return df

# --- BAŞLIK ALANI ---
st.title("⚡ SimsekPulse Pro | Ultimate Fleet, Driver & ERP Intelligence")
st.caption("🌐 24 Saatlik Otomatik Karne, Renk Kodlu Tedarikçi/Dorse Matrisi & Öz Mal Garaj ERP")
st.markdown("---")

df = verileri_yukle()

if df.empty:
    st.info("ℹ️ Henüz veritabanında aktif sefer kaydı bulunmuyor.")
else:
    tarihler = sorted([str(t) for t in df['op_tarih'].dropna().unique() if str(t) not in ['NaT', 'None']], reverse=True)
    secilen_tarih = st.sidebar.selectbox("📅 Çalışma Günü (08:00 - 08:00):", tarihler, key="tab_main_tarih")
    f_df = df[df['op_tarih'] == secilen_tarih]

    # SEKMELER
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 24 Saatlik Şoför Karnesi", 
        "🎨 Tedarikçi & Dorse Renk Matrisi", 
        "🔄 Vardiya Şoför Değişimi", 
        "🏛️ Öz Mal Garaj & Demirbaş ERP", 
        "💰 Finans & Hak Ediş"
    ])

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

            karne_df.columns = ['Plaka', 'Filo Aidiyeti', 'Dorse Tipi', 'Direksiyondaki Şoför', 'Sefer Sayısı', 'Toplam Tonaj', 'Ort. Tur Süresi (Dk)', 'Ort. Bekleme (Dk)']

            # KPI KARTLARI
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("📊 Günlük Toplam Tonaj", f"{f_df['net_tonaj'].sum():,.2f} Ton")
            c2.metric("🚛 Toplam Attığı Sefer", f"{len(f_df)} Sefer")
            c3.metric("🛞 Sahadaki Aktif Tır", f"{f_df['plaka_clean'].nunique()} Tır")
            c4.metric("👨‍✈️ Aktif Şoför Sayısı", f"{f_df['Aktif_Şoför'].nunique()} Kişi")

            st.markdown("---")
            st.dataframe(karne_df, use_container_width=True, height=350)

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                fig_sofor = px.bar(karne_df, x='Direksiyondaki Şoför', y='Toplam Tonaj', color='Filo Aidiyeti', text_auto='.1f', title="Şoför Bazlı Toplam Taşınan Tonaj")
                fig_sofor.update_layout(template="plotly_dark", height=320)
                st.plotly_chart(fig_sofor, use_container_width=True)

            with col_p2:
                fig_sure = px.bar(karne_df, x='Direksiyondaki Şoför', y='Ort. Tur Süresi (Dk)', color='Ort. Tur Süresi (Dk)', color_continuous_scale='Reds', title="Şoför Bazlı Ortalama Tur Süresi")
                fig_sure.update_layout(template="plotly_dark", height=320)
                st.plotly_chart(fig_sure, use_container_width=True)

    # -------------------------------------------------------------
    # TAB 2: TEDARİKÇİ & DORSE RENK MATRİSİ
    # -------------------------------------------------------------
    with tab2:
        st.subheader("🎨 Çift Katmanlı Renk Matrisi: Tedarikçi & Dorse Tipi Dağılımı")
        
        if not f_df.empty:
            renkli_df = f_df.sort_values('giris_dt').groupby('plaka_clean').last().reset_index()
            renkli_df = renkli_df[['plaka_clean', 'filo_kategorisi', 'dorse_tipi', 'Aktif_Şoför', 'gemi_adi', 'tesis', 'bosaltma_yeri', 'net_tonaj']]
            renkli_df.columns = ['Plaka', 'Filo Sınıfı', '🚛 Dorse Tipi', 'Görevli Şoför', 'Aktif Gemi', 'Yükleme Tesis', 'Boşaltma Yeri', 'Son Tonaj']

            st.dataframe(renkli_df, use_container_width=True, height=350)

            col_r1, col_r2 = st.columns(2)
            with col_r1:
                fig_ted = px.pie(f_df, names='filo_kategorisi', values='net_tonaj', hole=0.4, title="Filo Aidiyeti Tonaj Payı",
                                 color_discrete_map={'🟢 Öz Mal Filo': '#10b981', '🟧 Sözleşmeli Tedarikçi (Öz-İş)': '#f59e0b', '🟣 Spot Taşeron': '#8b5cf6'})
                fig_ted.update_layout(template="plotly_dark", height=300)
                st.plotly_chart(fig_ted, use_container_width=True)

            with col_r2:
                fig_dor = px.pie(f_df, names='dorse_tipi', values='net_tonaj', hole=0.4, title="Dorse Tipleri Tonaj Payı",
                                 color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_dor.update_layout(template="plotly_dark", height=300)
                st.plotly_chart(fig_dor, use_container_width=True)

    # -------------------------------------------------------------
    # TAB 3: VARDİYA ŞOFÖR DEĞİŞİMİ
    # -------------------------------------------------------------
    with tab3:
        st.subheader("🔄 Günlük Vardiya Şoför Değişim Formu (Geçici / Yedek Şoför)")
        
        col_d1, col_d2 = st.columns([1, 1])
        with col_d1:
            with st.form("sofor_degisim_formu"):
                tarih_degisim = st.selectbox("📅 İşlem Yapılacak Tarih:", tarihler)
                aktif_plakalar = [item["Plaka"] for item in st.session_state.ozmal_garaj if item["Durum"] == "🟢 Aktif Envanter"]
                secilen_plaka = st.selectbox("🚛 Araç Seçin:", aktif_plakalar)
                yeni_sofor_adi = st.text_input("👨‍✈️ Direksiyona Geçen Şoför:", "Kemal Yıldız (Yedek)")
                sebep = st.selectbox("📌 Sebep:", ["İzinli Asıl Şoför", "Hastalık / Rapor", "Çift Vardiya Değişimi", "Geçici Görev"])

                degistir_btn = st.form_submit_button("💾 Günlük Şoför Değişikliğini Kaydet")
                if degistir_btn:
                    key = f"{tarih_degisim}_{secilen_plaka}"
                    st.session_state.sofor_degisiklikleri[key] = f"{yeni_sofor_adi} [{sebep}]"
                    st.success(f"✅ {secilen_plaka} için {tarih_degisim} tarihinde şoför '{yeni_sofor_adi}' olarak güncellendi!")
                    st.rerun()

        with col_d2:
            st.write("📋 **Oluşturulan Geçici Şoför Kayıtları:**")
            if st.session_state.sofor_degisiklikleri:
                degisim_list = []
                for k, v in st.session_state.sofor_degisiklikleri.items():
                    t, p = k.split('_')
                    degisim_list.append({"Tarih": t, "Plaka": p, "Geçici Şoför": v})
                st.dataframe(pd.DataFrame(degisim_list), use_container_width=True, height=280)

    # -------------------------------------------------------------
    # TAB 4: ÖZ MAL GARAJ & DEMİRBAŞ ERP
    # -------------------------------------------------------------
    with tab4:
        st.subheader("🏛️ Şirket Öz Mal Garaj Envanteri (Ekle / Sat)")
        
        garaj_df = pd.DataFrame(st.session_state.ozmal_garaj)
        toplam_ozmal_sayisi = len(garaj_df[garaj_df['Durum'] == '🟢 Aktif Envanter'])
        aktif_ozmal_sahada = f_df[f_df['filo_kategorisi'] == '🟢 Öz Mal Filo']['plaka_clean'].nunique()
        verimlilik_yuzdesi = (aktif_ozmal_sahada / toplam_ozmal_sayisi) * 100.0 if toplam_ozmal_sayisi > 0 else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("🏛️ Garajdaki Öz Mal Tır", f"{toplam_ozmal_sayisi} Araç")
        m2.metric("🟢 Sahada Çalışan Öz Mal", f"{aktif_ozmal_sahada} Araç")
        m3.metric("⚡ SAF ÖZ MAL VERİMİ", f"%{verimlilik_yuzdesi:.1f}")

        st.markdown("---")
        col_g1, col_g2 = st.columns([2, 1])
        with col_g1:
            st.write("📋 **Öz Mal Envanter & Sabit Şoför Zimmet Listesi:**")
            st.dataframe(garaj_df, use_container_width=True, height=280)

        with col_g2:
            with st.form("yeni_arac_form"):
                y_plk = st.text_input("Ruhsat Plakası:", "31K9000").upper()
                y_sofor = st.text_input("Zimmetli Asıl Şoför:", "Osman Can")
                y_dorse = st.selectbox("Dorse Tipi:", ["🏗️ Damper Dorse", "📐 Kapaklı/Sal Dorse", "🚜 Lowbed/Platform", "📦 Konteyner Şasi"])
                ekle_btn = st.form_submit_button("💾 Filoya Kat (Garaja Ekle)")
                if ekle_btn:
                    st.session_state.ozmal_garaj.append({"Plaka": y_plk, "Asıl_Şoför": y_sofor, "Dorse": y_dorse, "Durum": "🟢 Aktif Envanter"})
                    st.success(f"✅ {y_plk} Öz Mal envanterine eklendi!")
                    st.rerun()

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
