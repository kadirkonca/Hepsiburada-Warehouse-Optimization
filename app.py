import streamlit as st
import pandas as pd
import pulp
import os
import json
from io import BytesIO

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hepsiburada Senaryo Merkezi", layout="wide")

DB_FILE = "shared_warehouse_data.csv"
SCENARIO_FILE = "scenarios.json"

initial_data = {
    "Depo Adı": ["Gebze Depo", "İzmir Torbalı Depo", "İzmir Pancar Depo", "Düzce Depo", "Bilecik Depo", "Adana Depo", "İzmir Pınarbaşı Depo"],
    "Kapasite (m3)": [19.301, 13.824, 3.365, 15.343, 22.000, 2.133, 4.694],
    "Kira Maliyeti (₺)": [10072.228, 3353.400, 2296.381, 2697.600, 3310.998, 0, 737.965],
    "Fix Cost (m3 Başı)": [185.19, 31.15, 277.30, 73.51, 55.12, 73.18, 48.03]
}

# --- FONKSİYONLAR ---
def load_scenarios():
    if os.path.exists(SCENARIO_FILE):
        with open(SCENARIO_FILE, "r") as f: return json.load(f)
    return {}

def save_scenarios(scs):
    with open(SCENARIO_FILE, "w") as f: json.dump(scs, f)

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

if "table_version" not in st.session_state: st.session_state["table_version"] = 0
scenarios = load_scenarios()

# --- SOL PANEL ---
st.sidebar.header("📂 Senaryo Arşivi")
if scenarios:
    for name in list(scenarios.keys()):
        with st.sidebar.expander(f"📍 {name}"):
            if st.button("📤 Yükle", key=f"load_{name}"):
                pd.DataFrame(scenarios[name]).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
            excel_data = to_excel(pd.DataFrame(scenarios[name]))
            st.sidebar.download_button(label="📥 İndir", data=excel_data, file_name=f"{name}.xlsx", key=f"dl_{name}")
            if st.sidebar.button("🗑️ Sil", key=f"del_{name}"):
                del scenarios[name]
                save_scenarios(scenarios)
                st.rerun()
else:
    st.sidebar.info("Kayıtlı senaryo yok.")

st.sidebar.markdown("---")
uploaded_file = st.sidebar.file_uploader("Excel/CSV Yükle", type=["csv", "xlsx"])

# --- ANA EKRAN ---
st.title("🚀 Hepsiburada Senaryo Merkezi")
if st.button("🚨 SİSTEMİ SIFIRLA"):
    reset_system()

if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(initial_data)

st.subheader("📊 Aktif Çalışma Tablosu")

# !!! KRİTİK DEĞİŞİKLİK: TABLO FORMATINI MANUEL ZORLUYORUZ !!!
column_config = {
    "Kapasite (m3)": st.column_config.NumberColumn(format="%d"),
    "Kira Maliyeti (₺)": st.column_config.NumberColumn(format="%d"),
    "Fix Cost (m3 Başı)": st.column_config.NumberColumn(format="%.2f"),
}

# data_editor içinde binlik ayraçları tarayıcı ayarlarından bağımsız zorlamak için locale ekledik
edited_df = st.data_editor(
    df, 
    use_container_width=True, 
    num_rows="dynamic", 
    column_config=column_config,
    key=f"editor_v{st.session_state['table_version']}"
)

st.markdown("### 💾 Senaryoyu Kaydet")
col_n, col_s, col_d = st.columns([2, 1, 1])
sc_name_input = col_n.text_input("Senaryo Adı:", key="sc_input")
if col_s.button("💾 Arşive Kaydet"):
    if sc_name_input:
        edited_df.to_csv(DB_FILE, index=False)
        scenarios[sc_name_input] = edited_df.to_dict(orient="list")
        save_scenarios(scenarios)
        st.rerun()

current_excel = to_excel(edited_df)
col_d.download_button(label="🧪 Excel İndir", data=current_excel, file_name="export.xlsx")

# --- OPTİMİZASYON ---
st.divider()
target_demand = st.number_input("Hedef Talep (m3)", value=35000)
if st.button("🚀 Optimizasyonu Çalıştır"):
    try:
        prob = pulp.LpProblem("Warehouse_Minimization", pulp.LpMinimize)
        depolar = edited_df["Depo Adı"].tolist()
        usage = pulp.LpVariable.dicts("m3", depolar, lowBound=0)
        
        prob += pulp.lpSum([(usage[d] * edited_df.loc[edited_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0]) + edited_df.loc[edited_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0] for d in depolar])
        prob += pulp.lpSum([usage[d] for d in depolar]) == target_demand
        for d in depolar:
            prob += usage[d] <= edited_df.loc[edited_df["Depo Adı"] == d, "Kapasite (m3)"].values[0]
            
        prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        if pulp.LpStatus[prob.status] == 'Optimal':
            cost_val = pulp.value(prob.objective)
            # BURASI KESİN NOKTALI GELECEK:
            cost_formatted = "{:,.0f}".format(cost_val).replace(",", ".")
            st.markdown(f"### 💰 Minimum Toplam Maliyet: **{cost_formatted} ₺**")
            
            res_df = pd.DataFrame([{"Depo": d, "Atanan": round(usage[d].varValue, 2)} for d in depolar])
            
            # Sonuç tablosunda binlik ayraç zorlaması
            st.write("**Dağılım Planı:**")
            st.dataframe(res_df.style.format({"Atanan": "{:,.2f}"}), use_container_width=True)
            st.bar_chart(res_df.set_index("Depo"))
    except Exception as e:
        st.error(f"Hata: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("Not: Veriler ortak sunucuda saklanır.")
