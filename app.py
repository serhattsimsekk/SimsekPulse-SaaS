# app.py içindeki st.markdown CSS bloğunun en altına ekle:
st.markdown("""
<style>
    /* Sağ alttaki tüm yüzen rozetleri, profil ikonunu ve Streamlit filigranlarını zorla gizle */
    footer, header, #MainMenu, .stAppHeader,
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"],
    [data-testid="stActionButton"],
    div[class*="viewerBadge"],
    div[class*="profileContainer"],
    div[class*="stAppFooter"],
    div[class*="floating"],
    div[data-test-script-badge],
    a[href*="streamlit.io"],
    a[href*="github.com"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        pointer-events: none !important;
    }

    /* Ekranın sağ alt köşesine sabitlenen her türlü öğeyi sıfırla */
    div[style*="position: fixed"][style*="bottom"],
    div[style*="position: absolute"][style*="bottom"] {
        display: none !important;
    }
</style>
""", unsafe_allow_html=True)
