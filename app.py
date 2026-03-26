import streamlit as st
import pandas as pd
import pulp
import os
import json
from io import BytesIO
from datetime import datetime

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hepsiburada Senaryo Merkezi", layout="wide")

# --- SOL ÜST ÖZEL TASARIM ---
st.sidebar.markdown(
    """
    <div style="background-color: #1e1e1e; padding: 25px 10px; border-radius: 15px; text-align: center; margin-bottom: 25px; border: 2px solid #FF6000;">
        <h1 style="font-family: 'Arial Black', Gadget, sans-serif; color: #FF6000; font-size: 24px; margin: 0; padding: 0; letter-spacing: 2px;">
            HEPSİBURADA
        </h1>
        <h2 style="font-family: 'Verdana', Geneva, sans-serif; color: #FFFFFF; font-size: 14px; font-weight: 100; margin-top: 8px; opacity: 0.9; letter-spacing: 1px;">
            Warehouse Optimization
        </h2>
    </div>
    """,
    unsafe_allow_html=True
)

# DOSYA YOLLARI
DB_FILE = "shared_warehouse_data.csv"
HISTORY_FILE = "all_scenarios_history.json" 

# --- SABİT TANIMLAMALAR ---
AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
PERIYOT_LISTESI = AYLAR + ["--- Çeyrekler ---", "Q1", "Q2", "Q3", "Q4", "--- Yarı Yıllar ---", "H1", "H2", "--- Yıl Sonu ---", "FY (Full Year)"]

CEYREKLER = {"Q1": ["Ocak", "Şubat", "Mart"], "Q2": ["Nisan", "Mayıs", "Haziran"], "Q3": ["Temmuz", "Ağustos", "Eylül"], "Q4": ["Ekim", "Kasım", "Aralık"]}
ALTI_AYLIK = {"H1": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran"], "H2": ["Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]}

# --- 2025 DATABASE HAZIRLAMA (Excel'den Gelen Veriler) ---
def initialize_database():
    if not os.path.exists(DB_FILE):
        data_2025 = []
        # Dosyandan aldığım depo listesi ve yıllık kira verileri (Kapaklı, Gebze, Tuzla vb.)
        depo_maliyetleri = {
            "Kapaklı Depo": [11826000, 11826000, 11826000, 11826000, 11826000, 11826000, 14782500, 14782500, 14782500, 14782500, 14782500, 14782500],
            "Gebze Depo": [10072228, 10072228, 10072228, 10072228, 10072228, 10072228, 12590285, 12590285, 12590285, 12590285, 12590285, 12590285],
            "Tuzla Depo": [3638250, 3638250, 3638250, 3638250, 3638250, 3638250, 4547813, 4547813, 4547813, 4547813, 4547813, 4547813],
            "İzmir Torbalı Depo": [3353400, 3353400, 3353400, 3353400, 3353400, 3353400, 4191750, 4191750, 4191750, 4191750, 4191750, 4191750],
            "İzmir Pancar Depo": [2296381, 2296381, 2296381, 2296381, 2296381, 2296381, 2870476, 2870476, 2870476, 2870476, 2870476, 2870476],
            "Düzce Depo": [2697600, 2697600, 2697600, 2697600, 2697600, 2697600, 3372000, 3372000, 3372000, 3372000, 3372000, 3372000],
            "Bilecik Depo": [3310998, 3310998, 3310998, 3310998, 3310998, 3310998, 4138748, 4138748, 4138748, 4138748, 4138748, 4138748],
            "İzmir Pınarbaşı Depo": [737965, 737965, 737965, 737965, 737965, 737965, 922456, 922456, 922456, 922456, 922456, 922456]
        }
        
        kapasite_fix = {
            "Kapaklı Depo": (32000, 36.32), "Gebze Depo": (19301, 185.19), "Tuzla Depo": (15343, 10.00), 
            "İzmir Torbalı Depo": (13824, 31.15), "İzmir Pancar Depo": (3365, 277.30), "Düzce Depo": (15343, 73.51), 
            "Bilecik Depo": (22000, 55.12), "İzmir Pınarbaşı Depo": (4694, 48.03)
        }

        for depo, kiralar in depo_maliyetleri.items():
            kap, fix = kapasite_fix[depo]
            for i, ay_adi in enumerate(AYLAR):
                data_2025.append({
                    "Yıl": 2025, "Ay": ay_adi, "Depo Adı": depo,
                    "Kapasite (m3)": kap, "Kira Maliyeti (₺)": kiralar[i], "Fix Cost (m3 Başı)": fix
                })
        
        df_init = pd.DataFrame(data_2025)
        df_init.to_csv(DB_FILE, index=False)

