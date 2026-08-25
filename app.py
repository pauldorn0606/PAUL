from datetime import date, timedelta
import calendar
import altair as alt
import pandas as pd
import streamlit as st

# =============================================================================
# 0. 假資料與資料庫介面模擬 (請替換為您現有的 DB 存取函式)
# =============================================================================


def get_logs_by_date(d_str):
    return pd.DataFrame(columns=["id", "item", "calories", "protein", "carbs", "fat"])


def get_workouts_by_date(d_str):
    return pd.DataFrame(
        columns=[
            "id",
            "item",
            "workout_type",
            "distance",
            "duration_min",
            "avg_hr",
            "shoe",
            "body_part",
            "rpe",
            "calories_burned",
            "workout_notes",
        ]
    )


def get_weight_by_date(d_str):
    return pd.DataFrame(columns=["weight", "body_fat", "note"])


def get_weekly_workout_summary(s_date):
    start_w = s_date - timedelta(days=s_date.weekday())
    end_w = start_w + timedelta(days=6)
    return pd.DataFrame(), start_w, end_w


def get_monthly_running_distance(s_date):
    return 0.0, 0


def get_shoe_mileage():
    return pd.DataFrame(columns=["shoe", "total_dist"])


def get_recent_weights(days):
    return pd.DataFrame(columns=["log_date", "weight", "body_fat"])


def get_recent_logs(days):
    return pd.DataFrame(), pd.DataFrame()


def get_running_history():
    return pd.DataFrame()


def calculate_pace(dist, dur):
    if not dist or dist <= 0:
        return "N/A"
    total_sec = dur * 60
    pace_sec = total_sec / dist
    m, s = divmod(int(pace_sec), 60)
    return f"{m}'{s:02d}\""


def add_workout(*args, **kwargs):
    pass


def add_or_update_weight(*args, **kwargs):
    pass


def update_log(*args, **kwargs):
    pass


def delete_log(*args, **kwargs):
    pass


def update_workout(*args, **kwargs):
    pass


def delete_workout(*args, **kwargs):
    pass


def delete_weight_log(*args, **kwargs):
    pass


# =============================================================================
# 1. 頁面初始化與日期選擇 (自動切換至今日)
# =============================================================================

st.set_page_config(page_title="健康與健身紀錄", layout="wide")

# 在側邊欄建立日期選擇器，預設值設定為今天 (date.today())
with st.sidebar:
    st.header("📅 日期選擇")

    # 關鍵修改：預設帶入 date.today()，讓程式每次啟動/重新載入時都自動定位在今天
    selected_date = st.date_input("選擇紀錄/查閱日期", value=date.today())

    # 格式化日期字串 (YYYY-MM-DD)
    date_str = selected_date.strftime("%Y-%m-%d")

    # 一鍵回到今天按鈕 (提升使用者體驗)
    if st.button("🔄 重置為今天", use_container_width=True):
        st.rerun()

    st.divider()
    st.caption(f"目前選擇日期：**{date_str}**")

# 目標數值設定 (可根據需求動態計算或自設)
target_cal = 2200.0
target_p = 140.0
target_carbs = 250.0
target_fat = 60.0


# =============================================================================
# 2. 各區塊 UI 渲染函式
# =============================================================================


