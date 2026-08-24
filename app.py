import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# ==========================================
# 1. 資料庫初始化與 helper 函數
# ==========================================
DB_NAME = "health_tracker.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 飲食明細表
    c.execute('''
        CREATE TABLE IF NOT EXISTS diet_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            meal_name TEXT NOT NULL,
            calories REAL DEFAULT 0,
            protein REAL DEFAULT 0,
            carbs REAL DEFAULT 0,
            fat REAL DEFAULT 0
        )
    ''')
    # 體重紀錄表
    c.execute('''
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT UNIQUE NOT NULL,
            weight REAL NOT NULL,
            body_fat REAL
        )
    ''')
    conn.commit()
    conn.close()

def get_connection():
    return sqlite3.connect(DB_NAME)

# --- 飲食相關 CRUD ---
def get_diet_logs(selected_date):
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, meal_name, calories, protein, carbs, fat FROM diet_logs WHERE log_date = ?",
        conn, params=(str(selected_date),)
    )
    conn.close()
    return df

def add_diet_log(log_date, meal_name, calories, protein, carbs, fat):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO diet_logs (log_date, meal_name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?)",
        (str(log_date), meal_name, calories, protein, carbs, fat)
    )
    conn.commit()
    conn.close()

def sync_diet_logs(selected_date, edited_df, original_df):
    """將編輯後的 Streamlit DataFrame 同步回 SQLite"""
    conn = get_connection()
    c = conn.cursor()
    
    orig_ids = set(original_df['id'].dropna().astype(int)) if not original_df.empty else set()
    current_ids = set(edited_df['id'].dropna().astype(int)) if 'id' in edited_df.columns else set()
    
    # 1. 處理刪除項
    deleted_ids = orig_ids - current_ids
    for del_id in deleted_ids:
        c.execute("DELETE FROM diet_logs WHERE id = ?", (int(del_id),))
        
    # 2. 處理新增與更新
    for _, row in edited_df.iterrows():
        row_id = row.get('id')
        meal_name = str(row.get('meal_name', '')).strip()
        if not meal_name:
            continue
            
        calories = float(row.get('calories', 0) or 0)
        protein = float(row.get('protein', 0) or 0)
        carbs = float(row.get('carbs', 0) or 0)
        fat = float(row.get('fat', 0) or 0)
        
        if pd.isna(row_id) or int(row_id) not in orig_ids:
            # 新增
            c.execute(
                "INSERT INTO diet_logs (log_date, meal_name, calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?)",
                (str(selected_date), meal_name, calories, protein, carbs, fat)
            )
        else:
            # 更新
            c.execute(
                "UPDATE diet_logs SET meal_name=?, calories=?, protein=?, carbs=?, fat=? WHERE id=?",
                (meal_name, calories, protein, carbs, fat, int(row_id))
            )
            
    conn.commit()
    conn.close()

# --- 體重相關 CRUD ---
def get_weight_logs():
    conn = get_connection()
    df = pd.read_sql_query(
        "SELECT id, log_date, weight, body_fat FROM weight_logs ORDER BY log_date DESC",
        conn
    )
    conn.close()
    return df

