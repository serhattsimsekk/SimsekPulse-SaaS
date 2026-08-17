st.markdown("""
<style>
    /* 1. Üst Menü, Header, Footer ve Toolbar Gizleme */
    .stAppHeader, #MainMenu, footer, header {
        display: none !important;
        visibility: hidden !important;
    }
    
    /* 2. Sağ Alttaki Profil İkonu ve Kırmızı Streamlit Rozetini Temizleme */
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"],
    .viewerBadge_container__1vB22,
    .viewerBadge_link__1S137,
    div[class*="viewerBadge"],
    div[class*="profileContainer"],
    div[class*="stAppFooter"],
    a[href*="streamlit.io"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    /* Sayfa Arka Planı ve Yerleşim Optimization */
    .stApp {
        background-color: #0b1329 !important;
    }
    .block-container {
        padding: 0.8rem 1rem !important;
        max-width: 100% !important;
    }
</style>
""", unsafe_allow_html=True)