def render_add_records(selected_date, date_str):
    st.subheader(f"➕ 新增紀錄 ({date_str})")

    tab_food, tab_sport, tab_weight = st.tabs(
        ["🍱 新增飲食", "🏃 新增運動", "⚖️ 體重與體脂"]
    )

    with tab_sport:
        sport_type = st.radio("運動類型", ["重訓/健身", "其他運動"], horizontal=True)

        if sport_type == "重訓/健身":
            with st.form("gym_form"):
                body_part_in = st.selectbox(
                    "訓練部位",
                    ["胸部", "背部", "腿部", "肩部", "手臂", "核心", "全身/其他"],
                )
                workout_name = st.text_input("運動/項目名稱", value="重訓")
                rpe_in = st.slider("自覺強度 (RPE 1-10)", 1, 10, 7)
                notes_in = st.text_area(
                    "動作與組數筆記", placeholder="如：深蹲 100kg 5x5", height=80
                )
                cal_burned_in = st.number_input(
                    "估計消耗熱量 (kcal)",
                    min_value=0.0,
                    value=None,
                    placeholder="0",
                    step=10.0,
                )

                submit_workout = st.form_submit_button(
                    "加入重訓紀錄", use_container_width=True
                )
                if submit_workout:
                    b_val = cal_burned_in if cal_burned_in is not None else 0.0
                    add_workout(
                        date_str,
                        workout_name,
                        b_val,
                        "重訓",
                        body_part=body_part_in,
                        workout_notes=notes_in,
                        rpe=rpe_in,
                    )
                    st.toast(f"已加入重訓紀錄：{body_part_in}")
                    st.rerun()
        else:
            with st.form("other_sport_form"):
                workout_name = st.text_input("運動名稱", value="")
                cal_burned_in = st.number_input(
                    "消耗熱量 (kcal)",
                    min_value=0.0,
                    value=None,
                    placeholder="0",
                    step=10.0,
                )
                submit_workout = st.form_submit_button(
                    "加入運動紀錄", use_container_width=True
                )
                if submit_workout:
                    b_val = cal_burned_in if cal_burned_in is not None else 0.0
                    display_w = (
                        workout_name.strip()
                        if workout_name.strip()
                        else "一般運動"
                    )
                    add_workout(date_str, display_w, b_val, "其他")
                    st.toast(f"已加入運動紀錄：{display_w}")
                    st.rerun()

    with tab_weight:
        curr_w_df = get_weight_by_date(date_str)
        curr_w = (
            curr_w_df["weight"].iloc[0]
            if not curr_w_df.empty and pd.notna(curr_w_df["weight"].iloc[0])
            else None
        )
        curr_fat = (
            curr_w_df["body_fat"].iloc[0]
            if not curr_w_df.empty
            and "body_fat" in curr_w_df.columns
            and pd.notna(curr_w_df["body_fat"].iloc[0])
            else None
        )
        curr_note = (
            curr_w_df["note"].iloc[0]
            if not curr_w_df.empty and pd.notna(curr_w_df["note"].iloc[0])
            else ""
        )

        with st.form("weight_form"):
            col_w1, col_w2 = st.columns(2)
            with col_w1:
                w_input = st.number_input(
                    "今日體重 (kg)",
                    min_value=30.0,
                    max_value=200.0,
                    value=float(curr_w) if curr_w else None,
                    placeholder="如 62.5",
                    step=0.1,
                )
            with col_w2:
                fat_input = st.number_input(
                    "體脂率 (%)",
                    min_value=3.0,
                    max_value=60.0,
                    value=float(curr_fat) if curr_fat else None,
                    placeholder="如 15.2",
                    step=0.1,
                )

            w_note = st.text_input(
                "備註 (如: 早晨空腹/運動後)", value=curr_note
            )
            submit_weight = st.form_submit_button(
                "💾 儲存體重與體脂紀錄", use_container_width=True
            )

            if submit_weight and w_input:
                add_or_update_weight(date_str, w_input, fat_input, w_note)
                st.toast(
                    f"已更新 {date_str} 體重：{w_input} kg"
                    + (f", 體脂：{fat_input}%" if fat_input else "")
                )
                st.rerun()


