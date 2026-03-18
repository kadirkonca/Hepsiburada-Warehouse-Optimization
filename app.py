import streamlit as st
import pandas as pd
import pulp

# 1. SAYFA AYARLARI
st.set_page_config(page_title="Hepsiburada Warehouse Optimization", layout="wide")

st.title("📦 Hepsiburada Depo Optimizasyon Sistemi")
st.markdown("""
Bu panel üzerinden depoların kapasite ve maliyet verilerini güncelleyebilir, 
toplam talebi karşılayacak **minimum maliyetli** dağıtım senaryosunu hesaplayabilirsiniz.
""")

# 2. VERİ SETİ (Senin verdiğin gerçek veriler)
if 'df' not in st.session_state:
    data = {
        "Depo Adı": ["Gebze Depo", "İzmir Torbalı Depo", "İzmir Pancar Depo", "Düzce Depo", "Bilecik Depo", "Adana Depo", "İzmir Pınarbaşı Depo"],
        "Kapasite (m3)": [19301, 13824, 3365, 15343, 22000, 2133, 4694],
        "Kira Maliyeti (₺)": [10072228, 3353400, 2296381, 2697600, 3310998, 0, 737965],
        "Fix Cost (m3 Başı)": [185.19, 31.15, 277.30, 73.51, 55.12, 73.18, 48.03]
    }
    st.session_state.df = pd.DataFrame(data)

# 3. ARAYÜZ: VERİ DÜZENLEME
st.subheader("📊 1. Adım: Depo Parametrelerini Güncelleyin")
edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", use_container_width=True)

# 4. OPTİMİZASYON AYARLARI
st.divider()
st.subheader("🎯 2. Adım: Talep ve Optimizasyon")

col1, col2 = st.columns([1, 2])

with col1:
    total_needed = st.number_input("Hedeflenen Toplam Sevkiyat Talebi (m3)", min_value=0, value=30000, step=500)
    run_button = st.button("🚀 Optimizasyonu Çalıştır", use_container_width=True)

# 5. MATEMATİKSEL MODEL (PuLP)
if run_button:
    # Problemi Tanımla
    prob = pulp.LpProblem("Warehouse_Minimization", pulp.LpMinimize)
    
    depolar = edited_df["Depo Adı"].tolist()
    # Karar Değişkeni: Her depodan kaç m3 kullanılacak?
    usage = pulp.LpVariable.dicts("m3_Usage", depolar, lowBound=0, cat='Continuous')
    
    # Amaç Fonksiyonu: Toplam Maliyet = Kira + (Kullanılan m3 * Fix Cost)
    prob += pulp.lpSum([
        (usage[d] * edited_df.loc[edited_df["Depo Adı"] == d, "Fix Cost (m3 Başı)"].values[0]) +
        (edited_df.loc[edited_df["Depo Adı"] == d, "Kira Maliyeti (₺)"].values[0])
        for d in depolar
    ])
    
    # Kısıtlar
    # 1. Toplam kullanım talebe eşit olmalı
    prob += pulp.lpSum([usage[d] for d in depolar]) == total_needed
    
    # 2. Her deponun kapasitesi aşılmamalı
    for d in depolar:
        max_cap = edited_df.loc[edited_df["Depo Adı"] == d, "Kapasite (m3)"].values[0]
        prob += usage[d] <= max_cap

    # Çözüm
    prob.solve(pulp.PULP_CBC_CMD(msg=0))
    
    if pulp.LpStatus[prob.status] == 'Optimal':
        st.success(f"✅ Optimizasyon Başarılı! Toplam Minimum Maliyet: {pulp.value(prob.objective):,.2f} ₺")
        
        # Sonuçları Hazırlama
        res_data = []
        for d in depolar:
            used_val = usage[d].varValue
            res_data.append({"Depo": d, "Kullanılan (m3)": round(used_val, 2)})
        
        res_df = pd.DataFrame(res_data)
        
        with col2:
            st.write("**Depo Kullanım Sonuçları:**")
            st.dataframe(res_df, use_container_width=True)
            
            # Basit Grafik (Matplotlib gerektirmez)
            st.bar_chart(res_df.set_index("Depo"))
            
    else:
        st.error("❌ Hata: Bu talebi karşılayacak yeterli toplam kapasite yok!")

# Yan Panel Bilgisi
st.sidebar.info(f"Toplam Mevcut Kapasite: {edited_df['Kapasite (m3)'].sum():,} m3")