import os
import sqlite3
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import streamlit as st
import plotly.express as px
from streamlit_autorefresh import st_autorefresh

DATA_DIR = r'C:\LOJISTIK_SISTEMI'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)
DATA_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(DATA_DIR, 'saha_operasyon.db')

st.set_page_config(
    page_title="SahaLojistik Pro | Canlı Operasyon Yönetimi",
    page_icon="🚛",
    layout="wide"
)

st_autorefresh(interval=10000, key="cloud_refresh")

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sefer_kayitlari (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            op_tarih TEXT,
            gemi_adi TEXT,
            tesis TEXT,
            bosaltma_yeri TEXT,
            plaka TEXT,
            malzeme_tipi TEXT,
            yukleme_zamani DATETIME,
            bosaltma_zamani DATETIME,
            net_tonaj REAL,
            vardiya TEXT,
            kaynak TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

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
        
        df = df[df['op_tarih'].notnull() & (df['op_tarih'] != 'NaT') & (df['op_tarih'] != 'None')]

        if 'vardiya' in df.columns:
            df['vardiya'] = df['vardiya'].apply(lambda v: f"{int(float(v))}. Vardiya" if pd.notnull(v) and str(v).replace('.','').isdigit() else str(v))

        df['giris_dt'] = pd.to_datetime(df['yukleme_zamani'], errors='coerce')
        df['cikis_dt'] = pd.to_datetime(df['bosaltma_zamani'], errors='coerce')

        df['tur_suresi_dk'] = (df['cikis_dt'] - df['giris_dt']).dt.total_seconds() / 60.0
        df.loc[df['tur_suresi_dk'] < 0, 'tur_suresi_dk'] += 1440.0

        df = df.sort_values(by=['plaka', 'giris_dt'])
        df['onceki_cikis_dt'] = df.groupby('plaka')['cikis_dt'].shift(1)
        df['seferler_arasi_dk'] = (df['giris_dt'] - df['onceki_cikis_dt']).dt.total_seconds() / 60.0
        df.loc[df['seferler_arasi_dk'] < 0, 'seferler_arasi_dk'] = np.nan
        df.loc[df['seferler_arasi_dk'] > 720, 'seferler_arasi_dk'] = np.nan

    return df

st.title("🚢 SahaLojistik Pro | Canlı Saha & Kantar Takip Platformu")
st.caption("⚡ Bulut Tabanlı B2B SaaS Yönetim Paneli")
st.markdown("---")

df = verileri_yukle()

if df.empty:
    st.info("ℹ️ Henüz veritabanında sefer kaydı bulunmuyor.")
else:
    st.sidebar.title("🎛️ SAHA VE FİLO FİLTRELERİ")
    
    tarihler = sorted([str(t) for t in df['op_tarih'].dropna().unique() if str(t) not in ['NaT', 'None']], reverse=True)
    secilen_tarih = st.sidebar.selectbox("📅 Çalışma Günü (08:00 - 08:00):", tarihler)

    v_options = ["TÜM VARDİYALAR (24 SAAT)"] + sorted(list(df['vardiya'].dropna().unique()))
    secilen_vardiya = st.sidebar.selectbox("⏱️ Vardiya Seçin:", v_options)

    g_options = ["TÜM GEMİLER"] + sorted(list(df['gemi_adi'].dropna().unique()))
    secilen_gemi = st.sidebar.selectbox("🚢 Gemi Seçin:", g_options)

    f_df = df[df['op_tarih'] == secilen_tarih]
    if secilen_vardiya != "TÜM VARDİYALAR (24 SAAT)":
        f_df = f_df[f_df['vardiya'] == secilen_vardiya]
    if secilen_gemi != "TÜM GEMİLER":
        f_df = f_df[f_df['gemi_adi'] == secilen_gemi]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📊 Toplam Tonaj", f"{f_df['net_tonaj'].sum():,.2f} Ton")
    c2.metric("🚛 Toplam Sefer", f"{len(f_df)} Sefer")
    c3.metric("🚛 Çalışan Araç", f"{f_df['plaka'].nunique()} Araç")
    c4.metric("⏱️ Ort. Kantar Süresi", f"{f_df['tur_suresi_dk'].mean():.1f} Dk" if not f_df.empty else "-")
    c5.metric("⏳ Ort. Sefer Arası Süre", f"{f_df['seferler_arasi_dk'].mean():.1f} Dk" if not f_df.empty else "-")

    st.markdown("---")
    st.subheader(f"📋 Araç Performans Tablosu ({secilen_tarih})")

    if not f_df.empty:
        arac_perf = f_df.groupby(['plaka', 'gemi_adi', 'bosaltma_yeri']).agg(
            Atilan_Sefer=('id', 'count'),
            Toplam_Tonaj=('net_tonaj', 'sum'),
            Ort_Sefer_Tonaj=('net_tonaj', 'mean'),
            Ort_Tur_Suresi_Dk=('tur_suresi_dk', 'mean'),
            Ort_Seferler_Arasi_Dk=('seferler_arasi_dk', 'mean')
        ).reset_index().sort_values(by='Atilan_Sefer', ascending=False)

        st.dataframe(arac_perf, height=400)