def render_daily_progress(selected_date, date_str):
    logs_df = get_logs_by_date(date_str)
    consumed_cal = logs_df["calories"].sum() if not logs_df.empty else 0.0
    consumed_p = logs_df["protein"].sum() if not logs_df.empty else 0.0
    consumed_carbs = logs_df["carbs"].sum() if not logs_df.empty else 0.0
    consumed_f = logs_df["fat"].sum() if not logs_df.empty else 0.0

    st.subheader(f"📊 {date_str} 攝取進度與目標")

    weight_df = get_weight_by_date(date_str)
    if not weight_df.empty:
        w_val = weight_df["weight"].iloc[0]
        fat_val = (
            weight_df["body_fat"].iloc[0]
            if "body_fat" in weight_df.columns
            and pd.notna(weight_df["body_fat"].iloc[0])
            else None
        )
        fat_str = f" | 體脂率：**{fat_val:.1f}%**" if fat_val else ""
        st.info(f"⚖️ **{date_str} 紀錄數據**：體重 **{w_val:.1f} kg**{fat_str}")

    rem_cal = target_cal - consumed_cal
    rem_p = target_p - consumed_p
    rem_carbs = target_carbs - consumed_carbs
    rem_f = target_fat - consumed_f

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "熱量剩餘",
        f"{rem_cal:.0f} kcal",
        delta=f"已攝取 {consumed_cal:.0f}",
    )
    m2.metric(
        "蛋白質剩餘", f"{rem_p:.1f} g", delta=f"已攝取 {consumed_p:.1f}"
    )
    m3.metric(
        "碳水剩餘",
        f"{rem_carbs:.1f} g",
        delta=f"已攝取 {consumed_carbs:.1f}",
    )
    m4.metric(
        "脂肪剩餘", f"{rem_f:.1f} g", delta=f"已攝取 {consumed_f:.1f}"
    )


def render_weekly_workout_summary(selected_date, date_str):
    st.subheader("🏋️ 本週重訓健身紀錄表格")
    weekly_df, start_w, end_w = get_weekly_workout_summary(selected_date)

    st.caption(
        f"📅 **本週區間**：{start_w.strftime('%Y-%m-%d')} (週一) 至 {end_w.strftime('%Y-%m-%d')} (週日)"
    )

    if not weekly_df.empty:
        st.dataframe(
            weekly_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "動作與組數筆記": st.column_config.TextColumn(
                    "動作與組數筆記", width="large"
                )
            },
        )
    else:
        st.info(
            "本週尚無重訓健身紀錄。可以在「新增紀錄 -> 🏃 新增運動 -> 🏋️ 重訓/健身」輸入紀錄！"
        )


def render_monthly_run_and_shoes(selected_date, date_str):
    monthly_dist, run_count = get_monthly_running_distance(selected_date)
    last_day_of_month = calendar.monthrange(
        selected_date.year, selected_date.month
    )[1]

    st.subheader("🏃 月跑量統計與跑鞋履歷")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.markdown(
            f"#### 📅 {selected_date.year} 年 {selected_date.month} 月跑量"
        )
        m_c1, m_c2 = st.columns(2)
        m_c1.metric("當月累積跑量", f"{monthly_dist:.2f} km")
        m_c2.metric("當月跑步次數", f"{run_count} 次")
        st.caption(
            f"統計區間：{selected_date.year}-{selected_date.month:02d}-01 至 {selected_date.year}-{selected_date.month:02d}-{last_day_of_month:02d}"
        )

    with col_right:
        st.markdown("#### 👟 跑鞋退役里程追蹤 (全歷史)")
        shoe_df = get_shoe_mileage()
        if not shoe_df.empty:
            for _, row in shoe_df.iterrows():
                s_name = row["shoe"]
                s_dist = row["total_dist"]
                st.write(f"**{s_name}**: {s_dist:.1f} km / 600 km")
                st.progress(min(s_dist / 600.0, 1.0))
        else:
            st.info("尚無跑鞋里程紀錄。")


