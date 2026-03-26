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

DB_FILE = "shared_warehouse_data.csv"
HISTORY_FILE = "all_scenarios_history.json" 

AYLAR = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
PERIYOT_LISTESI = AYLAR + ["--- Çeyrekler ---", "Q1", "Q2", "Q3", "Q4", "--- Yarı Yıllar ---", "H1", "H2", "--- Yıl Sonu ---", "FY (Full Year)"]

# --- VERİTABANI BAŞLATMA ---
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
    if isinstance(val, str): return float(val.strip().replace(".", "").replace(",", ""))
    return val

# --- GERÇEK EXCEL EXPORT (HÜCRE BAZLI) ---
def get_excel_download(df):
    output = BytesIO()
    # Excel motoru olarak xlsxwriter veya openpyxl kullanıyoruz
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Veriler')
    return output.getvalue()

full_history = load_history()

# --- SOL PANEL ---
st.sidebar.header("📜 Merkezi Senaryo Arşivi")
if full_history:
    for idx, entry in enumerate(full_history):
        with st.sidebar.expander(f"📍 {entry['isim']} | 👤 {entry.get('yukleyen', 'Bilinmiyor')}"):
            c1, c2 = st.columns(2)
            if c1.button("📤 Yükle", key=f"h_load_{idx}"):
                pd.DataFrame(entry['veri']).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] = st.session_state.get("table_version", 0) + 1
                st.rerun()
            if c2.button("🗑️ Sil", key=f"h_del_{idx}"):
                full_history.pop(idx); save_history_all(full_history); st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📤 Veri Yükle (Excel/CSV)")
up_user = st.sidebar.text_input("Ad Soyad:", key="up_user")
up_label = st.sidebar.text_input("Senaryo Adı:", key="up_label")
uploaded_file = st.sidebar.file_uploader("Dosya Seç", type=["csv", "xlsx"])
if uploaded_file and up_user and up_label:
    if st.sidebar.button("✅ Arşive ve Tabloya İşle"):
        up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        up_df.to_csv(DB_FILE, index=False)
        new_entry = {"tarih": datetime.now().strftime("%d.%m.%Y %H:%M"), "isim": up_label, "yukleyen": up_user, "veri": up_df.to_dict(orient="list")}
        full_history.insert(0, new_entry); save_history_all(full_history)
        st.session_state["table_version"] = st.session_state.get("table_version", 0) + 1; st.rerun()

# --- ANA EKRAN ---
st.title("🚀 Hepsiburada Stratejik Planlama Merkezi")
main_df = pd.read_csv(DB_FILE)

# Filtreler
f_col1, f_col2 = st.columns(2)
with f_col1: selected_period = st.selectbox("⏱️ Periyot Seçin:", options=PERIYOT_LISTESI)
with f_col2: sort_option = st.selectbox("🔃 Sırala:", options=["Depo Adı (A-Z)", "Kapasite (Yüksek->Düşük)", "Kira (Yüksek->Düşük)"])

filter_months = [selected_period] if selected_period in AYLAR else AYLAR # Basitleştirilmiş filtre

filtered_df = main_df[main_df["Ay"].isin(filter_months)]
if len(filter_months) > 1:
    display_df = filtered_df.groupby("Depo Adı").agg({"Kapasite (m3)": "sum", "Kira Maliyeti (₺)": "sum", "Fix Cost (m3 Başı)": "mean"}).reset_index()
else:
    display_df = filtered_df.drop(columns=["Yıl", "Ay"])

# Tablo Görünümü
view_df = display_df.copy()
view_df["Kapasite (m3)"] = view_df["Kapasite (m3)"].apply(format_num)
view_df["Kira Maliyeti (₺)"] = view_df["Kira Maliyeti (₺)"].apply(format_num)

st.subheader(f"📊 Mevcut Veri Tablosu ({selected_period})")
edited_df_display = st.data_editor(view_df, use_container_width=True, key=f"ed_{selected_period}")

# --- KRİTİK DÜZELTME: EXCEL İNDİRME BUTONU ---
excel_data = get_excel_download(display_df)
st.download_button(
    label="📥 Mevcut Tabloyu EXCEL (Hücre Bazlı) Olarak İndir",
    data=excel_data,
    file_name=f"HB_Tablo_{selected_period}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)

# --- OPTİMİZASYON ---
st.divider()
st.markdown("### 🎯 Akıllı Operasyon Optimizasyonu")
temp_opt_df = edited_df_display.copy()
temp_opt_df["Kapasite (m3)"] = temp_opt_df["Kapasite (m3)"].apply(unformat_num)
max_cap = temp_opt_df["Kapasite (m3)"].sum()

c_opt1, c_opt2 = st.columns([2, 1])
with c_opt1: target_demand = st.number_input("📥 Hedeflenen Sevkiyat Talebi (m3)", value=min(35000.0, max_cap))
with c_opt2: st.markdown(f"<p style='margin-top: 32px; color: #FF6000; font-weight: bold;'>⚠️ Maks. Kapasite: {'{:,.0f}'.format(max_cap).replace(',', '.')} m3</p>", unsafe_allow_html=True)

if st.button("🚀 Optimizasyonu Başlat", use_container_width=True):
    if target_demand > max_cap: st.error("Kapasite yetersiz!")
    else:
        try:
            opt_df = edited_df_display.copy()
            opt_df["Kapasite (m3)"] = opt_df["Kapasite (m3)"].apply(unformat_num)
            opt_df["Kira Maliyeti (₺)"] = opt_df["Kira Maliyeti (₺)"].apply(unformat_num)
            opt_df_valid = opt_df[opt_df["Kapasite (m3)"] > 0].copy()
            
            prob = pulp.LpProblem("WH_Min", pulp.LpMinimize)
            usage = pulp.LpVariable.dicts("m3", opt_df_valid["Depo Adı"], lowBound=0)
            prob += pulp.lpSum([(usage[d] * float(opt_df_valid.loc[opt_df_valid["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0])) + float(opt_df_valid.loc[opt_df_valid["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0]) for d in opt_df_valid["Depo Adı"]])
            prob += pulp.lpSum([usage[d] for d in opt_df_valid["Depo Adı"]]) == target_demand
            for d in opt_df_valid["Depo Adı"]: prob += usage[d] <= float(opt_df_valid.loc[opt_df_valid["Depo Adı"] == d, "Kapasite (m3)"].values[0])
            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.success(f"✅ Başarılı! Toplam Maliyet: {'{:,.0f}'.format(pulp.value(prob.objective)).replace(',', '.')} ₺")
                res_data = []
                for d in opt_df_valid["Depo Adı"]:
                    atanan = usage[d].varValue
                    kapasite = float(opt_df_valid.loc[opt_df_valid["Depo Adı"] == d, "Kapasite (m3)"].values[0])
                    doluluk = (atanan / kapasite) * 100 if kapasite > 0 else 0
                    durum = "❌ Atıl (Kapat)" if atanan <= 0.1 else ("✅ Tam Dolu" if doluluk >= 99.9 else "⚠️ Kısmi Kullanım")
                    res_data.append({"Depo": d, "Atanan (m3)": round(atanan, 0), "Doluluk (%)": f"%{doluluk:.1f}", "Durum": durum})
                
                res_df = pd.DataFrame(res_data)
                st.dataframe(res_df, use_container_width=True)
                
                # Optimizasyon Sonucu İndirme
                st.download_button(
                    label="📥 Optimizasyon Sonucunu EXCEL Olarak İndir",
                    data=get_excel_download(res_df),
                    file_name=f"HB_Optimizasyon_{selected_period}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
        except Exception as e: st.error(f"Hata: {e}")
