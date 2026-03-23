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

initial_data = {
    "Depo Adı": ["Gebze Depo", "İzmir Torbalı Depo", "İzmir Pancar Depo", "Düzce Depo", "Bilecik Depo", "Adana Depo", "İzmir Pınarbaşı Depo"],
    "Kapasite (m3)": [19301, 13824, 3365, 15343, 22000, 2133, 4694],
    "Kira Maliyeti (₺)": [10072228, 3353400, 2296381, 2697600, 3310998, 0, 737965],
    "Fix Cost (m3 Başı)": [185.19, 31.15, 277.30, 73.51, 55.12, 73.18, 48.03]
}

# --- FONKSİYONLAR ---
def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f: return json.load(f)
        except: return []
    return []

def save_to_history(new_entry):
    history = load_history()
    history.insert(0, new_entry) 
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=4)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

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

# --- SOL PANEL (ARŞİV) ---
st.sidebar.header("📜 Merkezi Senaryo Arşivi")
if full_history:
    for idx, entry in enumerate(full_history):
        # Başlıkta artık yükleyen kişi de görünüyor
        with st.sidebar.expander(f"📍 {entry['isim']} | 👤 {entry.get('yukleyen', 'Bilinmiyor')}"):
            st.caption(f"📅 {entry['tarih']} - {entry['tip']}")
            if st.button("📤 Tabloya Yükle", key=f"h_load_{idx}"):
                pd.DataFrame(entry['veri']).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
            st.download_button("📥 Excel İndir", to_excel(pd.DataFrame(entry['veri'])), f"{entry['isim']}.xlsx", key=f"h_dl_{idx}")
else:
    st.sidebar.info("Arşiv henüz boş.")

st.sidebar.markdown("---")

# --- YENİ DOSYA YÜKLEME BÖLÜMÜ (İSİM ZORUNLULUĞU) ---
st.sidebar.header("📤 Dışarıdan Veri Yükle")
up_user = st.sidebar.text_input("Adınız Soyadınız:", key="up_user_name", placeholder="Örn: Kadir Konca")
up_file_custom_name = st.sidebar.text_input("Dosya Takma Adı:", key="up_file_name", placeholder="Örn: 2024 Mart Verileri")
uploaded_file = st.sidebar.file_uploader("Excel veya CSV Seçin", type=["csv", "xlsx"])

if uploaded_file:
    if not up_user or not up_file_custom_name:
        st.sidebar.error("⚠️ Lütfen önce adınızı ve dosya adını girin!")
    else:
        if st.sidebar.button("✅ Arşive ve Tabloya İşle"):
            try:
                up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
                up_df.to_csv(DB_FILE, index=False)
                
                new_upload = {
                    "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
                    "isim": up_file_custom_name,
                    "yukleyen": up_user,
                    "tip": "Dışarıdan Yükleme",
                    "veri": up_df.to_dict(orient="list")
                }
                save_to_history(new_upload)
                st.session_state["table_version"] += 1
                st.sidebar.success("Kayıt başarıyla oluşturuldu!")
                st.rerun()
            except Exception as e: st.sidebar.error(f"Hata: {e}")

# --- ANA EKRAN ---
st.title("🚀 Hepsiburada Senaryo Merkezi")

if st.button("🚨 TABLOYU SIFIRLA"):
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.rerun()

df = pd.read_csv(DB_FILE) if os.path.exists(DB_FILE) else pd.DataFrame(initial_data)

st.subheader("📊 Aktif Çalışma Tablosu")
display_df = df.copy()
display_df["Kapasite (m3)"] = display_df["Kapasite (m3)"].apply(format_and_center)
display_df["Kira Maliyeti (₺)"] = display_df["Kira Maliyeti (₺)"].apply(format_and_center)

column_config = {
    "Depo Adı": st.column_config.TextColumn("Depo Adı", width="medium"),
    "Kapasite (m3)": st.column_config.TextColumn("Kapasite (m3)"),
    "Kira Maliyeti (₺)": st.column_config.TextColumn("Kira Maliyeti (₺)"),
    "Fix Cost (m3 Başı)": st.column_config.NumberColumn("Fix Cost (m3 Başı)", format="%.2f"),
}

edited_df_display = st.data_editor(display_df, use_container_width=True, num_rows="dynamic", column_config=column_config, key=f"ed_v{st.session_state['table_version']}")

edited_df = edited_df_display.copy()
edited_df["Kapasite (m3)"] = edited_df["Kapasite (m3)"].apply(unformat_dots)
edited_df["Kira Maliyeti (₺)"] = edited_df["Kira Maliyeti (₺)"].apply(unformat_dots)

# --- SENARYO KAYDETME (İSİM ZORUNLULUĞU) ---
st.markdown("### 💾 Bu Çalışmayı Yeni Senaryo Olarak Arşivle")
c1, c2, c3 = st.columns([1, 1, 1])
save_user = c1.text_input("Yükleyen Kişi:", placeholder="Adınız Soyadınız")
save_name = c2.text_input("Senaryo Dosya Adı:", placeholder="Örn: Bayram_Planı_v1")

if c3.button("💾 Arşive Kaydet", use_container_width=True):
    if not save_user or not save_name:
        st.error("⚠️ Kaydetmek için hem isminizi hem de senaryo adını girmelisiniz!")
    else:
        new_entry = {
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "isim": save_name,
            "yukleyen": save_user,
            "tip": "Manuel Kayıt",
            "veri": edited_df.to_dict(orient="list")
        }
        save_to_history(new_entry)
        st.success(f"Senaryo '{save_user}' tarafından başarıyla kaydedildi!")
        st.rerun()

# --- OPTİMİZASYON ---
st.divider()
target_demand = st.number_input("Hedeflenen Toplam Sevkiyat Talebi (m3)", value=35000)
if st.button("🚀 Optimizasyonu Çalıştır", use_container_width=True):
    try:
        prob = pulp.LpProblem("Warehouse_Minimization", pulp.LpMinimize)
        depolar = edited_df["Depo Adı"].tolist()
        usage = pulp.LpVariable.dicts("m3", depolar, lowBound=0)
        prob += pulp.lpSum([(usage[d] * float(edited_df.loc[edited_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0])) + float(edited_df.loc[edited_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0]) for d in depolar])
        prob += pulp.lpSum([usage[d] for d in depolar]) == target_demand
        for d in depolar:
            prob += usage[d] <= float(edited_df.loc[edited_df["Depo Adı"] == d, "Kapasite (m3)"].values[0])
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        if pulp.LpStatus[prob.status] == 'Optimal':
            cost_f = "{:,.0f}".format(pulp.value(prob.objective)).replace(",", ".")
            st.markdown(f"### 💰 Minimum Toplam Maliyet: **{cost_f} ₺**")
            res_df = pd.DataFrame([{"Depo": d, "Atanan (m3)": round(usage[d].varValue, 2)} for d in depolar])
            st.dataframe(res_df.style.format({"Atanan (m3)": "{:,.2f}"}), use_container_width=True)
            st.bar_chart(res_df.set_index("Depo"))
    except Exception as e: st.error(f"Hata: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("v3.0 - Kimlikli Arşiv Sistemi")
