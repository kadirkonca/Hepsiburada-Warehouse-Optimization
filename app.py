import streamlit as st
import pandas as pd
import pulp
import os
import json

# 1. SAYFA VE DOSYA YAPILANDIRMASI
st.set_page_config(page_title="Hepsiburada Senaryo Merkezi", layout="wide")

# Veri dosyaları
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

def save_scenarios(scenarios):
    with open(SCENARIO_FILE, "w") as f:
        json.dump(scenarios, f)

def reset_system():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.cache_data.clear()
    st.session_state["table_version"] = st.session_state.get("table_version", 0) + 1
    st.rerun()

# --- SESSION STATE BAŞLATMA ---
if "table_version" not in st.session_state: st.session_state["table_version"] = 0
scenarios = load_scenarios()

# --- SOL PANEL (SENARYO YÖNETİMİ) ---
st.sidebar.header("📂 Senaryo Kayıtları")

if scenarios:
    for name in list(scenarios.keys()):
        with st.sidebar.expander(f"📍 {name}"):
            col_s1, col_s2 = st.columns(2)
            if col_s1.button("Yükle", key=f"load_{name}"):
                pd.DataFrame(scenarios[name]).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
            if col_s2.button("Sil", key=f"del_{name}"):
                del scenarios[name]
                save_scenarios(scenarios)
                st.rerun()
else:
    st.sidebar.info("Henüz kayıtlı senaryo yok.")

st.sidebar.markdown("---")
st.sidebar.header("📤 Yeni Excel/Veri Yükle")
uploaded_file = st.sidebar.file_uploader("Dosya Seç", type=["csv", "xlsx"])

# --- ANA EKRAN ---
st.title("🚀 Hepsiburada Ortak Planlama Sistemi")

col_title, col_reset = st.columns([4, 1])
with col_reset:
    if st.button("🚨 SİSTEMİ SIFIRLA", use_container_width=True):
        reset_system()

# Veriyi yükle
if os.path.exists(DB_FILE):
    current_df = pd.read_csv(DB_FILE)
else:
    current_df = pd.DataFrame(initial_data)

# Tablo Düzenleme
st.subheader("📊 Depo Parametreleri")
edited_df = st.data_editor(
    current_df, 
    use_container_width=True, 
    num_rows="dynamic", 
    key=f"editor_v{st.session_state['table_version']}"
)

# --- KAYDETME ALANI ---
st.markdown("### 💾 Değişiklikleri Kaydet")
col_name, col_btn = st.columns([3, 1])
scenario_name = col_name.text_input("Senaryo İsmi (Örn: 2026 Q1 Planı)", placeholder="İsim giriniz...")

if col_btn.button("💾 Senaryoyu Arşive Ekle", use_container_width=True):
    if scenario_name:
        # Hem ortak dosyaya yaz hem de senaryolara ekle
        edited_df.to_csv(DB_FILE, index=False)
        scenarios[scenario_name] = edited_df.to_dict(orient="list")
        save_scenarios(scenarios)
        st.success(f"'{scenario_name}' başarıyla kaydedildi!")
        st.rerun()
    else:
        st.warning("Lütfen kaydetmeden önce bir isim girin!")

# Excel Yükleme Mantığı (İsim sorma için)
if uploaded_file:
    st.sidebar.warning("Yüklenen dosya için aşağıya isim girip kaydedin!")
    if scenario_name:
        try:
            up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
            up_df.to_csv(DB_FILE, index=False)
            scenarios[scenario_name] = up_df.to_dict(orient="list")
            save_scenarios(scenarios)
            st.rerun()
        except: st.error("Dosya okunamadı.")

# --- OPTİMİZASYON HESAPLAMA (AYNI KALDI) ---
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
        st.success(f"Minimum Maliyet: {pulp.value(prob.objective):,.2f} ₺")
        res_df = pd.DataFrame([{"Depo": d, "m3": round(usage[d].varValue, 2)} for d in depolar])
        st.dataframe(res_df, use_container_width=True)
        st.bar_chart(res_df.set_index("Depo"))
