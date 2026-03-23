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
UPLOAD_HISTORY_FILE = "upload_history.json" # Yüklenen dosyalar için ayrı arşiv

initial_data = {
    "Depo Adı": ["Gebze Depo", "İzmir Torbalı Depo", "İzmir Pancar Depo", "Düzce Depo", "Bilecik Depo", "Adana Depo", "İzmir Pınarbaşı Depo"],
    "Kapasite (m3)": [19301, 13824, 3365, 15343, 22000, 2133, 4694],
    "Kira Maliyeti (₺)": [10072228, 3353400, 2296381, 2697600, 3310998, 0, 737965],
    "Fix Cost (m3 Başı)": [185.19, 31.15, 277.30, 73.51, 55.12, 73.18, 48.03]
}

# --- FONKSİYONLAR ---
def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_json(file_path, data):
    with open(file_path, "w") as f: json.dump(data, f)

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    return output.getvalue()

def reset_system():
    if os.path.exists(DB_FILE): os.remove(DB_FILE)
    st.cache_data.clear()
    st.session_state["table_version"] = st.session_state.get("table_version", 0) + 1
    st.rerun()

def format_and_center(val):
    try:
        formatted = "{:,.0f}".format(float(val)).replace(",", ".")
        return f"      {formatted}      "
    except: return val

def unformat_dots(val):
    if isinstance(val, str):
        clean_val = val.strip().replace(".", "").replace(",", "")
        return float(clean_val) if clean_val else 0.0
    return val

# --- VERİLERİ YÜKLE ---
if "table_version" not in st.session_state: st.session_state["table_version"] = 0
scenarios = load_json(SCENARIO_FILE)
uploads = load_json(UPLOAD_HISTORY_FILE)

# --- SOL PANEL (ARŞİV VE YÜKLEME) ---
st.sidebar.header("💾 Kaydedilen Senaryolar")
if scenarios:
    for name in list(scenarios.keys()):
        with st.sidebar.expander(f"📍 {name}"):
            if st.button("📤 Yükle", key=f"load_sc_{name}"):
                pd.DataFrame(scenarios[name]).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
            if st.sidebar.button("🗑️ Sil", key=f"del_sc_{name}"):
                del scenarios[name]
                save_json(SCENARIO_FILE, scenarios)
                st.rerun()
else:
    st.sidebar.info("Kayıtlı senaryo yok.")

st.sidebar.markdown("---")
st.sidebar.header("📂 Yüklenen Dosya Geçmişi")
if uploads:
    for name in list(uploads.keys()):
        with st.sidebar.expander(f"📄 {name}"):
            if st.button("📤 Yükle", key=f"load_up_{name}"):
                pd.DataFrame(uploads[name]).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
            if st.sidebar.button("🗑️ Sil", key=f"del_up_{name}"):
                del uploads[name]
                save_json(UPLOAD_HISTORY_FILE, uploads)
                st.rerun()
else:
    st.sidebar.info("Yükleme geçmişi temiz.")

st.sidebar.markdown("---")
st.sidebar.header("📤 Yeni Dosya Yükle")
uploaded_file = st.sidebar.file_uploader("Excel veya CSV", type=["csv", "xlsx"])

if uploaded_file:
    try:
        up_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        up_df.columns = [c.strip() for c in up_df.columns]
        # Yüklenen dosyayı anlık tabloya bas
        up_df.to_csv(DB_FILE, index=False)
        # Geçmişe otomatik eklemek için isim alalım
        file_name = uploaded_file.name
        uploads[file_name] = up_df.to_dict(orient="list")
        save_json(UPLOAD_HISTORY_FILE, uploads)
        st.session_state["table_version"] += 1
        st.sidebar.success(f"✅ {file_name} yüklendi ve geçmişe eklendi!")
    except Exception as e:
        st.sidebar.error(f"Hata: {e}")

# --- ANA EKRAN ---
st.title("🚀 Hepsiburada Senaryo Merkezi")
if st.button("🚨 SİSTEMİ SIFIRLA"):
    reset_system()

if os.path.exists(DB_FILE):
    df = pd.read_csv(DB_FILE)
else:
    df = pd.DataFrame(initial_data)

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

edited_df_display = st.data_editor(
    display_df, 
    use_container_width=True, 
    num_rows="dynamic",
    column_config=column_config,
    key=f"editor_v{st.session_state['table_version']}"
)

edited_df = edited_df_display.copy()
edited_df["Kapasite (m3)"] = edited_df["Kapasite (m3)"].apply(unformat_dots)
edited_df["Kira Maliyeti (₺)"] = edited_df["Kira Maliyeti (₺)"].apply(unformat_dots)

# --- KAYDETME ---
st.markdown("### 💾 Bu Tabloyu Senaryo Olarak Kaydet")
col_n, col_s, col_d = st.columns([2, 1, 1])
sc_name_input = col_n.text_input("Senaryo Adı:", key="sc_input")
if col_s.button("💾 Senaryolara Ekle", use_container_width=True):
    if sc_name_input:
        edited_df.to_csv(DB_FILE, index=False)
        scenarios[sc_name_input] = edited_df.to_dict(orient="list")
        save_json(SCENARIO_FILE, scenarios)
        st.success("Senaryo kaydedildi!")
        st.rerun()

current_excel = to_excel(edited_df)
col_d.download_button(label="🧪 Excel Olarak İndir", data=current_excel, file_name="hb_plan.xlsx", use_container_width=True)

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
            cost_formatted = "{:,.0f}".format(pulp.value(prob.objective)).replace(",", ".")
            st.markdown(f"### 💰 Minimum Toplam Maliyet: **{cost_formatted} ₺**")
            res_df = pd.DataFrame([{"Depo": d, "Atanan (m3)": round(usage[d].varValue, 2)} for d in depolar])
            st.dataframe(res_df.style.format({"Atanan (m3)": "{:,.2f}"}), use_container_width=True)
            st.bar_chart(res_df.set_index("Depo"))
    except Exception as e: st.error(f"Hata: {e}")

st.sidebar.markdown("---")
st.sidebar.caption("HB Depo Optimizasyon v2.5")
