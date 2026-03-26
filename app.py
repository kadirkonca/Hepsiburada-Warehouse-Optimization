import streamlit as st
import pandas as pd
import pulp
import os
import json
from io import BytesIO
from datetime import datetime

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hepsiburada Senaryo Merkezi", layout="wide")

# Session State Yönetimi (Tablo versiyonu ve hata engelleme)
if "table_version" not in st.session_state:
    st.session_state["table_version"] = 0

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

DB_FILE = "shared_warehouse_data.csv"
HISTORY_FILE = "all_scenarios_history.json" 

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
PERIYOT_LISTESI = AYLAR + ["Q1", "Q2", "Q3", "Q4", "H1", "H2", "FY (Full Year)"]
CEYREKLER = {"Q1": ["Ocak", "Şubat", "Mart"], "Q2": ["Nisan", "Mayıs", "Haziran"], "Q3": ["Temmuz", "Ağustos", "Eylül"], "Q4": ["Ekim", "Kasım", "Aralık"]}
ALTI_AYLIK = {"H1": ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran"], "H2": ["Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]}

# --- VERİTABANI BAŞLATMA (ASLA DEĞİŞMEYEN ANA VERİLER) ---
def initialize_database():
    data_2025 = []
    master_dict = {
        "Gebze Depo": {"Kira": [8042645, 8036840, 8042645, 7593418, 7593890, 7592002, 8433446, 11047457, 11283347, 10571543, 10569725, 10211732], "Fix": [252.26, 259.81, 305.68, 347.14, 347.05, 397.88, 415.28, 381.73, 384.95, 483.83, 516.54, 534.27], "Cap": 19301},
        "Tuzla Depo": {"Kira": [1039493, 1032553, 299927, 29171, 0, 0, 0, 0, 0, 2825521, 2864461, 3076245], "Fix": [0.0]*12, "Cap": 0},
        "İzmir Pancar Depo": {"Kira": [2300000, 2300000, 2300000, 2300000, 2300000, 3353400, 3353400, 3353400, 3353400, 3353400, 3353400, 3353400], "Fix": [366.76, 206.01, 270.75, 218.67, 328.01, 277.30, 427.95, 324.67, 392.61, 441.71, 564.93, 594.06], "Cap": 3365},
        "İzmir Pınarbaşı Depo": {"Kira": [516842, 516842, 795058, 795058, 795058, 795058, 795058, 795058, 795058, 795058, 795058, 795058], "Fix": [48.20, -64.90, 161.05, 86.61, 89.27, 96.07, 87.54, 106.25, 83.23, 95.77, 148.01, 171.98], "Cap": 4694},
        "İzmir Torbalı Depo": {"Kira": [2062500, 2062500, 1593750, 2062500, 2062500, 2062500, 2062500, 1811842, 2529693, 2529693, 2529693, 2879663], "Fix": [26.46, 26.36, 29.43, 32.22, 32.32, 33.77, 37.44, 37.39, 126.35, 33.95, 46.25, 64.78], "Cap": 13824},
        "Bilecik Depo": {"Kira": [2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2500000, 2979500, 3459000, 3459000], "Fix": [30.10, 52.75, 22.98, 36.24, 52.04, 61.29, 58.18, 59.49, 48.59, 65.48, 57.08, 72.96], "Cap": 22000},
        "Düzce Depo": {"Kira": [1004105, 2000000, 2000000, 2000000, 2000000, 2000000, 2000000, 2000000, 2000000, 2000000, 2000000, 3481485], "Fix": [56.63, 16.29, 39.38, 54.43, 73.24, 83.05, 73.75, 75.12, 59.49, 86.67, 193.32, 152.93], "Cap": 15343},
        "BF Ek Depo": {"Kira": [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1415293], "Fix": [0.0]*12, "Cap": 0},
        "Adana Depo": {"Kira": [153150, 193714, 193408, 193714, 171345, 190383, 190383, 498993, 595686, 0, 0, 0], "Fix": [283.29, 123.99, 70.35, 229.62, 211.84, 155.93, 167.98, -9.14, -36.18, 1.60, 3.01, 53.69], "Cap": 2133}
    }
    for depo, vals in master_dict.items():
        for i, ay in enumerate(AYLAR):
            data_2025.append({"Yıl": 2025, "Ay": ay, "Depo Adı": depo, "Kapasite (m3)": vals["Cap"], "Kira Maliyeti (₺)": vals["Kira"][i], "Fix Cost (m3 Başı)": vals["Fix"][i]})
    pd.DataFrame(data_2025).to_csv(DB_FILE, index=False)