def render_daily_logs(selected_date, date_str):
    logs_df = get_logs_by_date(date_str)
    workouts_df = get_workouts_by_date(date_str)
    weight_df = get_weight_by_date(date_str)

    st.subheader(f"📝 {date_str} 明細清單")
    list_tab1, list_tab2, list_tab3 = st.tabs([
        f"🍱 飲食明細 ({len(logs_df)})",
        f"🏃 運動明細 ({len(workouts_df)})",
        f"⚖️ 體重/體脂 ({len(weight_df)})",
    ])

    with list_tab1:
        if not logs_df.empty:
            for _, row in logs_df.iterrows():
                log_id = row["id"]
                col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])
                with col_info:
                    st.write(
                        f"**• {row['item']}** — "
                        f"{row['calories']:.0f} kcal | "
                        f"P: {row['protein']:.1f}g | "
                        f"C: {row['carbs']:.1f}g | "
                        f"F: {row['fat']:.1f}g"
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
                        delete_log(log_id)
                        st.toast(f"已刪除飲食：{row['item']}")
                        st.rerun()

                if st.session_state.get(f"editing_food_{log_id}", False):
                    with st.form(key=f"form_edit_food_{log_id}"):
                        st.caption(f"🛠️ 編輯飲食紀錄 (ID: {log_id})")
                        e_item = st.text_input("品項名稱", value=row["item"])
                        col_e1, col_e2 = st.columns(2)
                        with col_e1:
                            e_cal = st.number_input(
                                "熱量 (kcal)",
                                value=float(row["calories"]),
                                step=5.0,
                            )
                            e_p = st.number_input(
                                "蛋白質 (g)",
                                value=float(row["protein"]),
                                step=1.0,
                            )
                        with col_e2:
                            e_carbs = st.number_input(
                                "碳水 (g)",
                                value=float(row["carbs"]),
                                step=1.0,
                            )
                            e_fat = st.number_input(
                                "脂肪 (g)",
                                value=float(row["fat"]),
                                step=1.0,
                            )

                        btn_save_food = st.form_submit_button("💾 儲存變更")
                        if btn_save_food:
                            update_log(
                                log_id, e_item.strip(), e_cal, e_p, e_carbs, e_fat
                            )
                            st.session_state[f"editing_food_{log_id}"] = False
                            st.toast("飲食紀錄已更新！")
                            st.rerun()
                    st.divider()
        else:
            st.info("當天尚無飲食紀錄。")

    with list_tab2:
        if not workouts_df.empty:
            for _, row in workouts_df.iterrows():
                w_id = row["id"]
                w_type = row.get("workout_type", "其他")

                col_info, col_edit, col_del = st.columns([3.5, 0.8, 0.8])
                with col_info:
                    if w_type == "慢跑":
                        pace = calculate_pace(
                            row["distance"], row["duration_min"]
                        )
                        shoe_str = (
                            f" | 👟 {row['shoe']}" if row.get("shoe") else ""
                        )
                        st.write(
                            f"**🏃 {row['item']}** — "
                            f"**{row['distance'] or 0:.2f} km** | "
                            f"配速: **{pace}** | "
                            f"時間: {row['duration_min'] or 0:.0f}分 | "
                            f"心率: {row['avg_hr'] or '-'} bpm"
                            f"{shoe_str}"
                        )
                    elif w_type == "重訓":
                        notes_str = (
                            f"\n> {row['workout_notes'].replace(chr(10), ' / ')}"
                            if row.get("workout_notes")
                            else ""
                        )
                        st.write(
                            f"**🏋️ {row['item']} ({row['body_part'] or '未設定'})** — "
                            f"RPE: **{row['rpe'] or '-'}** | "
                            f"消耗: {row['calories_burned']:.0f} kcal"
                            f"{notes_str}"
                        )
                    else:
                        st.write(
                            f"**• {row['item']}** — 消耗 **{row['calories_burned']:.0f}** kcal"
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
                        st.toast("已刪除運動紀錄")
                        st.rerun()

                if st.session_state.get(f"editing_workout_{w_id}", False):
                    with st.form(key=f"form_edit_workout_{w_id}"):
                        st.caption(f"🛠️ 編輯運動紀錄 (ID: {w_id})")
                        e_item = st.text_input("運動名稱", value=row["item"])

                        if w_type == "慢跑":
                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                e_dist = st.number_input(
                                    "距離 (km)",
                                    value=(
                                        float(row["distance"])
                                        if pd.notna(row["distance"])
                                        else 0.0
                                    ),
                                    step=0.1,
                                )
                                e_dur = st.number_input(
                                    "時間 (分鐘)",
                                    value=(
                                        float(row["duration_min"])
                                        if pd.notna(row["duration_min"])
                                        else 0.0
                                    ),
                                    step=1.0,
                                )
                                shoe_opts = [
                                    "Adidas Boston 13",
                                    "Adidas Adizero",
                                    "Ricoh / 其他",
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
                                    value=(
                                        int(row["avg_hr"])
                                        if pd.notna(row["avg_hr"])
                                        else 0
                                    ),
                                    step=1,
                                )
                                e_cal = st.number_input(
                                    "消耗熱量 (kcal)",
                                    value=(
                                        float(row["calories_burned"])
                                        if pd.notna(row["calories_burned"])
                                        else 0.0
                                    ),
                                    step=10.0,
                                )

                            btn_save_w = st.form_submit_button("💾 儲存變更")
                            if btn_save_w:
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
                                st.session_state[
                                    f"editing_workout_{w_id}"
                                ] = False
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
                                value=(
                                    row["workout_notes"]
                                    if pd.notna(row["workout_notes"])
                                    else ""
                                ),
                                height=100,
                            )

                            col_e1, col_e2 = st.columns(2)
                            with col_e1:
                                e_rpe = st.slider(
                                    "自覺強度 (RPE 1-10)",
                                    min_value=1,
                                    max_value=10,
                                    value=(
                                        int(row["rpe"])
                                        if pd.notna(row["rpe"])
                                        else 7
                                    ),
                                )
                            with col_e2:
                                e_cal = st.number_input(
                                    "消耗熱量 (kcal)",
                                    value=(
                                        float(row["calories_burned"])
                                        if pd.notna(row["calories_burned"])
                                        else 0.0
                                    ),
                                    step=10.0,
                                )

                            btn_save_w = st.form_submit_button("💾 儲存變更")
                            if btn_save_w:
                                update_workout(
                                    w_id,
                                    e_item.strip(),
                                    e_cal,
                                    "重訓",
                                    body_part=e_body,
                                    workout_notes=e_notes,
                                    rpe=e_rpe,
                                )
                                st.session_state[
                                    f"editing_workout_{w_id}"
                                ] = False
                                st.toast("重訓紀錄已更新！")
                                st.rerun()

                        else:
                            e_cal = st.number_input(
                                "消耗熱量 (kcal)",
                                value=(
                                    float(row["calories_burned"])
                                    if pd.notna(row["calories_burned"])
                                    else 0.0
                                ),
                                step=10.0,
                            )
                            btn_save_w = st.form_submit_button("💾 儲存變更")
                            if btn_save_w:
                                update_workout(
                                    w_id, e_item.strip(), e_cal, "其他"
                                )
                                st.session_state[
                                    f"editing_workout_{w_id}"
                                ] = False
                                st.toast("運動紀錄已更新！")
                                st.rerun()
                    st.divider()
        else:
            st.info("當天尚無運動紀錄。")

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
                            "體重 (kg)", value=float(w_row["weight"]), step=0.1
                        )
                    with col_ew2:
                        efat_val = st.number_input(
                            "體脂率 (%)",
                            value=(
                                float(w_row["body_fat"])
                                if (
                                    "body_fat" in w_row
                                    and pd.notna(w_row["body_fat"])
                                )
                                else None
                            ),
                            step=0.1,
                        )
                    ew_note = st.text_input(
                        "備註",
                        value=(
                            w_row["note"] if pd.notna(w_row["note"]) else ""
                        ),
                    )

                    btn_save_weight = st.form_submit_button("💾 儲存變更")
                    if btn_save_weight and ew_val:
                        add_or_update_weight(
                            date_str, ew_val, efat_val, ew_note
                        )
                        st.session_state[f"editing_weight_{date_str}"] = False
                        st.toast("體重紀錄已更新！")
                        st.rerun()
        else:
            st.info("當天尚無體重/體脂紀錄。")


