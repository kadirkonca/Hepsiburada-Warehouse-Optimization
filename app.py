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

# --- SADECE SAYFA1 VERİLERİYLE DATABASE BAŞLATMA ---
def initialize_database():
    data_2025 = []
    
    # Sayfa1'deki gerçek veriler (Kira, Kapasite, Fix Cost hepsi buradan)
    # Tem-Ara dönemindeki kira artışları dahil edildi.
    sayfa1_data = {
        "Gebze Depo": {"kiralar": [10072228]*6 + [12590285]*6, "kap": 19301, "fix": 185.19},
        "İzmir Torbalı Depo": {"kiralar": [3353400]*6 + [4191750]*6, "kap": 13824, "fix": 31.15},
        "İzmir Pancar Depo": {"kiralar": [2296381]*6 + [2870476]*6, "kap": 3365, "fix": 277.30},
        "Düzce Depo": {"kiralar": [2697600]*6 + [3372000]*6, "kap": 15343, "fix": 73.51},
        "Bilecik Depo": {"kiralar": [3310998]*6 + [4138748]*6, "kap": 22000, "fix": 55.12},
        "Adana Depo": {"kiralar": [0]*12, "kap": 2133, "fix": 73.18},
        "İzmir Pınarbaşı Depo": {"kiralar": [737965]*6 + [922456]*6, "kap": 4694, "fix": 48.03},
        "Ankara Depo": {"kiralar": [0]*12, "kap": 4038, "fix": 68.30},
        "Kapaklı Depo": {"kiralar": [11826000]*6 + [14782500]*6, "kap": 32000, "fix": 36.32},
        "Tuzla Depo": {"kiralar": [3638250]*6 + [4547813]*6, "kap": 15343, "fix": 10.00}
    }

    for depo, vals in sayfa1_data.items():
        for i, ay_adi in enumerate(AYLAR):
            data_2025.append({
                "Yıl": 2025, "Ay": ay_adi, "Depo Adı": depo,
                "Kapasite (m3)": vals["kap"], 
                "Kira Maliyeti (₺)": vals["kiralar"][i], 
                "Fix Cost (m3 Başı)": vals["fix"]
            })
    
    pd.DataFrame(data_2025).to_csv(DB_FILE, index=False)

# İlk kurulum veya manuel güncelleme
if not os.path.exists(DB_FILE) or st.sidebar.button("🔄 Veritabanını Sayfa1 ile Senkronize Et"):
    initialize_database()
    st.sidebar.success("Tüm veriler Sayfa1'den çekildi!")

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
