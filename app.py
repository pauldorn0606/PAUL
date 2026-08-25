from datetime import date, datetime, timedelta
import sqlite3
import altair as alt
import pandas as pd
import streamlit as st

# =============================================================================
# 0. 資料庫初始化與輔助函式 (Database & Helper Functions)
# =============================================================================


def get_connection():
    return sqlite3.connect("health_tracker.db", check_same_thread=False)


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # 飲食紀錄表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS food_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        item TEXT NOT NULL,
        calories REAL DEFAULT 0,
        protein REAL DEFAULT 0,
        carbs REAL DEFAULT 0,
        fat REAL DEFAULT 0,
        meal_type TEXT DEFAULT '未分類'
    )
    """)

    # 運動紀錄表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS workouts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        log_date TEXT NOT NULL,
        workout_type TEXT NOT NULL,
        item TEXT NOT NULL,
        calories_burned REAL DEFAULT 0,
        distance REAL DEFAULT 0,
        duration_min REAL DEFAULT 0,
        avg_hr REAL DEFAULT 0,
        shoe TEXT DEFAULT '',
        body_part TEXT DEFAULT '',
        workout_notes TEXT DEFAULT '',
        rpe INTEGER DEFAULT 0
    )
    """)

    # 體重與體脂紀錄表
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS weight_logs (
        log_date TEXT PRIMARY KEY,
        weight REAL NOT NULL,
        body_fat REAL,
        note TEXT DEFAULT ''
    )
    """)

    conn.commit()
    conn.close()


def calculate_pace(distance_km, duration_min):
    if not distance_km or distance_km <= 0 or not duration_min:
        return "N/A"
    total_seconds = duration_min * 60
    sec_per_km = total_seconds / distance_km
    pace_min = int(sec_per_km // 60)
    pace_sec = int(sec_per_km % 60)
    return f"{pace_min}'{pace_sec:02d}\""


# ---------------- CRUD 輔助函式 ----------------
def delete_food_log(log_id):
    conn = get_connection()
    conn.execute("DELETE FROM food_logs WHERE id = ?", (log_id,))
    conn.commit()
    conn.close()


def update_food_log(log_id, item, calories, protein, carbs, fat, meal_type):
    conn = get_connection()
    conn.execute(
        """
        UPDATE food_logs 
        SET item = ?, calories = ?, protein = ?, carbs = ?, fat = ?, meal_type = ?
        WHERE id = ?
    """,
        (item, calories, protein, carbs, fat, meal_type, log_id),
    )
    conn.commit()
    conn.close()


def delete_workout(workout_id):
    conn = get_connection()
    conn.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))
    conn.commit()
    conn.close()


def update_workout(workout_id, item, calories_burned, workout_type, **kwargs):
    conn = get_connection()
    distance = kwargs.get("distance", 0.0)
    duration_min = kwargs.get("duration_min", 0.0)
    avg_hr = kwargs.get("avg_hr", 0)
    shoe = kwargs.get("shoe", "")
    body_part = kwargs.get("body_part", "")
    workout_notes = kwargs.get("workout_notes", "")
    rpe = kwargs.get("rpe", 0)

    conn.execute(
        """
        UPDATE workouts 
        SET item = ?, calories_burned = ?, workout_type = ?, distance = ?, 
            duration_min = ?, avg_hr = ?, shoe = ?, body_part = ?, 
            workout_notes = ?, rpe = ?
        WHERE id = ?
    """,
        (
            item,
            calories_burned,
            workout_type,
            distance,
            duration_min,
            avg_hr,
            shoe,
            body_part,
            workout_notes,
            rpe,
            workout_id,
        ),
    )
    conn.commit()
    conn.close()


def delete_weight_log(date_str):
    conn = get_connection()
    conn.execute("DELETE FROM weight_logs WHERE log_date = ?", (date_str,))
    conn.commit()
    conn.close()


def add_or_update_weight(date_str, weight, body_fat, note=""):
    conn = get_connection()
    conn.execute(
        """
        INSERT INTO weight_logs (log_date, weight, body_fat, note)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(log_date) DO UPDATE SET
            weight=excluded.weight,
            body_fat=excluded.body_fat,
            note=excluded.note
    """,
        (date_str, weight, body_fat, note),
    )
    conn.commit()
    conn.close()


# ---------------- 資料查詢輔助函式 ----------------
def get_daily_logs(date_str):
    conn = get_connection()
    food_df = pd.read_sql_query(
        "SELECT * FROM food_logs WHERE log_date = ?", conn, params=(date_str,)
    )
    workout_df = pd.read_sql_query(
        "SELECT * FROM workouts WHERE log_date = ?", conn, params=(date_str,)
    )
    weight_df = pd.read_sql_query(
        "SELECT * FROM weight_logs WHERE log_date = ?",
        conn,
        params=(date_str,),
    )
    conn.close()
    return food_df, workout_df, weight_df


def get_recent_weights(days=30):
    conn = get_connection()
    cutoff_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    df = pd.read_sql_query(
        "SELECT * FROM weight_logs WHERE log_date >= ? ORDER BY log_date ASC",
        conn,
        params=(cutoff_date,),
    )
    conn.close()
    return df


def get_recent_logs(days=7):
    conn = get_connection()
    cutoff_date = (date.today() - timedelta(days=days)).strftime("%Y-%m-%d")
    food_df = pd.read_sql_query(
        "SELECT * FROM food_logs WHERE log_date >= ? ORDER BY log_date ASC",
        conn,
        params=(cutoff_date,),
    )
    workout_df = pd.read_sql_query(
        "SELECT * FROM workouts WHERE log_date >= ? ORDER BY log_date ASC",
        conn,
        params=(cutoff_date,),
    )
    conn.close()
    return food_df, workout_df


# =============================================================================
# 1. 頁面區塊渲染函式 (UI Components)
# =============================================================================


def render_add_records(date_str):
    st.markdown(f"### ➕ 新增紀錄 ({date_str})")
    tab1, tab2, tab3 = st.tabs(
        ["🥗 飲食紀錄", "🏋️ 運動紀錄", "⚖️ 體重與體脂"]
    )

    with tab1:
        with st.form("add_food_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                f_item = st.text_input("食物/餐點名稱", placeholder="例如：雞胸肉便當")
                f_type = st.selectbox(
                    "餐別", ["早餐", "午餐", "晚餐", "點心/補給"]
                )
                f_cal = st.number_input(
                    "熱量 (kcal)", min_value=0.0, step=10.0
                )
            with col2:
                f_p = st.number_input(
                    "蛋白質 (g)", min_value=0.0, step=1.0
                )
                f_c = st.number_input("碳水化合物 (g)", min_value=0.0, step=1.0)
                f_f = st.number_input("脂肪 (g)", min_value=0.0, step=1.0)

            if st.form_submit_button("➕ 新增飲食"):
                if f_item:
                    conn = get_connection()
                    conn.execute(
                        """
                        INSERT INTO food_logs (log_date, item, calories, protein, carbs, fat, meal_type)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            date_str,
                            f_item.strip(),
                            f_cal,
                            f_p,
                            f_c,
                            f_f,
                            f_type,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.toast("飲食紀錄新增成功！")
                    st.rerun()
                else:
                    st.warning("請輸入食物名稱。")

    with tab2:
        with st.form("add_workout_form", clear_on_submit=True):
            w_type = st.selectbox(
                "運動類型", ["慢跑", "重訓", "騎車/其他"]
            )
            col1, col2 = st.columns(2)

            with col1:
                w_item = st.text_input(
                    "運動項目", placeholder="例如：Zone 2 慢跑 / 深蹲"
                )
                w_cal = st.number_input(
                    "消耗熱量 (kcal)", min_value=0.0, step=10.0
                )

                if w_type == "慢跑":
                    w_dist = st.number_input(
                        "距離 (km)", min_value=0.0, step=0.1
                    )
                    w_dur = st.number_input(
                        "時間 (分鐘)", min_value=0.0, step=1.0
                    )
                    w_shoe = st.selectbox(
                        "使用跑鞋",
                        [
                            "Adidas Boston 13",
                            "Adidas Adizero",
                            "其他跑鞋",
                            "不指定",
                        ],
                    )
                else:
                    w_dist, w_dur, w_shoe = 0.0, 0.0, ""

            with col2:
                if w_type == "慢跑":
                    w_hr = st.number_input(
                        "平均心率 (bpm)", min_value=0, step=1
                    )
                    w_body, w_notes, w_rpe = "", "", 0
                elif w_type == "重訓":
                    w_hr = 0
                    w_body = st.selectbox(
                        "主要訓練部位",
                        [
                            "胸部",
                            "背部",
                            "腿部",
                            "肩部",
                            "手臂",
                            "核心",
                            "全身/其他",
                        ],
                    )
                    w_rpe = st.slider(
                        "自覺強度 (RPE 1-10)",
                        min_value=1,
                        max_value=10,
                        value=7,
                    )
                    w_notes = st.text_area(
                        "動作與組數紀錄",
                        placeholder="例如：槓鈴深蹲 80kg 5x5",
                        height=70,
                    )
                else:
                    w_hr, w_body, w_notes, w_rpe = 0, "", "", 0

            if st.form_submit_button("➕ 新增運動"):
                if w_item:
                    conn = get_connection()
                    conn.execute(
                        """
                        INSERT INTO workouts (log_date, workout_type, item, calories_burned, distance, duration_min, avg_hr, shoe, body_part, workout_notes, rpe)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            date_str,
                            w_type,
                            w_item.strip(),
                            w_cal,
                            w_dist,
                            w_dur,
                            w_hr,
                            w_shoe,
                            w_body,
                            w_notes,
                            w_rpe,
                        ),
                    )
                    conn.commit()
                    conn.close()
                    st.toast("運動紀錄新增成功！")
                    st.rerun()
                else:
                    st.warning("請輸入運動項目名稱。")

    with tab3:
        with st.form("add_weight_form", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                wt_val = st.number_input(
                    "體重 (kg)", min_value=0.0, max_value=200.0, step=0.1
                )
            with col2:
                fat_val = st.number_input(
                    "體脂率 (%)",
                    min_value=0.0,
                    max_value=60.0,
                    step=0.1,
                    value=0.0,
                )
            wt_note = st.text_input("備註 (可選)", placeholder="例如：早起空腹測量")

            if st.form_submit_button("💾 儲存體重/體脂紀錄"):
                if wt_val > 0:
                    add_or_update_weight(
                        date_str,
                        wt_val,
                        fat_val if fat_val > 0 else None,
                        wt_note,
                    )
                    st.toast("體重紀錄更新成功！")
                    st.rerun()
                else:
                    st.warning("請輸入有效的體重數值。")


def render_daily_progress(
    date_str, target_cal, target_p, target_carbs, target_fat
):
    st.markdown(f"### 🎯 當日進度與營養目標 ({date_str})")
    food_df, workout_df, weight_df = get_daily_logs(date_str)

    total_cal = food_df["calories"].sum() if not food_df.empty else 0
    total_p = food_df["protein"].sum() if not food_df.empty else 0
    total_c = food_df["carbs"].sum() if not food_df.empty else 0
    total_f = food_df["fat"].sum() if not food_df.empty else 0
    burned_cal = (
        workout_df["calories_burned"].sum() if not workout_df.empty else 0
    )

    # 體重與體脂顯示邏輯
    if not weight_df.empty:
        curr_weight = weight_df.iloc[0]["weight"]
        curr_fat = weight_df.iloc[0]["body_fat"]
        weight_str = f"{curr_weight:.1f} kg"
        fat_str = (
            f"{curr_fat:.1f}%"
            if pd.notna(curr_fat) and curr_fat > 0
            else "未紀錄"
        )
    else:
        weight_str = "今日未紀錄"
        fat_str = "今日未紀錄"

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("🔥 淨攝取熱量", f"{total_cal - burned_cal:.0f} kcal", f"目標: {target_cal}")
    col2.metric("🥩 蛋白質", f"{total_p:.1f} g", f"目標: {target_p}g")
    col3.metric("🍚 碳水化合物", f"{total_c:.1f} g", f"目標: {target_carbs}g")
    col4.metric("🥑 脂肪", f"{total_f:.1f} g", f"目標: {target_fat}g")
    col5.metric("⚖️ 當日體重/體脂", weight_str, f"體脂: {fat_str}")


def render_daily_logs(date_str):
    st.markdown(f"### 📋 當日明細清單 ({date_str})")
    food_df, workouts_df, weight_df = get_daily_logs(date_str)

    list_tab1, list_tab2, list_tab3 = st.tabs(
        ["🥗 飲食明細", "🏋️ 運動明細", "⚖️ 體重紀錄"]
    )

    # 1. 飲食明細
    with list_tab1:
        if not food_df.empty:
            for _, row in food_df.iterrows():
                log_id = row["id"]
                col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])
                with col_info:
                    st.write(
                        f"**[{row['meal_type']}] {row['item']}** — {row['calories']:.0f} kcal | "
                        f"P: {row['protein']:.1f}g | C: {row['carbs']:.1f}g | F: {row['fat']:.1f}g"
                    )
                with col_edit:
                    if st.button("✏️ 編輯", key=f"btn_edit_food_{log_id}"):
                        st.session_state[f"editing_food_{log_id}"] = (
                            not st.session_state.get(
                                f"editing_food_{log_id}", False
                            )
                        )
                with col_del:
                    if st.button("🗑️ 刪除", key=f"del_food_{log_id}"):
                        delete_food_log(log_id)
                        st.toast(f"已刪除：{row['item']}")
                        st.rerun()

                if st.session_state.get(f"editing_food_{log_id}", False):
                    with st.form(key=f"form_edit_food_{log_id}"):
                        st.caption(f"🛠️ 編輯飲食紀錄 ID: {log_id}")
                        e_item = st.text_input("名稱", value=row["item"])
                        meal_opts = ["早餐", "午餐", "晚餐", "點心/補給"]
                        curr_meal_idx = (
                            meal_opts.index(row["meal_type"])
                            if row["meal_type"] in meal_opts
                            else 0
                        )
                        e_type = st.selectbox(
                            "餐別", meal_opts, index=curr_meal_idx
                        )

                        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                        with col_e1:
                            e_cal = st.number_input(
                                "熱量",
                                value=float(row["calories"]),
                                step=10.0,
                            )
                        with col_e2:
                            e_p = st.number_input(
                                "蛋白質", value=float(row["protein"]), step=1.0
                            )
                        with col_e3:
                            e_c = st.number_input(
                                "碳水", value=float(row["carbs"]), step=1.0
                            )
                        with col_e4:
                            e_f = st.number_input(
                                "脂肪", value=float(row["fat"]), step=1.0
                            )

                        if st.form_submit_button("💾 儲存變更"):
                            update_food_log(
                                log_id,
                                e_item.strip(),
                                e_cal,
                                e_p,
                                e_c,
                                e_f,
                                e_type,
                            )
                            st.session_state[f"editing_food_{log_id}"] = False
                            st.toast("飲食紀錄已更新！")
                            st.rerun()
                    st.divider()
        else:
            st.info("當天尚無飲食紀錄。")

    # 2. 運動明細
    with list_tab2:
        if not workouts_df.empty:
            for _, row in workouts_df.iterrows():
                w_id = row["id"]
                w_type = row["workout_type"]
                col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])

                with col_info:
                    if w_type == "慢跑":
                        pace_str = calculate_pace(
                            row["distance"], row["duration_min"]
                        )
                        hr_str = (
                            f" | 心率: {int(row['avg_hr'])} bpm"
                            if pd.notna(row["avg_hr"]) and row["avg_hr"] > 0
                            else ""
                        )
                        shoe_str = (
                            f" | 跑鞋: {row['shoe']}"
                            if pd.notna(row["shoe"]) and row["shoe"]
                            else ""
                        )
                        st.write(
                            f"**🏃 {row['item']}** — {row['distance']:.2f} km | 配速: {pace_str} | 時間: {row['duration_min']:.0f} 分鐘{hr_str}{shoe_str} (🔥 {row['calories_burned']:.0f} kcal)"
                        )
                    elif w_type == "重訓":
                        body_str = (
                            f"[{row['body_part']}] "
                            if pd.notna(row["body_part"]) and row["body_part"]
                            else ""
                        )
                        rpe_str = (
                            f" | RPE: {int(row['rpe'])}"
                            if pd.notna(row["rpe"]) and row["rpe"] > 0
                            else ""
                        )
                        notes_str = (
                            f"\n> 筆記: {row['workout_notes']}"
                            if pd.notna(row["workout_notes"])
                            and row["workout_notes"]
                            else ""
                        )
                        st.write(
                            f"**🏋️ {body_str}{row['item']}**{rpe_str} (🔥 {row['calories_burned']:.0f} kcal){notes_str}"
                        )
                    else:
                        st.write(
                            f"**🚴 {row['item']}** (🔥 {row['calories_burned']:.0f} kcal)"
                        )

                with col_edit:
                    if st.button("✏️ 編輯", key=f"btn_edit_workout_{w_id}"):
                        st.session_state[f"editing_workout_{w_id}"] = (
                            not st.session_state.get(
                                f"editing_workout_{w_id}", False
                            )
                        )
                with col_del:
                    if st.button("🗑️ 刪除", key=f"del_workout_{w_id}"):
                        delete_workout(w_id)
                        st.toast(f"已刪除：{row['item']}")
                        st.rerun()

                if st.session_state.get(f"editing_workout_{w_id}", False):
                    with st.form(key=f"form_edit_workout_{w_id}"):
                        st.caption(f"🛠️ 編輯運動紀錄 ID: {w_id}")
                        e_item = st.text_input("運動名稱", value=row["item"])

                        if w_type == "慢跑":
                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                e_dist = st.number_input(
                                    "距離 (km)",
                                    value=float(row["distance"])
                                    if pd.notna(row["distance"])
                                    else 0.0,
                                    step=0.1,
                                )
                                e_dur = st.number_input(
                                    "時間 (分鐘)",
                                    value=float(row["duration_min"])
                                    if pd.notna(row["duration_min"])
                                    else 0.0,
                                    step=1.0,
                                )
                                shoe_opts = [
                                    "Adidas Boston 13",
                                    "Adidas Adizero",
                                    "其他跑鞋",
                                    "不指定",
                                ]
                                curr_shoe_idx = (
                                    shoe_opts.index(row["shoe"])
                                    if row["shoe"] in shoe_opts
                                    else 3
                                )
                                e_shoe = st.selectbox(
                                    "使用跑鞋",
                                    shoe_opts,
                                    index=curr_shoe_idx,
                                )
                            with col_e2:
                                e_hr = st.number_input(
                                    "平均心率 (bpm)",
                                    value=int(row["avg_hr"])
                                    if pd.notna(row["avg_hr"])
                                    else 0,
                                    step=1,
                                )
                                e_cal = st.number_input(
                                    "消耗熱量 (kcal)",
                                    value=float(row["calories_burned"])
                                    if pd.notna(row["calories_burned"])
                                    else 0.0,
                                    step=10.0,
                                )

                            if st.form_submit_button("💾 儲存變更"):
                                update_workout(
                                    w_id,
                                    e_item.strip(),
                                    e_cal,
                                    "慢跑",
                                    distance=e_dist,
                                    duration_min=e_dur,
                                    avg_hr=e_hr,
                                    shoe=e_shoe,
                                )
                                st.session_state[f"editing_workout_{w_id}"] = (
                                    False
                                )
                                st.toast("慢跑紀錄已更新！")
                                st.rerun()

                        elif w_type == "重訓":
                            body_opts = [
                                "胸部",
                                "背部",
                                "腿部",
                                "肩部",
                                "手臂",
                                "核心",
                                "全身/其他",
                            ]
                            curr_body_idx = (
                                body_opts.index(row["body_part"])
                                if row["body_part"] in body_opts
                                else 6
                            )
                            e_body = st.selectbox(
                                "主要訓練部位",
                                body_opts,
                                index=curr_body_idx,
                            )
                            e_notes = st.text_area(
                                "動作與組數紀錄",
                                value=row["workout_notes"]
                                if pd.notna(row["workout_notes"])
                                else "",
                                height=100,
                            )

                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                e_rpe = st.slider(
                                    "自覺強度 (RPE 1-10)",
                                    min_value=1,
                                    max_value=10,
                                    value=int(row["rpe"])
                                    if pd.notna(row["rpe"])
                                    else 7,
                                )
                            with col_e2:
                                e_cal = st.number_input(
                                    "消耗熱量 (kcal)",
                                    value=float(row["calories_burned"])
                                    if pd.notna(row["calories_burned"])
                                    else 0.0,
                                    step=10.0,
                                )

                            if st.form_submit_button("💾 儲存變更"):
                                update_workout(
                                    w_id,
                                    e_item.strip(),
                                    e_cal,
                                    "重訓",
                                    body_part=e_body,
                                    workout_notes=e_notes,
                                    rpe=e_rpe,
                                )
                                st.session_state[f"editing_workout_{w_id}"] = (
                                    False
                                )
                                st.toast("重訓紀錄已更新！")
                                st.rerun()

                        else:
                            e_cal = st.number_input(
                                "消耗熱量 (kcal)",
                                value=float(row["calories_burned"])
                                if pd.notna(row["calories_burned"])
                                else 0.0,
                                step=10.0,
                            )
                            if st.form_submit_button("💾 儲存變更"):
                                update_workout(
                                    w_id, e_item.strip(), e_cal, "其他"
                                )
                                st.session_state[f"editing_workout_{w_id}"] = (
                                    False
                                )
                                st.toast("運動紀錄已更新！")
                                st.rerun()
                    st.divider()
        else:
            st.info("當天尚無運動紀錄。")

    # 3. 體重明細
    with list_tab3:
        if not weight_df.empty:
            w_row = weight_df.iloc[0]
            col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])
            with col_info:
                fat_disp = (
                    f" | 體脂: {w_row['body_fat']:.1f}%"
                    if "body_fat" in w_row and pd.notna(w_row["body_fat"])
                    else ""
                )
                note_disp = (
                    f" ({w_row['note']})" if w_row.get("note") else ""
                )
                st.write(
                    f"**⚖️ 體重: {w_row['weight']:.1f} kg**{fat_disp}{note_disp}"
                )
            with col_edit:
                if st.button("✏️ 編輯", key=f"btn_edit_weight_{date_str}"):
                    st.session_state[f"editing_weight_{date_str}"] = (
                        not st.session_state.get(
                            f"editing_weight_{date_str}", False
                        )
                    )
            with col_del:
                if st.button("🗑️ 刪除", key=f"del_weight_{date_str}"):
                    delete_weight_log(date_str)
                    st.toast(f"已刪除 {date_str} 的體重紀錄")
                    st.rerun()

            if st.session_state.get(f"editing_weight_{date_str}", False):
                with st.form(key=f"form_edit_weight_{date_str}"):
                    st.caption("🛠️ 編輯體重與體脂紀錄")
                    col_ew1, col_ew2 = st.columns(2)
                    with col_ew1:
                        ew_val = st.number_input(
                            "體重 (kg)",
                            value=float(w_row["weight"]),
                            step=0.1,
                        )
                    with col_ew2:
                        efat_val = st.number_input(
                            "體脂率 (%)",
                            value=float(w_row["body_fat"])
                            if (
                                "body_fat" in w_row
                                and pd.notna(w_row["body_fat"])
                            )
                            else 0.0,
                            step=0.1,
                        )
                    ew_note = st.text_input(
                        "備註",
                        value=w_row["note"]
                        if pd.notna(w_row["note"])
                        else "",
                    )

                    if st.form_submit_button("💾 儲存變更") and ew_val:
                        add_or_update_weight(
                            date_str,
                            ew_val,
                            efat_val if efat_val > 0 else None,
                            ew_note,
                        )
                        st.session_state[f"editing_weight_{date_str}"] = False
                        st.toast("體重紀錄已更新！")
                        st.rerun()
        else:
            st.info("當天尚無體重/體脂紀錄。")


def render_weekly_workout_summary(selected_date):
    st.markdown("### 🗓️ 週重訓與運動彙總")
    start_of_week = selected_date - timedelta(days=selected_date.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    conn = get_connection()
    query = """
        SELECT log_date, workout_type, item, body_part, calories_burned, rpe
        FROM workouts 
        WHERE log_date BETWEEN ? AND ?
        ORDER BY log_date ASC
    """
    df = pd.read_sql_query(
        query,
        conn,
        params=(
            start_of_week.strftime("%Y-%m-%d"),
            end_of_week.strftime("%Y-%m-%d"),
        ),
    )
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("本週尚無運動紀錄。")


def render_monthly_run_and_shoes(selected_date):
    st.markdown("### 👟 月跑量與跑鞋追蹤")
    month_start = selected_date.replace(day=1).strftime("%Y-%m-%d")

    conn = get_connection()
    df = pd.read_sql_query(
        """
        SELECT shoe, SUM(distance) as total_dist, COUNT(*) as run_count
        FROM workouts
        WHERE workout_type = '慢跑' AND log_date >= ?
        GROUP BY shoe
    """,
        conn,
        params=(month_start,),
    )
    conn.close()

    if not df.empty:
        st.dataframe(df, use_container_width=True)
    else:
        st.info("本月尚無慢跑紀錄。")


def render_weight_chart():
    st.markdown("### 📉 近 30 天體重與體脂趨勢圖")
    w_df = get_recent_weights(30)
    if not w_df.empty:
        chart_tab1, chart_tab2 = st.tabs(
            ["📉 體重趨勢 (kg)", "📉 體脂率趨勢 (%)"]
        )
        with chart_tab1:
            st.line_chart(w_df, x="log_date", y="weight", color="#5A738E")
        with chart_tab2:
            fat_df = w_df.dropna(subset=["body_fat"])
            if not fat_df.empty:
                st.line_chart(
                    fat_df, x="log_date", y="body_fat", color="#D97706"
                )
            else:
                st.info("近 30 天尚無體脂率紀錄數據。")
    else:
        st.info(
            "尚無體重紀錄，可在上方「新增紀錄 -> ⚖️ 體重與體脂」輸入數據。"
        )


def render_cal_chart():
    st.markdown("### 🔥 熱量與三大營養素趨勢")
    recent_logs_df, recent_workouts_df = get_recent_logs(days=7)
    today_dt = date.today()
    date_range = [
        (today_dt - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(6, -1, -1)
    ]

    food_summary = (
        recent_logs_df.groupby("log_date").sum().reindex(date_range).fillna(0)
        if not recent_logs_df.empty
        else pd.DataFrame(
            0,
            index=date_range,
            columns=["calories", "protein", "carbs", "fat"],
        )
    )

    if not recent_workouts_df.empty:
        workout_summary = (
            recent_workouts_df.groupby("log_date")
            .agg({"calories_burned": "sum", "distance": "sum"})
            .reindex(date_range)
            .fillna(0)
        )
    else:
        workout_summary = pd.DataFrame(
            0, index=date_range, columns=["calories_burned", "distance"]
        )

    daily_summary = food_summary.join(workout_summary).reset_index()
    daily_summary.rename(
        columns={
            "index": "日期",
            "log_date": "日期",
            "calories": "攝取熱量(kcal)",
            "calories_burned": "運動消耗(kcal)",
            "protein": "蛋白質(g)",
            "carbs": "碳水(g)",
            "fat": "脂肪(g)",
        },
        inplace=True,
    )

    st.line_chart(daily_summary, x="日期", y="攝取熱量(kcal)", color="#5A738E")
    st.line_chart(
        daily_summary, x="日期", y=["蛋白質(g)", "碳水(g)", "脂肪(g)"]
    )


# =============================================================================
# 2. 主程式流程與動態排序 (Main Program & Dynamic Sorting)
# =============================================================================


def main():
    st.set_page_config(
        page_title="個人健康與健身數據看板", page_icon="🏋️", layout="wide"
    )
    init_db()

    # --- 側邊欄設定 ---
    st.sidebar.title("⚙️ 系統設定")

    selected_date = st.sidebar.date_input("📅 選擇紀錄日期", value=date.today())
    date_str = selected_date.strftime("%Y-%m-%d")

    st.sidebar.divider()
    st.sidebar.subheader("🎯 每日營養目標")
    target_cal = st.sidebar.number_input(
        "目標熱量 (kcal)", value=2200, step=50
    )
    target_p = st.sidebar.number_input(
        "蛋白質目標 (g)", value=130.0, step=5.0
    )
    target_carbs = st.sidebar.number_input(
        "碳水目標 (g)", value=250.0, step=5.0
    )
    target_fat = st.sidebar.number_input("脂肪目標 (g)", value=60.0, step=5.0)

    # 恢復版面區塊排序功能
    st.sidebar.divider()
    with st.sidebar.expander("🧩 版面區塊排序設定", expanded=False):
        st.caption("數字越小越靠上顯示 (1~7)")
        pos_add = st.number_input("新增紀錄區塊", value=1, min_value=1, max_value=7)
        pos_prog = st.number_input("當日進度與目標", value=2, min_value=1, max_value=7)
        pos_logs = st.number_input("當日明細清單", value=3, min_value=1, max_value=7)
        pos_weekly = st.number_input("週重訓彙總表格", value=4, min_value=1, max_value=7)
        pos_shoes = st.number_input("月跑量與跑鞋追蹤", value=5, min_value=1, max_value=7)
        pos_weight = st.number_input("近30天體重體脂圖", value=6, min_value=1, max_value=7)
        pos_cal = st.number_input("熱量與營養趨勢圖", value=7, min_value=1, max_value=7)

    # 頂部抬頭
    st.title("🏋️ 個人健康 & 運動數據看板")

    # 區塊名稱對應渲染函式的字典
    section_mapping = {
        "新增紀錄區塊": (
            pos_add,
            lambda: render_add_records(date_str),
        ),
        "當日進度與目標": (
            pos_prog,
            lambda: render_daily_progress(
                date_str, target_cal, target_p, target_carbs, target_fat
            ),
        ),
        "當日明細清單": (pos_logs, lambda: render_daily_logs(date_str)),
        "週重訓彙總表格": (
            pos_weekly,
            lambda: render_weekly_workout_summary(selected_date),
        ),
        "月跑量與跑鞋追蹤": (
            pos_shoes,
            lambda: render_monthly_run_and_shoes(selected_date),
        ),
        "近30天體重體脂圖": (pos_weight, render_weight_chart),
        "熱量與營養趨勢圖": (pos_cal, render_cal_chart),
    }

    # 根據使用者輸入的數字進行排序 (自訂數字小到大)
    sorted_sections = sorted(section_mapping.items(), key=lambda x: x[1][0])

    # 依排序結果進行動態渲染
    for name, (_, render_func) in sorted_sections:
        render_func()
        st.divider()


if __name__ == "__main__":
    main()