initialize_database()

# --- FONKSİYONLAR ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_history_all(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(history, f, ensure_ascii=False, indent=4)

def format_and_center(val):
    try: return f"      {'{:,.0f}'.format(float(val)).replace(',', '.')}      "
    except: return val

def unformat_dots(val):
    if isinstance(val, str): return float(val.strip().replace(".", "").replace(",", ""))
    return val

full_history = load_history()

# --- SOL PANEL ---
st.sidebar.header("📜 Merkezi Senaryo Arşivi")
if full_history:
    for idx, entry in enumerate(full_history):
        with st.sidebar.expander(f"📍 {entry['isim']} | 👤 {entry.get('yukleyen', 'Bilinmiyor')}"):
            if st.button("📤 Tabloya Yükle", key=f"h_load_{idx}"):
                pd.DataFrame(entry['veri']).to_csv(DB_FILE, index=False)
                st.rerun()
            if st.button("🗑️ Sil", key=f"h_del_{idx}"):
                full_history.pop(idx); save_history_all(full_history); st.rerun()
else: st.sidebar.info("Arşiv boş.")

st.sidebar.markdown("---")
st.sidebar.header("📤 Veri Ekle")
up_user = st.sidebar.text_input("Ad Soyad:", key="up_user")
up_label = st.sidebar.text_input("Senaryo Adı:", key="up_label")
uploaded_file = st.sidebar.file_uploader("Excel/CSV", type=["csv", "xlsx"])

