import streamlit as st
import pandas as pd
import pulp
import os

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hepsiburada Ortak Depo", layout="wide")

DB_FILE = "shared_warehouse_data.csv"

# FABRİKA AYARLARI (İlk Veriler)
initial_data = {
    "Depo Adı": ["Gebze Depo", "İzmir Torbalı Depo", "İzmir Pancar Depo", "Düzce Depo", "Bilecik Depo", "Adana Depo", "İzmir Pınarbaşı Depo"],
    "Kapasite (m3)": [19301, 13824, 3365, 15343, 22000, 2133, 4694],
    "Kira Maliyeti (₺)": [10072228, 3353400, 2296381, 2697600, 3310998, 0, 737965],
    "Fix Cost (m3 Başı)": [185.19, 31.15, 277.30, 73.51, 55.12, 73.18, 48.03]
}

# --- YARDIMCI FONKSİYONLAR ---
def save_data(df):
    df.to_csv(DB_FILE, index=False)

def load_shared_data():
    if os.path.exists(DB_FILE):
        return pd.read_csv(DB_FILE)
    return pd.DataFrame(initial_data)

# --- SIFIRLAMA MANTIĞI (GELİŞTİRİLMİŞ) ---
def reset_system():
    # 1. Ortak dosyayı sil
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    # 2. Streamlit'in tüm geçici hafızasını (manuel değişiklikleri) temizle
    for key in st.session_state.keys():
        del st.session_state[key]
    
    st.cache_data.clear()
    st.success("Sistem ve tarayıcı hafızası tamamen sıfırlandı!")
    st.rerun()

# --- ARAYÜZ ---
st.title("🚀 Hepsiburada Ortak Depo Planlama")

col_title, col_reset = st.columns([4, 1])
with col_reset:
    # Burada direkt fonksiyonu çağırıyoruz
    if st.button("🚨 SİSTEMİ SIFIRLA"):
        reset_system()

st.markdown("---")

# Yan Panel: Dosya Yükleme
st.sidebar.header("📤 Veri Güncelleme")
uploaded_file = st.sidebar.file_uploader("Excel veya CSV Yükleyin", type=["csv", "xlsx"])

if uploaded_file:
    try:
        new_df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith('.csv') else pd.read_excel(uploaded_file)
        new_df.columns = [c.strip() for c in new_df.columns]
        save_data(new_df)
        # Yükleme sonrası hafızayı temizle ki yeni veri görünsün
        st.cache_data.clear()
        st.sidebar.success("✅ Yeni dosya kaydedildi!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Hata: {e}")

# Veriyi yükle
df = load_shared_data()

# --- TABLO (Key eklendi ki sıfırlanınca resetlensin) ---
st.subheader("📊 Güncel Ortak Veri Tablosu")
# 'key' parametresi sayesinde reset_system içindeki 'del st.session_state' komutu burayı sıfırlar
edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic", key="main_editor")

if st.button("💾 Tablodaki Değişiklikleri Herkese Kaydet"):
    save_data(edited_df)
    st.toast("Değişiklikler kaydedildi!", icon="✅")

# --- OPTİMİZASYON ---
st.divider()
col_opt1, col_opt2 = st.columns([1, 2])

with col_opt1:
    target_demand = st.number_input("Hedeflenen Toplam Sevkiyat Talebi (m3)", min_value=0, value=35000)
    if st.button("🚀 Hesapla", use_container_width=True):
        try:
            prob = pulp.LpProblem("Warehouse_Minimization", pulp.LpMinimize)
            depolar = edited_df["Depo Adı"].tolist()
            usage = pulp.LpVariable.dicts("m3_Usage", depolar, lowBound=0)
            
            prob += pulp.lpSum([
                (usage[d] * edited_df.loc[edited_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0]) +
                (edited_df.loc[edited_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0])
                for d in depolar
            ])
            
            prob += pulp.lpSum([usage[d] for d in depolar]) == target_demand
            for d in depolar:
                max_cap = edited_df.loc[edited_df["Depo Adı"] == d, "Kapasite (m3)"].values[0]
                prob += usage[d] <= max_cap

            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.session_state['results'] = [{"Depo": d, "m3": round(usage[d].varValue, 2)} for d in depolar]
                st.session_state['cost'] = pulp.value(prob.objective)
            else:
                st.error("❌ Kapasite yetersiz!")
        except Exception as e:
            st.error(f"Hata: {e}")

if 'results' in st.session_state:
    st.info(f"💰 Minimum Maliyet: {st.session_state['cost']:,.2f} ₺")
    with col_opt2:
        res_df = pd.DataFrame(st.session_state['results'])
        st.dataframe(res_df, use_container_width=True)
        st.bar_chart(res_df.set_index("Depo"))
