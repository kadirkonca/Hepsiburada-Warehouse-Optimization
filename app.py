import streamlit as st
import pandas as pd
import pulp
import os
import json
from io import BytesIO
from datetime import datetime

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hepsiburada Senaryo Merkezi", layout="wide")

# DOSYA YOLLARI
DB_FILE = "shared_warehouse_data.csv"
HISTORY_FILE = "all_scenarios_history.json" 

# --- SABİT TANIMLAMALAR ---
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
CEYREKLER = {"Q1": ["Ocak", "Şubat", "Mart"], "Q2": ["Nisan", "Mayıs", "Haziran"], 
             "Q3": ["Temmuz", "Ağustos", "Eylül"], "Q4": ["Ekim", "Kasım", "Aralık"]}
ALTI_AYLIK = {"H1": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran"], 
              "H2": ["Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]}

# --- FONKSİYONLAR ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_history_all(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def format_and_center(val):
    try:
        formatted = "{:,.0f}".format(float(val)).replace(",", ".")
        return f"      {formatted}      "
    except: return val

def unformat_dots(val):
    if isinstance(val, str):
        return float(val.strip().replace(".", "").replace(",", ""))
    return val

# --- VERİLERİ YÜKLE ---
if "table_version" not in st.session_state: st.session_state["table_version"] = 0
full_history = load_history()

# --- SOL PANEL ---
st.sidebar.header("📜 Merkezi Senaryo Arşivi")
if full_history:
    new_history_list = full_history.copy()
    for idx, entry in enumerate(full_history):
        with st.sidebar.expander(f"📍 {entry['isim']} | 👤 {entry.get('yukleyen', 'Bilinmiyor')}"):
            st.caption(f"📅 {entry['tarih']}")
            if st.button("📤 Yükle", key=f"h_load_{idx}"):
                pd.DataFrame(entry['veri']).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
            if st.button("🗑️ Sil", key=f"h_del_{idx}"):
                new_history_list.pop(idx)
                save_history_all(new_history_list)
                st.rerun()
else: st.sidebar.info("Arşiv boş.")

st.sidebar.markdown("---")
st.sidebar.header("📤 Veri Yükle (Yıllık/Aylık)")
up_user = st.sidebar.text_input("Ad Soyad:", key="up_user")
up_label = st.sidebar.text_input("Senaryo/Dosya Adı:", key="up_label")
uploaded_file = st.sidebar.file_uploader("Excel/CSV", type=["csv", "xlsx"])

if uploaded_file and up_user and up_label:
    if st.sidebar.button("✅ Arşive İşle"):
        up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        up_df.to_csv(DB_FILE, index=False)
        new_entry = {"tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "isim": up_label, 
                     "yukleyen": up_user, "tip": "Yükleme", "veri": up_df.to_dict(orient="list")}
        full_history.insert(0, new_entry); save_history_all(full_history)
        st.session_state["table_version"] += 1; st.rerun()

# --- ANA EKRAN FİLTRELEME SİSTEMİ ---
st.title("🚀 Hepsiburada Stratejik Planlama Merkezi")

# Veriyi oku
if os.path.exists(DB_FILE):
    main_df = pd.read_csv(DB_FILE)
else:
    # Eğer dosya yoksa örnek bir yapı oluştur (Yıl ve Ay sütunları ile)
    main_df = pd.DataFrame({
        "Yıl": [2025]*7, "Ay": ["Ocak"]*7,
        "Depo Adı": ["Gebze Depo", "İzmir Torbalı Depo", "İzmir Pancar Depo", "Düzce Depo", "Bilecik Depo", "Adana Depo", "İzmir Pınarbaşı Depo"],
        "Kapasite (m3)": [19301, 13824, 3365, 15343, 22000, 2133, 4694],
        "Kira Maliyeti (₺)": [10072228, 3353400, 2296381, 2697600, 3310998, 0, 737965],
        "Fix Cost (m3 Başı)": [185.19, 31.15, 277.30, 73.51, 55.12, 73.18, 48.03]
    })

st.markdown("### 🔍 Veri Filtreleme ve Periyot Seçimi")
f_col1, f_col2 = st.columns(2)

with f_col1:
    selected_year = st.selectbox("Yıl Seçin:", options=[2025, 2026], index=0)

with f_col2:
    period_options = ["Tek Ay Seçimi", "Çeyrek Bazlı (Q)", "6 Aylık (H)", "Tüm Yıl (FY)"]
    selected_period_type = st.selectbox("Periyot Tipi:", options=period_options)

# Dinamik alt filtreler
filter_months = []
if selected_period_type == "Tek Ay Seçimi":
    m = st.selectbox("Ay Seçin:", AYLAR)
    filter_months = [m]
elif selected_period_type == "Çeyrek Bazlı (Q)":
    q = st.selectbox("Çeyrek Seçin:", list(CEYREKLER.keys()))
    filter_months = CEYREKLER[q]
elif selected_period_type == "6 Aylık (H)":
    h = st.selectbox("Yarı Yıl Seçin:", list(ALTI_AYLIK.keys()))
    filter_months = ALTI_AYLIK[h]
elif selected_period_type == "Tüm Yıl (FY)":
    st.info(f"{selected_year} yılının tüm verileri gösteriliyor.")
    filter_months = AYLAR

# --- VERİ İŞLEME ---
# Seçilen yıl ve aylara göre filtrele
filtered_df = main_df[(main_df["Yıl"] == selected_year) & (main_df["Ay"].isin(filter_months))]

# Eğer seçilen periyotta birden fazla ay varsa (Q, H, FY), depoları gruplayıp topla
if len(filter_months) > 1:
    st.warning(f"⚠️ {', '.join(filter_months)} verileri konsolide ediliyor (Toplam m3 ve Toplam Kira).")
    display_df = filtered_df.groupby("Depo Adı").agg({
        "Kapasite (m3)": "sum",
        "Kira Maliyeti (₺)": "sum",
        "Fix Cost (m3 Başı)": "mean" # Fix cost genelde ortalama alınır
    }).reset_index()
else:
    display_df = filtered_df.drop(columns=["Yıl", "Ay"]) if "Yıl" in filtered_df.columns else filtered_df

st.subheader(f"📊 {selected_year} - {selected_period_type} Çalışma Tablosu")

# Formatlama
view_df = display_df.copy()
if "Kapasite (m3)" in view_df.columns: view_df["Kapasite (m3)"] = view_df["Kapasite (m3)"].apply(format_and_center)
if "Kira Maliyeti (₺)" in view_df.columns: view_df["Kira Maliyeti (₺)"] = view_df["Kira Maliyeti (₺)"].apply(format_and_center)

column_config = {
    "Depo Adı": st.column_config.TextColumn("Depo Adı", width="medium"),
    "Kapasite (m3)": st.column_config.TextColumn("Kapasite (m3)"),
    "Kira Maliyeti (₺)": st.column_config.TextColumn("Kira Maliyeti (₺)"),
    "Fix Cost (m3 Başı)": st.column_config.NumberColumn("Fix Cost (m3 Başı)", format="%.2f"),
}

edited_df_display = st.data_editor(view_df, use_container_width=True, num_rows="dynamic", column_config=column_config, key=f"ed_v{st.session_state['table_version']}")

# --- KAYDETME ---
st.divider()
c1, c2, c3 = st.columns([1,1,1])
save_user = c1.text_input("Yükleyen/Düzenleyen:", placeholder="Kadir Konca")
save_name = c2.text_input("Senaryo Adı:", placeholder="2025_Q1_Final")

if c3.button("💾 Senaryoyu Arşive Ekle", use_container_width=True):
    if save_user and save_name:
        # Geriye dönük sayısal temizlik
        save_df = edited_df_display.copy()
        save_df["Kapasite (m3)"] = save_df["Kapasite (m3)"].apply(unformat_dots)
        save_df["Kira Maliyeti (₺)"] = save_df["Kira Maliyeti (₺)"].apply(unformat_dots)
        
        new_entry = {"tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "isim": save_name, 
                     "yukleyen": save_user, "tip": "Manuel Kayıt", "veri": save_df.to_dict(orient="list")}
        full_history.insert(0, new_entry); save_history_all(full_history)
        st.success("Senaryo kaydedildi!"); st.rerun()

# --- OPTİMİZASYON ---
st.divider()
target_demand = st.number_input("Hedeflenen Toplam Sevkiyat Talebi (m3)", value=35000)
if st.button("🚀 Seçili Periyot İçin Optimizasyonu Çalıştır", use_container_width=True):
    try:
        # Sayısal veriye çevir
        opt_df = edited_df_display.copy()
        opt_df["Kapasite (m3)"] = opt_df["Kapasite (m3)"].apply(unformat_dots)
        opt_df["Kira Maliyeti (₺)"] = opt_df["Kira Maliyeti (₺)"].apply(unformat_dots)
        
        prob = pulp.LpProblem("Warehouse_Minimization", pulp.LpMinimize)
        depolar = opt_df["Depo Adı"].tolist()
        usage = pulp.LpVariable.dicts("m3", depolar, lowBound=0)
        
        prob += pulp.lpSum([(usage[d] * float(opt_df.loc[opt_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0])) + 
                            float(opt_df.loc[opt_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0]) for d in depolar])
        
        prob += pulp.lpSum([usage[d] for d in depolar]) == target_demand
        for d in depolar:
            prob += usage[d] <= float(opt_df.loc[opt_df["Depo Adı"] == d, "Kapasite (m3)"].values[0])
            
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        if pulp.LpStatus[prob.status] == 'Optimal':
            cost_f = "{:,.0f}".format(pulp.value(prob.objective)).replace(",", ".")
            st.markdown(f"### 💰 Periyot Sonu Toplam Maliyet: **{cost_f} ₺**")
            res_df = pd.DataFrame([{"Depo": d, "Atanan (m3)": round(usage[d].varValue, 2)} for d in depolar])
            st.dataframe(res_df.style.format({"Atanan (m3)": "{:,.2f}"}), use_container_width=True)
    except Exception as e: st.error(f"Hata: {e}")

st.sidebar.caption("v4.0 - Yıllık & Dönemsel Planlama Modülü")