if uploaded_file and up_user and up_label:
    if st.sidebar.button("✅ Kaydet"):
        up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        up_df.to_csv(DB_FILE, index=False)
        new_entry = {"tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "isim": up_label, "yukleyen": up_user, "veri": up_df.to_dict(orient="list")}
        full_history.insert(0, new_entry); save_history_all(full_history); st.rerun()

# --- ANA EKRAN ---
st.title("🚀 Hepsiburada Stratejik Planlama Merkezi")
main_df = pd.read_csv(DB_FILE)

st.markdown("### 🔍 Görünüm ve Sıralama Ayarları")
f_col1, f_col2, f_col3 = st.columns(3)
with f_col1: selected_year = st.selectbox("📅 Yıl Seçin:", options=[2025, 2026], index=0)
with f_col2: selected_period = st.selectbox("⏱️ Periyot Seçin:", options=PERIYOT_LISTESI)
with f_col3: sort_option = st.selectbox("🔃 Sırala:", options=["Depo Adı (A-Z)", "Depo Adı (Z-A)", "Kapasite (Yüksek->Düşük)", "Kapasite (Düşük->Yüksek)", "Kira Maliyeti (Yüksek->Düşük)", "Kira Maliyeti (Düşük->Yüksek)", "Fix Cost (Yüksek->Düşük)", "Fix Cost (Düşük->Yüksek)"])

filter_months = []
if selected_period in AYLAR: filter_months = [selected_period]
elif selected_period in CEYREKLER: filter_months = CEYREKLER[selected_period]
elif selected_period in ALTI_AYLIK: filter_months = ALTI_AYLIK[selected_period]
elif selected_period == "FY (Full Year)": filter_months = AYLAR
else: filter_months = ["Ocak"]

filtered_df = main_df[(main_df["Yıl"] == selected_year) & (main_df["Ay"].isin(filter_months))]

if len(filter_months) > 1:
    display_df = filtered_df.groupby("Depo Adı").agg({"Kapasite (m3)": "sum", "Kira Maliyeti (₺)": "sum", "Fix Cost (m3 Başı)": "mean"}).reset_index()
else:
    display_df = filtered_df.drop(columns=["Yıl", "Ay"]) if "Yıl" in filtered_df.columns else filtered_df

# Sıralama Uygulama
sort_map = {"Depo Adı (A-Z)": ("Depo Adı", True), "Depo Adı (Z-A)": ("Depo Adı", False), "Kapasite (Yüksek->Düşük)": ("Kapasite (m3)", False), "Kapasite (Düşük->Yüksek)": ("Kapasite (m3)", True), "Kira Maliyeti (Yüksek->Düşük)": ("Kira Maliyeti (₺)", False), "Kira Maliyeti (Düşük->Yüksek)": ("Kira Maliyeti (₺)", True), "Fix Cost (Yüksek->Düşük)": ("Fix Cost (m3 Başı)", False), "Fix Cost (Düşük->Yüksek)": ("Fix Cost (m3 Başı)", True)}
col, asc = sort_map[sort_option]
display_df = display_df.sort_values(by=col, ascending=asc)

st.subheader(f"📊 {selected_year} - {selected_period}")
view_df = display_df.copy()
view_df["Kapasite (m3)"] = view_df["Kapasite (m3)"].apply(format_and_center)
view_df["Kira Maliyeti (₺)"] = view_df["Kira Maliyeti (₺)"].apply(format_and_center)

column_config = {"Depo Adı": st.column_config.TextColumn("Depo Adı", width="medium"), "Kapasite (m3)": st.column_config.TextColumn("Kapasite (m3)"), "Kira Maliyeti (₺)": st.column_config.TextColumn("Kira Maliyeti (₺)"), "Fix Cost (m3 Başı)": st.column_config.NumberColumn("Fix Cost (m3 Başı)", format="%.2f")}
edited_df_display = st.data_editor(view_df, use_container_width=True, num_rows="dynamic", column_config=column_config)

# --- KAYDETME VE OPTİMİZASYON ---
st.divider()
c1, c2, c3 = st.columns([1,1,1])
save_user = c1.text_input("👤 Kaydeden:", placeholder="Kadir Konca")
save_name = c2.text_input("📝 Senaryo Adı:", placeholder="Plan_v1")

if c3.button("💾 Arşive Ekle", use_container_width=True) and save_user and save_name:
    save_df = edited_df_display.copy()
    save_df["Kapasite (m3)"] = save_df["Kapasite (m3)"].apply(unformat_dots)
    save_df["Kira Maliyeti (₺)"] = save_df["Kira Maliyeti (₺)"].apply(unformat_dots)
    new_entry = {"tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "isim": save_name, "yukleyen": save_user, "veri": save_df.to_dict(orient="list")}
    full_history.insert(0, new_entry); save_history_all(full_history); st.success("Arşivlendi!"); st.rerun()

st.divider()
target_demand = st.number_input("🎯 Hedeflenen Sevkiyat Talebi (m3)", value=35000)
if st.button("🚀 Optimizasyonu Çalıştır", use_container_width=True):
    try:
        opt_df = edited_df_display.copy()
        opt_df["Kapasite (m3)"] = opt_df["Kapasite (m3)"].apply(unformat_dots)
        opt_df["Kira Maliyeti (₺)"] = opt_df["Kira Maliyeti (₺)"].apply(unformat_dots)
        prob = pulp.LpProblem("MinCost", pulp.LpMinimize)
        usage = pulp.LpVariable.dicts("m3", opt_df["Depo Adı"], lowBound=0)
        prob += pulp.lpSum([(usage[d] * float(opt_df.loc[opt_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0])) + float(opt_df.loc[opt_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0]) for d in opt_df["Depo Adı"]])
        prob += pulp.lpSum([usage[d] for d in opt_df["Depo Adı"]]) == target_demand
        for d in opt_df["Depo Adı"]: prob += usage[d] <= float(opt_df.loc[opt_df["Depo Adı"] == d, "Kapasite (m3)"].values[0])
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        if pulp.LpStatus[prob.status] == 'Optimal':
            st.markdown(f"### 💰 Toplam Maliyet: **{'{:,.0f}'.format(pulp.value(prob.objective)).replace(',', '.')} ₺**")
            res_df = pd.DataFrame([{"Depo": d, "Atanan (m3)": round(usage[d].varValue, 2)} for d in opt_df["Depo Adı"]])
            st.dataframe(res_df.style.format({"Atanan (m3)": "{:,.2f}"}), use_container_width=True)
    except Exception as e: st.error(f"Hata: {e}")