if not os.path.exists(DB_FILE): initialize_database()

# --- YARDIMCI FONKSİYONLAR ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_history_all(history):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f: json.dump(history, f, ensure_ascii=False, indent=4)

def format_num(val):
    try: return f"{'{:,.0f}'.format(float(val)).replace(',', '.')}"
    except: return val

def unformat_num(val):
    if isinstance(val, str):
        val = val.strip().replace(".", "").replace(",", "")
        return float(val) if val else 0.0
    return float(val)

def get_excel_download(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='HB_Data')
    return output.getvalue()

full_history = load_history()

# --- SOL PANEL (ARŞİV VE EXCEL YÜKLEME - TÜM ÖZELLİKLER GERİ GELDİ) ---
st.sidebar.header("📜 Merkezi Senaryo Arşivi")
if full_history:
    for idx, entry in enumerate(full_history):
        with st.sidebar.expander(f"📍 {entry['isim']} | 👤 {entry.get('yukleyen', 'Bilinmiyor')}"):
            c1, c2 = st.columns(2)
            if c1.button("📤 Yükle", key=f"h_load_{idx}"):
                pd.DataFrame(entry['veri']).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
            if c2.button("🗑️ Sil", key=f"h_del_{idx}"):
                full_history.pop(idx); save_history_all(full_history); st.rerun()
else: st.sidebar.info("Arşiv boş.")

