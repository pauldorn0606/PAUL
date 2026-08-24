import sqlite3
import pandas as pd
import streamlit as st
from datetime import date

# ==========================================
# 1. 資料庫初始化與連線設定
# ==========================================
DB_FILE = "health_tracker.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    
    # 建立飲食紀錄表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS food_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL,
            meal_type TEXT NOT NULL,
            food_name TEXT NOT NULL,
            calories REAL DEFAULT 0,
            protein REAL DEFAULT 0,
            carbs REAL DEFAULT 0,
            fat REAL DEFAULT 0
        )
    """)
    
    # 建立體重紀錄表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weight_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            log_date TEXT NOT NULL UNIQUE,
            weight REAL NOT NULL,
            body_fat REAL,
            note TEXT
        )
    """)
    
    conn.commit()
    conn.close()

init_db()

# ==========================================
# 2. 頁面選單設定
# ==========================================
st.set_page_config(page_title="健康與飲食追蹤系統", page_icon="🥗", layout="wide")
st.title("🥗 健康與飲食追蹤系統")

tab1, tab2, tab3 = st.tabs(["📝 新增紀錄", "📊 飲食明細管理", "⚖️ 體重紀錄管理"])

# ==========================================
# TAB 1: 新增紀錄
# ==========================================
with tab1:
    col1, col2 = st.columns(2)
    
    # --- 新增飲食 ---
    with col1:
        st.subheader("🍕 新增飲食紀錄")
        with st.form("add_food_form", clear_on_submit=True):
            f_date = st.date_input("日期", value=date.today(), key="add_f_date")
            f_meal = st.selectbox("餐別", ["早餐", "午餐", "晚餐", "點心/補給"])
            f_name = st.text_input("食物名稱", placeholder="例如：雞胸肉沙拉")
            
            c1, c2 = st.columns(2)
            f_cal = c1.number_input("熱量 (kcal)", min_value=0.0, step=10.0)
            f_protein = c2.number_input("蛋白質 (g)", min_value=0.0, step=1.0)
            
            c3, c4 = st.columns(2)
            f_carbs = c3.number_input("碳水化合物 (g)", min_value=0.0, step=1.0)
            f_fat = c4.number_input("脂肪 (g)", min_value=0.0, step=1.0)
            
            submit_food = st.form_submit_button("新增飲食資料")
            
            if submit_food:
                if not f_name.strip():
                    st.error("請輸入食物名稱！")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO food_logs (log_date, meal_type, food_name, calories, protein, carbs, fat)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (str(f_date), f_meal, f_name, f_cal, f_protein, f_carbs, f_fat))
                    conn.commit()
                    conn.close()
                    st.success(f"已成功新增：{f_name}")
                    st.rerun()

    # --- 新增體重 ---
    with col2:
        st.subheader("⚖️ 新增/更新體重紀錄")
        with st.form("add_weight_form", clear_on_submit=True):
            w_date = st.date_input("日期", value=date.today(), key="add_w_date")
            w_weight = st.number_input("體重 (kg)", min_value=0.0, max_value=200.0, step=0.1, format="%.1f")
            w_fat = st.number_input("體脂率 (%) [選填]", min_value=0.0, max_value=60.0, step=0.1, format="%.1f")
            w_note = st.text_input("備註", placeholder="例如：晨起空腹")
            
            submit_weight = st.form_submit_button("儲存體重紀錄")
            
            if submit_weight:
                if w_weight <= 0:
                    st.error("請輸入有效的體重！")
                else:
                    conn = get_connection()
                    cursor = conn.cursor()
                    # 使用 INSERT OR REPLACE 避免同天重複紀錄
                    cursor.execute("""
                        INSERT OR REPLACE INTO weight_logs (log_date, weight, body_fat, note)
                        VALUES (?, ?, ?, ?)
                    """, (str(w_date), w_weight, w_fat if w_fat > 0 else None, w_note))
                    conn.commit()
                    conn.close()
                    st.success(f"已記錄 {w_date} 的體重：{w_weight} kg")
                    st.rerun()

