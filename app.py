import streamlit as st

# Temiz & Kurumsal Arayüz CSS Enjeksiyonu
st.markdown("""
<style>
    /* Sağ üstteki Fork, GitHub ve Varsayılan Menüyü Gizle */
    .stAppHeader, #MainMenu, footer, header {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* Sağ alttaki Streamlit Rozetlerini ve İmzaları Yok Et */
    .viewerBadge_container__1vB22, 
    .viewerBadge_link__1S137,
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"] {
        display: none !important;
    }

    /* Sayfa Üst Boşluğunu Sıfırla */
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 1rem !important;
    }
</style>
""", unsafe_allow_html=True)
