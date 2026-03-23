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

def save_history_all(history):
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
    # Silme işlemi için listenin kopyası üzerinden döneceğiz
    new_history_list = full_history.copy()
    for idx, entry in enumerate(full_history):
        with st.sidebar.expander(f"📍 {entry['isim']} | 👤 {entry.get('yukleyen', 'Bilinmiyor')}"):
            st.caption(f"📅 {entry['tarih']} - {entry['tip']}")
            
            col_load, col_dl, col_del = st.columns([1, 1, 1])
            
            if col_load.button("📤 Yükle", key=f"h_load_{idx}"):
                pd.DataFrame(entry['veri']).to_csv(DB_FILE, index=False)
                st.session_state["table_version"] += 1
                st.rerun()
                
            col_dl.download_button("📥 İndir", to_excel(pd.DataFrame(entry['veri'])), f"{entry['isim']}.xlsx", key=f"h_dl_{idx}")
            
            if col_del.button("🗑️ Sil", key=f"h_del_{idx}"):
                # Arşivden ilgili kaydı çıkar
                new_history_list.pop(idx)
                save_history_all(new_history_list)
                st.sidebar.success(f"'{entry['isim']}' arşivden silindi.")
                st.rerun()
else:
    st.sidebar.info("Arşiv henüz boş.")

st.sidebar.markdown("---")

# --- YENİ DOSYA YÜKLEME (İSİM KONTROLÜ) ---
st.sidebar.header("📤 Dışarıdan Veri Yükle")
up_user = st.sidebar.text_input("Adınız Soyadınız:", key="up_user_name", placeholder="Kadir Konca")
up_file_custom_name = st.sidebar.text_input("Dosya Takma Adı:", key="up_file_name", placeholder="2024 Mart")
uploaded_file = st.sidebar.file_uploader("Excel veya CSV Seçin", type=["csv", "xlsx"])

if uploaded_file:
    # İsimlerin benzersiz olup olmadığını kontrol et
    existing_names = [e['isim'] for e in full_history]
    
    if not up_user or not up_file_custom_name:
        st.sidebar.error("⚠️ Adınızı ve dosya adını girin!")
    elif up_file_custom_name in existing_names:
        st.sidebar.error(f"⚠️ '{up_file_custom_name}' adında bir senaryo zaten var!")
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
                full_history.insert(0, new_upload)
                save_history_all(full_history)
                st.session_state["table_version"] += 1
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

# --- SENARYO KAYDETME (İSİM KONTROLÜ) ---
st.markdown("### 💾 Bu Çalışmayı Yeni Senaryo Olarak Arşivle")
c1, c2, c3 = st.columns([1, 1, 1])
save_user = c1.text_input("Yükleyen Kişi:", placeholder="Adınız Soyadınız")
save_name = c2.text_input("Senaryo Dosya Adı:", placeholder="Örn: Kampanya_v1")

existing_names = [e['isim'] for e in full_history]

if c3.button("💾 Arşive Kaydet", use_container_width=True):
    if not save_user or not save_name:
        st.error("⚠️ İsim ve senaryo adı zorunludur!")
    elif save_name in existing_names:
        st.error(f"⚠️ '{save_name}' isimli bir senaryo zaten mevcut. Lütfen farklı bir isim seçin!")
    else:
        new_entry = {
            "tarih": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "isim": save_name,
            "yukleyen": save_user,
            "tip": "Manuel Kayıt",
            "veri": edited_df.to_dict(orient="list")
        }
        full_history.insert(0, new_entry)
        save_history_all(full_history)
        st.success(f"Senaryo kaydedildi!")
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
st.sidebar.caption("v3.1 - Gelişmiş Arşiv & Güvenlik")
