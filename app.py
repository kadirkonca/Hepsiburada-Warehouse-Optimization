import streamlit as st
import pandas as pd
import pulp
import os
import json
from io import BytesIO

# 1. SAYFA VE DOSYA AYARLARI
st.set_page_config(page_title="Hepsiburada Senaryo Merkezi v2", layout="wide")

DB_FILE = "shared_warehouse_data.csv"
SCENARIO_FILE = "scenarios.json"

# FABRİKA AYARLARI
initial_data = {
    "Depo Adı": ["Gebze Depo", "İzmir Torbalı Depo", "İzmir Pancar Depo", "Düzce Depo", "Bilecik Depo", "Adana Depo", "İzmir Pınarbaşı Depo"],
    "Kapasite (m3)": [19301, 13824, 3365, 15343, 22000, 2133, 4694],
    "Kira Maliyeti (₺)": [10072228, 3353400, 2296381, 2697600, 3310998, 0, 737965],
    "Fix Cost (m3 Başı)": [185.19, 31.15, 277.30, 73.51, 55.12, 73.18, 48.03]
}

# --- FONKSİYONLAR ---
def load_scenarios():
    if os.path.exists(SCENARIO_FILE):
        with open(SCENARIO_FILE, "r") as f:
            return json.load(f)
    return {}

def save_scenarios(scs):
    with open(SCENARIO_FILE, "w") as f:
        json.dump(scs, f)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='DepoVerileri')
    return output.getvalue()

def reset_system():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.cache_data.clear()
    st.session_state["table_version"] = st.session_state.get("table_version", 0) + 1
    st.rerun()

# --- INITIALIZE ---
if "table_version" not in st.session_state: st.session_state["table_version"] = 0
scenarios = load_scenarios()

# --- SOL PANEL (SENARYO YÖNETİMİ) ---
st.sidebar.header("📂 Senaryo Arşivi")

if scenarios:
    for name in list(scenarios.keys()):
        with st.sidebar.expander(f"📍 {name}"):
            col_a, col_b = st.columns(2)
            
            if col_a.button("📤 Yükle", key=f"load_{name}"):
                pd.DataFrame(scenarios[name]).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
            
            excel_data = to_excel(pd.DataFrame(scenarios[name]))
            col_b.download_button(
                label="📥 İndir",
                data=excel_data,
                file_name=f"{name}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key=f"dl_{name}"
            )
            
            new_name = st.text_input("Yeni İsim:", value=name, key=f"rename_input_{name}")
            if st.button("✏️ Adı Güncelle", key=f"rename_btn_{name}"):
                if new_name and new_name != name:
                    scenarios[new_name] = scenarios.pop(name)
                    save_scenarios(scenarios)
                    st.rerun()
            
            if st.button("🗑️ Bu Senaryoyu Sil", key=f"del_{name}", use_container_width=True):
                del scenarios[name]
                save_scenarios(scenarios)
                st.rerun()
else:
    st.sidebar.info("Kayıtlı senaryo bulunamadı.")

st.sidebar.markdown("---")
st.sidebar.header("📤 Dışarıdan Veri Ekle")
uploaded_file = st.sidebar.file_uploader("Excel veya CSV Yükle", type=["csv", "xlsx"])

# --- ANA EKRAN ---
st.title("🚀 Hepsiburada Senaryo ve Optimizasyon Merkezi")

col_title, col_reset = st.columns([4, 1])
with col_reset:
    if st.button("🚨 SİSTEMİ SIFIRLA", use_container_width=True):
        reset_system()

# Mevcut veriyi belirle
if os.path.exists(DB_FILE):
    current_df = pd.read_csv(DB_FILE)
else:
    current_df = pd.DataFrame(initial_data)

# --- TABLO (GÖRSEL FORMATLAMA EKLENDİ) ---
st.subheader("📊 Aktif Çalışma Tablosu")

# Sütun bazlı formatlama ayarları
column_config = {
    "Kapasite (m3)": st.column_config.NumberColumn(format="%d"),
    "Kira Maliyeti (₺)": st.column_config.NumberColumn(format="%d"),
    "Fix Cost (m3 Başı)": st.column_config.NumberColumn(format="%.2f"),
}

edited_df = st.data_editor(
    current_df, 
    use_container_width=True, 
    num_rows="dynamic", 
    column_config=column_config,
    key=f"editor_v{st.session_state['table_version']}"
)

# --- KAYDETME VE DIŞA AKTARMA ---
st.markdown("### 💾 Senaryoyu Kaydet")
col_n, col_s, col_d = st.columns([2, 1, 1])
sc_name_input = col_n.text_input("Senaryo Adı:", placeholder="Örn: Bayram Kampanyası 2026")

if col_s.button("💾 Arşive Kaydet", use_container_width=True):
    if sc_name_input:
        edited_df.to_csv(DB_FILE, index=False)
        scenarios[sc_name_input] = edited_df.to_dict(orient="list")
        save_scenarios(scenarios)
        st.success(f"'{sc_name_input}' kaydedildi!")
        st.rerun()
    else:
        st.warning("İsim giriniz!")

current_excel = to_excel(edited_df)
col_d.download_button(
    label="🧪 Mevcut Tabloyu Excel İndir",
    data=current_excel,
    file_name="hepsiburada_depo_export.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    use_container_width=True
)

if uploaded_file:
    st.sidebar.warning("Yüklenen dosyayı kaydetmek için aşağıya isim yazıp Arşive Kaydet'e basın!")
    try:
        if uploaded_file.name.endswith('.csv'):
            up_df = pd.read_csv(uploaded_file)
        else:
            up_df = pd.read_excel(uploaded_file)
        up_df.to_csv(DB_FILE, index=False)
        st.session_state["table_version"] += 1
    except: st.error("Dosya okuma hatası!")

# --- OPTİMİZASYON ---
st.divider()
target_demand = st.number_input("Hedeflenen Toplam Sevkiyat Talebi (m3)", min_value=0, value=35000)
if st.button("🚀 Optimizasyonu Çalıştır", use_container_width=True):
    prob = pulp.LpProblem("Warehouse_Minimization", pulp.LpMinimize)
    depolar = edited_df["Depo Adı"].tolist()
    usage = pulp.LpVariable.dicts("m3_Usage", depolar, lowBound=0)
    
    prob += pulp.lpSum([(usage[d] * edited_df.loc[edited_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0]) + edited_df.loc[edited_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0] for d in depolar])
    prob += pulp.lpSum([usage[d] for d in depolar]) == target_demand
    for d in depolar:
        prob += usage[d] <= edited_df.loc[edited_df["Depo Adı"] == d, "Kapasite (m3)"].values[0]
    
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    if pulp.LpStatus[prob.status] == 'Optimal':
        # Sonuç maliyeti de binlik ayraçlı gösterelim
        total_cost_val = pulp.value(prob.objective)
        st.success(f"💰 Minimum Toplam Maliyet: {total_cost_val:,.0f} ₺".replace(",", "."))
        res_df = pd.DataFrame([{"Depo": d, "Atanan (m3)": round(usage[d].varValue, 2)} for d in depolar])
        st.dataframe(res_df, use_container_width=True)
        st.bar_chart(res_df.set_index("Depo"))