def save_weight_log(log_date, weight, body_fat):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        INSERT INTO weight_logs (log_date, weight, body_fat)
        VALUES (?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET
            weight=excluded.weight,
            body_fat=excluded.body_fat
    ''', (str(log_date), weight, body_fat))
    conn.commit()
    conn.close()

def sync_weight_logs(edited_df, original_df):
    """同步體重編輯與刪除至 SQLite"""
    conn = get_connection()
    c = conn.cursor()
    
    orig_ids = set(original_df['id'].dropna().astype(int)) if not original_df.empty else set()
    current_ids = set(edited_df['id'].dropna().astype(int)) if 'id' in edited_df.columns else set()
    
    # 刪除已被移除的列
    deleted_ids = orig_ids - current_ids
    for del_id in deleted_ids:
        c.execute("DELETE FROM weight_logs WHERE id = ?", (int(del_id),))
        
    # 更新修改或新增的列
    for _, row in edited_df.iterrows():
        row_id = row.get('id')
        log_date = str(row.get('log_date', '')).strip()
        if not log_date:
            continue
        
        weight = float(row.get('weight', 0) or 0)
        body_fat = row.get('body_fat')
        body_fat = float(body_fat) if (body_fat is not None and not pd.isna(body_fat)) else None
        
        if pd.isna(row_id) or int(row_id) not in orig_ids:
            c.execute(
                "INSERT INTO weight_logs (log_date, weight, body_fat) VALUES (?, ?, ?)",
                (log_date, weight, body_fat)
            )
        else:
            c.execute(
                "UPDATE weight_logs SET log_date=?, weight=?, body_fat=? WHERE id=?",
                (log_date, weight, body_fat, int(row_id))
            )
            
    conn.commit()
    conn.close()

# ==========================================
# 2. Streamlit 介面與主流程
# ==========================================
st.set_page_config(page_title="健康與飲食管理系統", layout="wide")
init_db()

st.title("🥗 每日營養與體重紀錄系統")

# 日期選擇器
selected_date = st.date_input("📅 選擇日期", value=date.today())

tab1, tab2 = st.tabs(["🍽️ 飲食明細編輯", "⚖️ 體重紀錄與管理"])

# ------------------------------------------
# Tab 1: 飲食明細管理
# ------------------------------------------
with tab1:
    st.subheader(f"{selected_date} 飲食紀錄")
    
    # 快速新增區塊
    with st.expander("➕ 新增單筆飲食紀錄", expanded=False):
        with st.form("add_diet_form", clear_on_submit=True):
            col1, col2, col3, col4, col5 = st.columns(5)
            meal_name = col1.text_input("餐點/食物名稱")
            calories = col2.number_input("熱量 (kcal)", min_value=0.0, step=10.0)
            protein = col3.number_input("蛋白質 (g)", min_value=0.0, step=1.0)
            carbs = col4.number_input("碳水化合物 (g)", min_value=0.0, step=1.0)
            fat = col5.number_input("脂肪 (g)", min_value=0.0, step=1.0)
            
            submitted = st.form_submit_button("新增紀錄")
            if submitted:
                if meal_name.strip():
                    add_diet_log(selected_date, meal_name, calories, protein, carbs, fat)
                    st.success(f"已新增：{meal_name}")
                    st.rerun()
                else:
                    st.warning("請輸入餐點名稱！")

    # 顯示與可編輯表格區塊
    diet_df = get_diet_logs(selected_date)
    
    if not diet_df.empty:
        st.write("💡 **直接在下方表格修改欄位數據，或選取欄位按 Delete/Backspace 鍵刪除整行，修改後請點擊「儲存飲食變更」。**")
        
        edited_diet_df = st.data_editor(
            diet_df,
            column_config={
                "id": None,  # 隱藏內部 ID 欄位
                "meal_name": st.column_config.TextColumn("餐點名稱", required=True),
                "calories": st.column_config.NumberColumn("熱量 (kcal)", min_value=0, format="%.1f"),
                "protein": st.column_config.NumberColumn("蛋白質 (g)", min_value=0, format="%.1f"),
                "carbs": st.column_config.NumberColumn("碳水 (g)", min_value=0, format="%.1f"),
                "fat": st.column_config.NumberColumn("脂肪 (g)", min_value=0, format="%.1f"),
            },
            num_rows="dynamic",  # 允許使用者在表格底部新增/刪除行
            use_container_width=True,
            key="diet_editor"
        )
        
        if st.button("💾 儲存飲食變更", type="primary"):
            sync_diet_logs(selected_date, edited_diet_df, diet_df)
            st.success("飲食明細已成功更新！")
            st.rerun()

        # 每日營養總計
        st.markdown("---")
        total_cal = edited_diet_df["calories"].sum()
        total_p = edited_diet_df["protein"].sum()
        total_c = edited_diet_df["carbs"].sum()
        total_f = edited_diet_df["fat"].sum()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("總熱量", f"{total_cal:.1f} kcal")
        m2.metric("總蛋白質", f"{total_p:.1f} g")
        m3.metric("總碳水", f"{total_c:.1f} g")
        m4.metric("總脂肪", f"{total_f:.1f} g")
    else:
        st.info("當天尚無飲食紀錄，請使用上方表單新增。")

# ------------------------------------------
# Tab 2: 體重紀錄管理
# ------------------------------------------
with tab2:
    st.subheader("體重與體脂率紀錄")
    
    # 新增/更新當日體重
    col_w1, col_w2, col_w3 = st.columns([2, 2, 1])
    input_weight = col_w1.number_input("體重 (kg)", min_value=30.0, max_value=200.0, value=62.0, step=0.1)
    input_fat = col_w2.number_input("體脂率 (%) [選填]", min_value=0.0, max_value=60.0, value=0.0, step=0.1)
    
    if col_w3.button("📥 快速紀錄當天體重", use_container_width=True):
        fat_val = input_fat if input_fat > 0 else None
        save_weight_log(selected_date, input_weight, fat_val)
        st.success(f"已儲存 {selected_date} 體重紀錄！")
        st.rerun()
        
    st.markdown("---")
    st.write("📋 **歷史體重紀錄表（可直接修改日期、體重、體脂或刪除項目）**")
    
    weight_df = get_weight_logs()
    
    if not weight_df.empty:
        edited_weight_df = st.data_editor(
            weight_df,
            column_config={
                "id": None,  # 隱藏內部 ID
                "log_date": st.column_config.TextColumn("日期 (YYYY-MM-DD)", required=True),
                "weight": st.column_config.NumberColumn("體重 (kg)", min_value=30.0, max_value=200.0, format="%.1f", required=True),
                "body_fat": st.column_config.NumberColumn("體脂率 (%)", min_value=0.0, max_value=60.0, format="%.1f"),
            },
            num_rows="dynamic",
            use_container_width=True,
            key="weight_editor"
        )
        
        if st.button("💾 儲存體重資料變更", type="primary"):
            sync_weight_logs(edited_weight_df, weight_df)
            st.success("體重紀錄已成功更新！")
            st.rerun()

        # 簡單趨勢折線圖
        st.subheader("📈 體重變化趨勢")
        chart_data = weight_df.sort_values("log_date").set_index("log_date")
        st.line_chart(chart_data["weight"])
    else:
        st.info("目前尚無體重紀錄。")