st.sidebar.markdown("---")
st.sidebar.header("📤 Dışarıdan Veri Yükle")
up_user = st.sidebar.text_input("Ad Soyad:", key="up_user")
up_label = st.sidebar.text_input("Senaryo Adı:", key="up_label")
uploaded_file = st.sidebar.file_uploader("Dosya Seç (Excel/CSV)", type=["csv", "xlsx"])
if uploaded_file and up_user and up_label:
    if st.sidebar.button("✅ Arşive ve Tabloya İşle"):
        up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        up_df.to_csv(DB_FILE, index=False)
        new_entry = {"tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "isim": up_label, "yukleyen": up_user, "veri": up_df.to_dict(orient="list")}
        full_history.insert(0, new_entry); save_history_all(full_history)
        st.session_state["table_version"] += 1; st.rerun()

# --- ANA EKRAN ---
st.title("🚀 Hepsiburada Stratejik Planlama Merkezi")
main_df = pd.read_csv(DB_FILE)

# Filtreler
f_col1, f_col2, f_col3 = st.columns(3)
with f_col1: selected_period = st.selectbox("⏱️ Periyot Seçin:", options=PERIYOT_LISTESI, index=0)
with f_col2: sort_opt = st.selectbox("🔃 Sırala:", options=["Depo Adı", "Kapasite", "Kira"])

filter_months = [selected_period] if selected_period in AYLAR else (CEYREKLER.get(selected_period) or ALTI_AYLIK.get(selected_period) or AYLAR)
f_df = main_df[main_df["Ay"].isin(filter_months)]

if len(filter_months) > 1:
    display_df = f_df.groupby("Depo Adı").agg({"Kapasite (m3)": "sum", "Kira Maliyeti (₺)": "sum", "Fix Cost (m3 Başı)": "mean"}).reset_index()
else:
    display_df = f_df.drop(columns=["Yıl", "Ay"])

# --- TABLO ÜSTÜ KONTROLLER ---
st.divider()
c_tab1, c_tab2, c_tab3 = st.columns([2, 1, 1])
with c_tab1:
    st.subheader(f"📊 {selected_period} Tablosu")
with c_tab2:
    if st.button("🔄 Verileri Sıfırla", use_container_width=True):
        initialize_database()
        st.session_state["table_version"] += 1
        st.rerun()
with c_tab3:
    st.download_button(
        label="📥 Excel Olarak İndir",
        data=get_excel_download(display_df),
        file_name=f"HB_Data_{selected_period}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

# Veri Formatlama
v_df = display_df.copy()
v_df["Kapasite (m3)"] = v_df["Kapasite (m3)"].apply(format_num)
v_df["Kira Maliyeti (₺)"] = v_df["Kira Maliyeti (₺)"].apply(format_num)

column_config = {
    "Depo Adı": st.column_config.TextColumn("Depo Adı", width="medium"),
    "Kapasite (m3)": st.column_config.TextColumn("Kapasite (m3)"),
    "Kira Maliyeti (₺)": st.column_config.TextColumn("Kira Maliyeti (₺)"),
    "Fix Cost (m3 Başı)": st.column_config.NumberColumn("Fix Cost (m3 Başı)", format="%.2f")
}

edited_df = st.data_editor(v_df, use_container_width=True, num_rows="dynamic", column_config=column_config, key=f"editor_{selected_period}_{st.session_state['table_version']}")

# --- OPTİMİZASYON ---
st.divider()
st.markdown("### 🎯 Akıllı Operasyon Optimizasyonu")
opt_prep = edited_df.copy()
opt_prep["Kapasite (m3)"] = opt_prep["Kapasite (m3)"].apply(unformat_num)
max_cap = opt_prep["Kapasite (m3)"].sum()

c_opt1, c_opt2 = st.columns([2, 1])
with c_opt1:
    target = st.number_input("📥 Hedef Sevkiyat Talebi (m3)", value=min(35000.0, max_cap))
with c_opt2:
    st.markdown(f"<p style='margin-top: 32px; color: #FF6000; font-weight: bold;'>⚠️ Maks. Kapasite: {format_num(max_cap)} m3</p>", unsafe_allow_html=True)

if st.button("🚀 Optimizasyonu Başlat", use_container_width=True):
    if target > max_cap: st.error("Kapasite yetersiz!")
    else:
        try:
            opt_final = edited_df.copy()
            opt_final["Kapasite (m3)"] = opt_final["Kapasite (m3)"].apply(unformat_num)
            opt_final["Kira Maliyeti (₺)"] = opt_final["Kira Maliyeti (₺)"].apply(unformat_num)
            valid_df = opt_final[opt_final["Kapasite (m3)"] > 0].copy()
            prob = pulp.LpProblem("WH_Min", pulp.LpMinimize)
            usage = pulp.LpVariable.dicts("m3", valid_df["Depo Adı"], lowBound=0)
            prob += pulp.lpSum([(usage[d] * float(valid_df.loc[valid_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0])) + float(valid_df.loc[valid_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0]) for d in valid_df["Depo Adı"]])
            prob += pulp.lpSum([usage[d] for d in opt_df_valid["Depo Adı"]]) == target # Düzeltildi
            # Düzeltme: usage[d] döngüsü valid_df üzerinden olmalı
            prob = pulp.LpProblem("WH_Min", pulp.LpMinimize)
            usage = pulp.LpVariable.dicts("m", valid_df["Depo Adı"], lowBound=0)
            prob += pulp.lpSum([(usage[d] * float(valid_df.loc[valid_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0])) + float(valid_df.loc[valid_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0]) for d in valid_df["Depo Adı"]])
            prob += pulp.lpSum([usage[d] for d in valid_df["Depo Adı"]]) == target
            for d in valid_df["Depo Adı"]: prob += usage[d] <= float(valid_df.loc[valid_df["Depo Adı"] == d, "Kapasite (m3)"].values[0])
            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.success(f"Maliyet: {format_num(pulp.value(prob.objective))} ₺")
                res = []
                for d in valid_df["Depo Adı"]:
                    atanan = usage[d].varValue
                    kap = float(valid_df.loc[valid_df["Depo Adı"] == d, "Kapasite (m3)"].values[0])
                    res.append({"Depo": d, "Atanan (m3)": format_num(atanan), "Doluluk (%)": f"% {(atanan/kap)*100:.1f}" if kap > 0 else "0", "Durum": "❌ Atıl" if atanan <= 0.1 else "✅ Kullanımda"})
                st.dataframe(pd.DataFrame(res), use_container_width=True)
        except Exception as e: st.error(f"Hata: {e}")

# --- KAYDETME ---
st.divider()
st.markdown("### 💾 Bu Çalışmayı Kaydet")
c1, c2, c3 = st.columns([1,1,1])
s_user = c1.text_input("👤 Kaydeden:", placeholder="Kadir Konca")
s_name = c2.text_input("📝 Senaryo Adı:", placeholder="Plan_v1")
if c3.button("💾 Arşive Yeni Kayıt Ekle", use_container_width=True):
    if s_user and s_name:
        sdf = edited_df.copy()
        sdf["Kapasite (m3)"] = sdf["Kapasite (m3)"].apply(unformat_num)
        sdf["Kira Maliyeti (₺)"] = sdf["Kira Maliyeti (₺)"].apply(unformat_num)
        new_entry = {"tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "isim": s_name, "yukleyen": s_user, "veri": sdf.to_dict(orient="list")}
        full_history.insert(0, new_entry); save_history_all(full_history); st.success("Arşivlendi!"); st.rerun()