def render_weight_chart(selected_date, date_str):
    st.markdown("#### ⚖️ 近 30 天體重與體脂趨勢圖")
    w_df = get_recent_weights(30)
    if not w_df.empty:
        chart_tab1, chart_tab2 = st.tabs(["📉 體重趨勢 (kg)", "% 體脂率趨勢 (%)"])
        with chart_tab1:
            st.line_chart(w_df, x="log_date", y="weight", color="#5A738E")
        with chart_tab2:
            fat_df = w_df.dropna(subset=["body_fat"])
            if not fat_df.empty:
                st.line_chart(fat_df, x="log_date", y="body_fat", color="#D97706")
            else:
                st.info("近 30 天尚無體脂率紀錄數據。")
    else:
        st.info("尚無體重紀錄，可在上方「新增紀錄 -> ⚖️ 體重與體脂」輸入數據。")


def render_cal_chart(selected_date, date_str):
    st.markdown("#### 🔥 熱量與三大營養素趨勢")
    recent_logs_df, recent_workouts_df = get_recent_logs(days=7)
    today_dt = date.today()
    date_range = [
        (today_dt - timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(6, -1, -1)
    ]

    food_summary = (
        recent_logs_df.groupby("log_date")
        .sum()
        .reindex(date_range)
        .fillna(0)
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
    st.line_chart(daily_summary, x="日期", y=["蛋白質(g)", "碳水(g)", "脂肪(g)"])


def render_pace_hr_chart(selected_date, date_str):
    st.markdown("#### 🏃 慢跑心率 vs. 配速散佈圖 (心肺效率)")
    run_hist_df = get_running_history()
    if not run_hist_df.empty and run_hist_df["avg_hr"].notna().any():
        st.caption(
            "💡 右下方代表相同心率下配速更快。滑鼠移至點點上可查閱詳細日期與紀錄。"
        )
        scatter_chart = (
            alt.Chart(run_hist_df)
            .mark_circle(size=90)
            .encode(
                x=alt.X(
                    "avg_hr:Q",
                    title="平均心率 (bpm)",
                    scale=alt.Scale(zero=False),
                ),
                y=alt.Y(
                    "pace_decimal:Q",
                    title="配速 (分鐘/km)",
                    scale=alt.Scale(zero=False, reverse=True),
                ),
                color=alt.Color("shoe:N", title="跑鞋"),
                tooltip=[
                    alt.Tooltip("log_date:N", title="日期"),
                    alt.Tooltip("item:N", title="項目"),
                    alt.Tooltip("distance:Q", title="距離 (km)", format=".2f"),
                    alt.Tooltip("配速:N", title="配速"),
                    alt.Tooltip("avg_hr:Q", title="平均心率 (bpm)"),
                ],
            )
            .interactive()
        )
        st.altair_chart(scatter_chart, use_container_width=True)
    else:
        st.info("尚無包含平均心率的慢跑紀錄數據。")


# =============================================================================
# 3. 區塊動態分流渲染
# =============================================================================

# 可自由自訂區塊順序
ordered_sections = [
    "當日攝取進度與目標",
    "新增紀錄區塊",
    "當日明細清單",
    "週重訓彙總表格",
    "月跑量與跑鞋追蹤",
    "近30天體重與體脂趨勢圖",
    "熱量與營養趨勢圖",
    "慢跑心率 vs. 配速散佈圖",
]

section_mapping = {
    "新增紀錄區塊": render_add_records,
    "當日攝取進度與目標": render_daily_progress,
    "週重訓彙總表格": render_weekly_workout_summary,
    "月跑量與跑鞋追蹤": render_monthly_run_and_shoes,
    "當日明細清單": render_daily_logs,
    "近30天體重與體脂趨勢圖": render_weight_chart,
    "熱量與營養趨勢圖": render_cal_chart,
    "慢跑心率 vs. 配速散佈圖": render_pace_hr_chart,
}

# 依序呼叫並傳入 selected_date 與 date_str 參數
for sec_name in ordered_sections:
    if sec_name in section_mapping:
        section_mapping[sec_name](selected_date, date_str)
        st.divider()
