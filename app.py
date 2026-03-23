import streamlit as st
import pandas as pd
import pulp
import os

# 1. SAYFA VE DOSYA AYARLARI
st.set_page_config(page_title="Hepsiburada Ortak Depo Yönetimi", layout="wide")

# Sunucuda verilerin saklanacağı ortak dosya adı
DB_FILE = "shared_warehouse_data.csv"

# SİSTEMİN İLK VERİLERİ (Sıfırla deyince geri dönecek olanlar)
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

# --- ARAYÜZ BAŞLANGIÇ ---
st.title("🚀 Hepsiburada Ortak Depo Planlama Sistemi")

# Üst Panel: Başlık ve Sıfırlama Butonu
col_title, col_reset = st.columns([4, 1])

with col_reset:
    if st.button("🚨 SİSTEMİ SIFIRLA", help="Tüm yüklenen dosyaları siler ve ilk verilere döner"):
        if os.path.exists(DB_FILE):
            os.remove(DB_FILE)
        st.cache_data.clear()
        st.success("Sistem ilk haline döndürüldü!")
        st.rerun()

st.markdown("---")

# Yan Panel: Dosya Yükleme
st.sidebar.header("📤 Veri Güncelleme")
st.sidebar.write("Yeni bir Excel veya CSV yükleyerek tüm ekip için verileri güncelleyebilirsiniz.")
uploaded_file = st.sidebar.file_uploader("Dosya Seçin", type=["csv", "xlsx"])

if uploaded_file:
    try:
        if uploaded_file.name.endswith('.csv'):
            new_df = pd.read_csv(uploaded_file)
        else:
            new_df = pd.read_excel(uploaded_file)
        
        # Sütun isimlerini temizle
        new_df.columns = [c.strip() for c in new_df.columns]
        save_data(new_df)
        st.sidebar.success("✅ Yeni dosya başarıyla sisteme kaydedildi!")
        st.rerun()
    except Exception as e:
        st.sidebar.error(f"Hata oluştu: {e}")

# Mevcut ortak veriyi yükle
df = load_shared_data()

# --- VERİ TABLOSU ---
st.subheader("📊 Güncel Ortak Veri Tablosu")
st.caption("Bu tabloyu herkes aynı görür. Üzerinde değişiklik yapıp aşağıdan kaydedebilirsiniz.")
edited_df = st.data_editor(df, use_container_width=True, num_rows="dynamic")

if st.button("💾 Tablodaki Değişiklikleri Herkese Kaydet"):
    save_data(edited_df)
    st.toast("Değişiklikler tüm kullanıcılar için kaydedildi!", icon="✅")

# --- OPTİMİZASYON HESAPLAMA ---
st.divider()
st.subheader("🎯 Optimizasyon ve Verimlilik Analizi")

col_opt1, col_opt2 = st.columns([1, 2])

with col_opt1:
    target_demand = st.number_input("Hedeflenen Toplam Sevkiyat Talebi (m3)", min_value=0, value=35000, step=500)
    if st.button("🚀 Hesaplamayı Başlat", use_container_width=True):
        try:
            # PuLP Modeli
            prob = pulp.LpProblem("Warehouse_Minimization", pulp.LpMinimize)
            depolar = edited_df["Depo Adı"].tolist()
            usage = pulp.LpVariable.dicts("m3_Usage", depolar, lowBound=0, cat='Continuous')
            
            # Amaç Fonksiyonu: Kira + (Kullanım * Fix Cost)
            prob += pulp.lpSum([
                (usage[d] * edited_df.loc[edited_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0]) +
                (edited_df.loc[edited_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0])
                for d in depolar
            ])
            
            # Kısıtlar
            prob += pulp.lpSum([usage[d] for d in depolar]) == target_demand
            for d in depolar:
                max_cap = edited_df.loc[edited_df["Depo Adı"] == d, "Kapasite (m3)"].values[0]
                prob += usage[d] <= max_cap

            prob.solve(pulp.PULP_CBC_CMD(msg=0))
            
            if pulp.LpStatus[prob.status] == 'Optimal':
                st.session_state['results'] = [{"Depo": d, "m3": round(usage[d].varValue, 2)} for d in depolar]
                st.session_state['cost'] = pulp.value(prob.objective)
            else:
                st.error("❌ Kapasite yetersiz! Lütfen talebi düşürün.")
        except Exception as e:
            st.error(f"Matematiksel hata: {e}")

# Sonuç Gösterimi
if 'results' in st.session_state:
    st.info(f"💰 **Minimum Toplam Maliyet:** {st.session_state['cost']:,.2f} ₺")
    with col_opt2:
        res_df = pd.DataFrame(st.session_state['results'])
        st.dataframe(res_df, use_container_width=True)
        st.bar_chart(res_df.set_index("Depo"))

st.sidebar.markdown("---")
st.sidebar.info("📌 **İpucu:** Bir arkadaşınız dosya yüklediğinde güncel halini görmek için sayfayı yenilemeniz yeterlidir.")