# ==========================================
# TAB 2: 飲食明細管理（可線上編輯 & 刪除）
# ==========================================
with tab2:
    st.subheader("📋 飲食明細編輯與刪除")
    
    conn = get_connection()
    df_food = pd.read_sql_query("SELECT * FROM food_logs ORDER BY log_date DESC, id DESC", conn)
    conn.close()
    
    if df_food.empty:
        st.info("目前尚無飲食紀錄。")
    else:
        st.markdown("💡 **操作說明**：可直接點擊表格儲存格修改內容，或勾選「刪除」後點擊下方按鈕進行批次刪除。")
        
        # 增加一欄用於勾選刪除
        df_food.insert(0, "刪除", False)
        
        # 使用 st.data_editor 進行線上編輯
        edited_food_df = st.data_editor(
            df_food,
            disabled=["id"],  # 不可編輯主鍵 ID
            column_config={
                "id": "ID",
                "刪除": st.column_config.CheckboxColumn("刪除", help="勾選欲刪除的項目"),
                "log_date": st.column_config.DateColumn("日期", format="YYYY-MM-DD", required=True),
                "meal_type": st.column_config.SelectboxColumn("餐別", options=["早餐", "午餐", "晚餐", "點心/補給"], required=True),
                "food_name": st.column_config.TextColumn("食物名稱", required=True),
                "calories": st.column_config.NumberColumn("熱量 (kcal)", min_value=0, format="%.1f"),
                "protein": st.column_config.NumberColumn("蛋白質 (g)", min_value=0, format="%.1f"),
                "carbs": st.column_config.NumberColumn("碳水化合物 (g)", min_value=0, format="%.1f"),
                "fat": st.column_config.NumberColumn("脂肪 (g)", min_value=0, format="%.1f"),
            },
            hide_index=True,
            use_container_width=True,
            key="food_editor"
        )
        
        btn_col1, btn_col2 = st.columns([1, 4])
        
        # 儲存變更按鈕
        if btn_col1.button("💾 儲存修改內容", key="save_food"):
            conn = get_connection()
            cursor = conn.cursor()
            for idx, row in edited_food_df.iterrows():
                cursor.execute("""
                    UPDATE food_logs
                    SET log_date = ?, meal_type = ?, food_name = ?, calories = ?, protein = ?, carbs = ?, fat = ?
                    WHERE id = ?
                """, (str(row['log_date']), row['meal_type'], row['food_name'], 
                      row['calories'], row['protein'], row['carbs'], row['fat'], row['id']))
            conn.commit()
            conn.close()
            st.success("飲食紀錄修改完成！")
            st.rerun()
            
        # 刪除所選資料按鈕
        if btn_col2.button("🗑️ 刪除勾選項目", type="primary", key="delete_food"):
            to_delete = edited_food_df[edited_food_df["刪除"] == True]
            if to_delete.empty:
                st.warning("請先勾選欲刪除的項目。")
            else:
                delete_ids = to_delete["id"].tolist()
                conn = get_connection()
                cursor = conn.cursor()
                cursor.executemany("DELETE FROM food_logs WHERE id = ?", [(i,) for i in delete_ids])
                conn.commit()
                conn.close()
                st.success(f"已刪除 {len(delete_ids)} 筆資料！")
                st.rerun()

# ==========================================
# TAB 3: 體重紀錄管理（可線上編輯 & 刪除）
# ==========================================
with tab3:
    st.subheader("📉 體重紀錄編輯與刪除")
    
    conn = get_connection()
    df_weight = pd.read_sql_query("SELECT * FROM weight_logs ORDER BY log_date DESC", conn)
    conn.close()
    
    if df_weight.empty:
        st.info("目前尚無體重紀錄。")
    else:
        st.markdown("💡 **操作說明**：可直接修改體重、體脂或備註，修改完請點擊「儲存修改內容」。")
        
        # 增加一欄用於勾選刪除
        df_weight.insert(0, "刪除", False)
        
        edited_weight_df = st.data_editor(
            df_weight,
            disabled=["id"],
            column_config={
                "id": "ID",
                "刪除": st.column_config.CheckboxColumn("刪除", help="勾選欲刪除的項目"),
                "log_date": st.column_config.DateColumn("日期", format="YYYY-MM-DD", required=True),
                "weight": st.column_config.NumberColumn("體重 (kg)", min_value=0.0, format="%.1f", required=True),
                "body_fat": st.column_config.NumberColumn("體脂率 (%)", min_value=0.0, format="%.1f"),
                "note": st.column_config.TextColumn("備註"),
            },
            hide_index=True,
            use_container_width=True,
            key="weight_editor"
        )
        
        w_btn_col1, w_btn_col2 = st.columns([1, 4])
        
        # 儲存體重修改
        if w_btn_col1.button("💾 儲存修改內容", key="save_weight"):
            conn = get_connection()
            cursor = conn.cursor()
            for idx, row in edited_weight_df.iterrows():
                cursor.execute("""
                    UPDATE weight_logs
                    SET log_date = ?, weight = ?, body_fat = ?, note = ?
                    WHERE id = ?
                """, (str(row['log_date']), row['weight'], row['body_fat'], row['note'], row['id']))
            conn.commit()
            conn.close()
            st.success("體重紀錄修改完成！")
            st.rerun()
            
        # 刪除體重項目
        if w_btn_col2.button("🗑️ 刪除勾選項目", type="primary", key="delete_weight"):
            to_delete_w = edited_weight_df[edited_weight_df["刪除"] == True]
            if to_delete_w.empty:
                st.warning("請先勾選欲刪除的項目。")
            else:
                delete_w_ids = to_delete_w["id"].tolist()
                conn = get_connection()
                cursor = conn.cursor()
                cursor.executemany("DELETE FROM weight_logs WHERE id = ?", [(i,) for i in delete_w_ids])
                conn.commit()
                conn.close()
                st.success(f"已刪除 {len(delete_w_ids)} 筆體重紀錄！")
                st.rerun()
                
        # 體重變化圖表
        st.divider()
        st.subheader("📈 體重趨勢圖")
        df_chart = df_weight.sort_values("log_date")
        st.line_chart(df_chart, x="log_date", y="weight")
