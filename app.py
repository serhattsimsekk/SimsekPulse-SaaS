import streamlit as st

# ⚠️ KRİTİK KURAL: set_page_config her zaman İLK Streamlit komutu olmalı!
st.set_page_config(
    page_title="Şimşek Lojistik | SimsekPulse Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Kurumsal Görünüm - Menü ve Alt Yazı Temizliği (CSS Enjeksiyonu)
st.markdown("""
<style>
    /* Üst Menü, Header ve Footer Gizleme */
    .stAppHeader, #MainMenu, footer, header {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Streamlit Rozetleri ve Toolbar Gizleme */
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"] {
        display: none !important;
    }

    /* Sayfa Üst Boşluğunu Optimize Etme */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)
