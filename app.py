import streamlit as st
import pandas as pd

# 1. SAYFA YAPILANDIRMASI (Excel Modu)
st.set_page_config(
    page_title="Şimşek Lojistik | Excel Sevkiyat Matrisi",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 2. EXCEL BİREBİR ARAYÜZ VE HÜCRE STİLLERİ (CSS)
st.markdown("""
<style>
    /* Streamlit Menü ve Başlıkları Gizle */
    .stAppHeader, #MainMenu, footer, header,
    [data-testid="stDecoration"],
    [data-testid="stStatusWidget"],
    [data-testid="stToolbar"] {
        display: none !important;
        visibility: hidden !important;
    }

    .stApp {
        background-color: #0b1329 !important;
        color: #000000;
    }

    .block-container {
        padding: 0.5rem 1rem !important;
        max-width: 100% !important;
    }

    /* Excel Üst Bilgi Çubuğu */
    .excel-top-bar {
        background-color: #0d2137;
        color: #ffffff;
        padding: 8px 15px;
        font-family: 'Calibri', 'Segoe UI', sans-serif;
        font-weight: bold;
        font-size: 14px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 2px solid #1a365d;
    }

    /* BİREBİR EXCEL TABLO MATRİSİ STİLİ */
    .excel-container {
        width: 100%;
        overflow-x: auto;
        background-color: #ffffff;
        border: 2px solid #2b4c7e;
        margin-top: 5px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.5);
    }

    .excel-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Calibri', 'Arial', sans-serif;
        font-size: 12px;
        color: #000000;
    }

    .excel-table th, .excel-table td {
        border: 1px solid #a6b9ca;
        padding: 4px 6px;
        text-align: center;
        white-space: nowrap;
        font-weight: 600;
    }

    /* Excel Başlık Hücreleri */
    .th-header { background-color: #d9e1f2; color: #000; font-weight: bold; }
    .th-cinsi { background-color: #2f5597; color: #ffffff; font-weight: bold; font-size: 13px; }
    .row-ozmal { background-color: #e2efda; color: #375623; font-weight: bold; }
    .row-destek { background-color: #fce4d6; color: #c65911; font-weight: bold; }

    /* Görseldeki Renkli Sütun Hücreleri */
    .col-green { background-color: #00c853 !important; color: #000000 !important; font-weight: bold; }
    .col-cyan { background-color: #00e5ff !important; color: #000000 !important; font-weight: bold; }
    .col-purple { background-color: #b388ff !important; color: #000000 !important; font-weight: bold; }
    .col-blue { background-color: #80d8ff !important; color: #000000 !important; font-weight: bold; }
    .col-orange { background-color: #ff9100 !important; color: #000000 !important; font-weight: bold; }
    .col-white { background-color: #ffffff !important; color: #000000 !important; }

    /* Alt Excel Sayfa Sekmeleri (Sheet Tabs) */
    .excel-sheets-bar {
        background-color: #e6e6e6;
        padding: 4px 10px;
        display: flex;
        gap: 2px;
        border-top: 1px solid #b0b0b0;
        font-family: 'Segoe UI', sans-serif;
        font-size: 11px;
    }

    .sheet-tab {
        padding: 5px 15px;
        background-color: #d9d9d9;
        border: 1px solid #b0b0b0;
        border-bottom: none;
        border-radius: 3px 3px 0 0;
        color: #333333;
        font-weight: 600;
        cursor: pointer;
    }

    .sheet-tab.active {
        background-color: #ffffff;
        color: #008000;
        border-top: 3px solid #008000;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# 3. EXCEL ÜST BANT (Vardiya & Tarih)
st.markdown("""
<div class="excel-excel-top-bar excel-top-bar">
    <div>⚡ ŞİMŞEK LOJİSTİK - İSKENDERUN / DİLOVASI SAHA MATRİSİ</div>
    <div>📅 12.08.2026 VARDİYA AMİRLERİ: SİNAN GÜL // MUSTAFA ÇETİN</div>
</div>
""", unsafe_allow_html=True)

# 4. CANLI EXCEL MATRİS TABLOSU (HTML/CSS REPLİKA)
st.markdown("""
<div class="excel-container">
    <table class="excel-table">
        <thead>
            <tr class="th-header">
                <th style="width: 40px;">LİMAN GEMİ ADI TESİS YERLERİ</th>
                <th colspan="2">MMK PORT / SAHA 1</th>
                <th>EYAP LİMANI</th>
                <th>GÜUB LİMANI</th>
                <th>ISKEN SANTRAL</th>
                <th>TOSYALI LİMANI</th>
            </tr>
            <tr class="th-cinsi">
                <td>CİNSİ</td>
                <td colspan="2">HURDA / DÖKME YÜK</td>
                <td>SİLİS KUMU</td>
                <td>ÇİMENTO</td>
                <td>KÖMÜR</td>
                <td>CEVHER</td>
            </tr>
            <tr class="row-ozmal">
                <td>ÖZ MAL (FİLO)</td>
                <td colspan="2">79 Araç</td>
                <td>14 Araç</td>
                <td>7 Araç</td>
                <td>21 Araç</td>
                <td>12 Araç</td>
            </tr>
            <tr class="row-destek">
                <td>DESTEK (DİŞ)</td>
                <td colspan="2">0 Araç</td>
                <td>0 Araç</td>
                <td>0 Araç</td>
                <td>0 Araç</td>
                <td>2 Araç</td>
            </tr>
            <tr class="th-header" style="background-color: #b4c6e7;">
                <th>SIRA</th>
                <th>HAT 1 (ÖZEL)</th>
                <th>HAT 2 (GENEL)</th>
                <th>SAHA A</th>
                <th>SAHA B</th>
                <th>SAHA C</th>
                <th>SAHA D</th>
            </tr>
        </thead>
        <tbody>
            <tr><td><b>1</b></td><td class="col-green">31 ANM 573</td><td>31 ANM 593</td><td class="col-cyan">31 ANK 374</td><td class="col-cyan">31 AAG 291</td><td class="col-purple">31 ANM 598</td><td class="col-purple">31 ANN 331</td></tr>
            <tr><td><b>2</b></td><td class="col-green">31 ANN 019</td><td>31 ANN 168</td><td class="col-cyan">31 ANL 936</td><td class="col-cyan">31 AKL 553</td><td class="col-purple">31 AIU 808</td><td class="col-purple">31 AOK 866</td></tr>
            <tr><td><b>3</b></td><td class="col-green">31 ANM 150</td><td>31 ANN 304</td><td class="col-cyan">31 ANM 576</td><td class="col-cyan">31 AKL 554</td><td class="col-purple">31 AIU 869</td><td class="col-purple">31 AKL 556</td></tr>
            <tr><td><b>4</b></td><td class="col-white">31 AOB 800</td><td>31 ANN 312</td><td class="col-cyan">31 ANN 284</td><td class="col-cyan">31 AKL 852</td><td class="col-purple">31 ANK 278</td><td class="col-purple">31 ANM 210</td></tr>
            <tr><td><b>5</b></td><td class="col-white">31 AIU 820</td><td>31 ANV 235</td><td class="col-cyan">31 ANR 925</td><td class="col-cyan">31 AKL 862</td><td class="col-purple">31 ANM 584</td><td class="col-purple">31 AIY 548</td></tr>
            <tr><td><b>6</b></td><td class="col-white">31 AKL 545</td><td>31 ANV 253</td><td class="col-cyan">31 ANR 938</td><td class="col-cyan">31 ANJ 636</td><td class="col-purple">31 ANN 358</td><td class="col-purple">31 AOV 949</td></tr>
            <tr><td><b>7</b></td><td class="col-white">31 ANJ 479</td><td>31 AOB 756</td><td class="col-cyan">31 ANR 943</td><td class="col-cyan">31 ANK 359</td><td class="col-purple">31 ANR 916</td><td class="col-purple">31 ANF 677</td></tr>
            <tr><td><b>8</b></td><td class="col-white">31 ANM 112</td><td>31 AOK 710</td><td class="col-white">31 AOB 847</td><td class="col-cyan">31 ANM 091</td><td class="col-purple">31 ANR 937</td><td class="col-orange">31 AOK 698</td></tr>
            <tr><td><b>9</b></td><td class="col-white">31 ANM 157</td><td>31 AOK 715</td><td class="col-white">31 AOK 711</td><td class="col-cyan">31 ANM 187</td><td class="col-purple">31 AOV 941</td><td class="col-orange">31 AIY 560</td></tr>
            <tr><td><b>10</b></td><td class="col-white">31 ANM 200</td><td>31 AOV 747</td><td class="col-white">31 AOV 964</td><td class="col-cyan">31 ANM 201</td><td class="col-purple">31 AOV 956</td><td class="col-orange">31 AOC 430</td></tr>
            <tr><td><b>11</b></td><td class="col-white">31 ANM 219</td><td>31 AOV 960</td><td class="col-white">31 ASZ 260</td><td class="col-cyan">31 ANM 244</td><td class="col-purple">31 ANN 018</td><td class="col-orange">31 ANM 211</td></tr>
            <tr><td><b>12</b></td><td class="col-white">31 ANM 243</td><td>31 AOV 973</td><td class="col-white">31 AUR 259</td><td class="col-cyan">31 ANM 254</td><td class="col-purple">31 ASZ 241</td><td class="col-orange">31 ANM 337</td></tr>
            <tr><td><b>13</b></td><td class="col-white">31 ANM 265</td><td>31 APP 839</td><td class="col-white">31 AUR 263</td><td class="col-cyan">31 ANM 260</td><td class="col-purple">31 ANM 286</td><td class="col-orange">31 ANM 264</td></tr>
            <tr><td><b>14</b></td><td class="col-white">31 ANM 295</td><td>31 AUR 239</td><td class="col-white">31 AUR 289</td><td class="col-cyan">31 ANM 566</td><td class="col-purple">31 AOV 943</td><td class="col-orange">31 AIY 516</td></tr>
            <tr><td><b>15</b></td><td class="col-white">31 ANM 664</td><td>31 AUR 243</td><td class="col-white">31 AUR 297</td><td class="col-cyan">31 ANR 914</td><td class="col-white">31 ABC 123</td><td class="col-orange">31 ANM 285</td></tr>
        </tbody>
    </table>
</div>
""", unsafe_allow_html=True)

# 5. ALT EXCEL SAYFA SEKMELERİ (Sheet Tabs)
st.markdown("""
<div class="excel-sheets-bar">
    <div class="sheet-tab">AYLIK ÖZET</div>
    <div class="sheet-tab">ARAÇ GRUP DÜZENİ</div>
    <div class="sheet-tab">ARAÇ VERİTABANI</div>
    <div class="sheet-tab">11.08.2026</div>
    <div class="sheet-tab active">GÜNCEL SEVKİYAT</div>
</div>
""", unsafe_allow_html=True)

# 6. EXCEL DÜZENLEME & İŞLEVSALLİK PANELİ (Veri Girişi)
st.markdown("<br>", unsafe_allow_html=True)
with st.expander("📝 Excel Matrisine Araç / Plaka Ekle - Düzenle"):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.text_input("Plaka No:", placeholder="Örn: 31 ANM 573")
    with c2:
        st.selectbox("Hedef Sütun / Tesis:", ["MMK PORT (Hurda)", "EYAP (Silis Kumu)", "GÜUB (Çimento)", "TOSYALI"])
    with c3:
        st.selectbox("Renk Kodlama:", ["Yeşil (Aktif)", "Turkuaz (Yolda)", "Mor (Kantar)", "Turuncu (Destek)"])
    with c4:
        st.button("➕ Matrise Kaydet", use_container_width=True)
