from datetime import date, timedelta
import altair as alt
import pandas as pd
import streamlit as st

# 假設已從資料庫層載入以下輔助函式 (保留原程式結構)
# init_db, calculate_pace, delete_workout, update_workout, delete_weight_log,
# add_or_update_weight, get_recent_weights, get_recent_logs, get_running_history,
# delete_food_log, update_food_log, get_daily_food_logs, get_daily_workouts, get_daily_weight, etc.


# =============================================================================
# 區塊渲染函式群
# =============================================================================


def render_add_records(date_str):
    """新增紀錄區塊 (請依原有的輸入表單邏輯串接)"""
    st.markdown("### 📝 新增紀錄")
    # 此處保留您原有的新增飲食/運動/體重表單 UI
    st.caption(f"目前選擇日期：{date_str}")


def render_daily_progress(
    date_str, target_cal, target_p, target_carbs, target_fat
):
    """當日攝取進度與目標 (包含體重體脂資訊)"""
    st.markdown("### 📊 當日攝取進度與目標")

    # 取得當天資料
    food_df = get_daily_food_logs(date_str)
    weight_df = get_daily_weight(date_str)

    tot_cal = food_df["calories"].sum() if not food_df.empty else 0.0
    tot_p = food_df["protein"].sum() if not food_df.empty else 0.0
    tot_c = food_df["carbs"].sum() if not food_df.empty else 0.0
    tot_f = food_df["fat"].sum() if not food_df.empty else 0.0

    # 體重體脂字串格式化
    if not weight_df.empty:
        w_row = weight_df.iloc[0]
        w_val = (
            f"{w_row['weight']:.1f} kg"
            if pd.notna(w_row.get("weight"))
            else "未紀錄"
        )
        fat_val = (
            f"{w_row['body_fat']:.1f} %"
            if "body_fat" in w_row and pd.notna(w_row["body_fat"])
            else "未紀錄"
        )
        weight_disp = f"{w_val} / {fat_val}"
    else:
        weight_disp = "未紀錄"

    # 指標欄位展示 (包含新增的體重體脂欄位)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric(
            "🔥 熱量攝取",
            f"{tot_cal:.0f} kcal",
            delta=f"{tot_cal - target_cal:.0f} kcal",
        )
        st.progress(min(1.0, tot_cal / target_cal if target_cal > 0 else 0.0))
    with col2:
        st.metric(
            "🥩 蛋白質",
            f"{tot_p:.1f} g",
            delta=f"{tot_p - target_p:.1f} g",
        )
        st.progress(min(1.0, tot_p / target_p if target_p > 0 else 0.0))
    with col3:
        st.metric(
            "🍚 碳水化合物",
            f"{tot_c:.1f} g",
            delta=f"{tot_c - target_carbs:.1f} g",
        )
        st.progress(min(1.0, tot_c / target_carbs if target_carbs > 0 else 0.0))
    with col4:
        st.metric(
            "🥑 脂肪",
            f"{tot_f:.1f} g",
            delta=f"{tot_f - target_fat:.1f} g",
        )
        st.progress(min(1.0, tot_f / target_fat if target_fat > 0 else 0.0))
    with col5:
        st.metric("⚖️ 當日體重 / 體脂", weight_disp)


def render_daily_logs(date_str):
    """當日明細清單"""
    st.markdown("### 📋 當日明細清單")
    food_df = get_daily_food_logs(date_str)
    workouts_df = get_daily_workouts(date_str)
    weight_df = get_daily_weight(date_str)

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
                        f"**{row['meal_type']} | {row['item']}** — {row['calories']:.0f} kcal (🥩 {row['protein']:.1f}g | 🍚 {row['carbs']:.1f}g | 🥑 {row['fat']:.1f}g)"
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
                        e_item = st.text_input("食物名稱", value=row["item"])
                        col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                        with col_e1:
                            e_cal = st.number_input(
                                "熱量 (kcal)",
                                value=float(row["calories"]),
                                step=10.0,
                            )
                        with col_e2:
                            e_p = st.number_input(
                                "蛋白質 (g)",
                                value=float(row["protein"]),
                                step=1.0,
                            )
                        with col_e3:
                            e_c = st.number_input(
                                "碳水 (g)",
                                value=float(row["carbs"]),
                                step=1.0,
                            )
                        with col_e4:
                            e_f = st.number_input(
                                "脂肪 (g)",
                                value=float(row["fat"]),
                                step=1.0,
                            )

                        if st.form_submit_button("💾 儲存變更"):
                            update_food_log(
                                log_id, e_item.strip(), e_cal, e_p, e_c, e_f
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
                            if pd.notna(row["shoe"])
                            else ""
                        )
                        st.write(
                            f"**🏃 {row['item']}** — {row['distance']:.2f} km | 配速: {pace_str} | 時間: {row['duration_min']:.0f} 分鐘{hr_str}{shoe_str} (🔥 {row['calories_burned']:.0f} kcal)"
                        )
                    elif w_type == "重訓":
                        body_str = (
                            f"[{row['body_part']}] "
                            if pd.notna(row["body_part"])
                            else ""
                        )
                        rpe_str = (
                            f" | RPE: {int(row['rpe'])}"
                            if pd.notna(row["rpe"])
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
                            else None,
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
                            date_str, ew_val, efat_val, ew_note
                        )
                        st.session_state[f"editing_weight_{date_str}"] = False
                        st.toast("體重紀錄已更新！")
                        st.rerun()
        else:
            st.info("當天尚無體重/體脂紀錄。")


def render_weekly_workout_summary(selected_date):
    """週重訓彙總表格"""
    st.markdown("### 🏋️ 週重訓彙總")
    # 此處保留您原本的週重訓統計渲染邏輯


def render_monthly_run_and_shoes(selected_date):
    """月跑量與跑鞋追蹤"""
    st.markdown("### 🏃 月跑量與跑鞋追蹤")
    # 此處保留您原本的月跑量與跑鞋統計渲染邏輯


def render_weight_chart():
    """近 30 天體重與體脂趨勢圖"""
    st.markdown("#### ⚖️ 近 30 天體重與體脂趨勢圖")
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
    """熱量與三大營養素趨勢"""
    st.markdown("#### 🔥 熱量與三大營養素趨勢")
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
# 主程式流程與動態分流渲染 (Main Program)
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

    # 恢復數字編輯欄位順序功能
    st.sidebar.divider()
    with st.sidebar.expander("📐 版面區塊順序設定", expanded=False):
        st.caption("調整下方數字即可自訂主畫面的區塊上下順序：")
        sec_order = {
            "新增紀錄區塊": st.number_input(
                "新增紀錄區塊", value=1, min_value=1, max_value=7
            ),
            "當日攝取進度與目標": st.number_input(
                "當日攝取進度與目標", value=2, min_value=1, max_value=7
            ),
            "當日明細清單": st.number_input(
                "當日明細清單", value=3, min_value=1, max_value=7
            ),
            "週重訓彙總表格": st.number_input(
                "週重訓彙總表格", value=4, min_value=1, max_value=7
            ),
            "月跑量與跑鞋追蹤": st.number_input(
                "月跑量與跑鞋追蹤", value=5, min_value=1, max_value=7
            ),
            "近30天體重與體脂趨勢圖": st.number_input(
                "近30天體重與體脂趨勢圖", value=6, min_value=1, max_value=7
            ),
            "熱量與營養趨勢圖": st.number_input(
                "熱量與營養趨勢圖", value=7, min_value=1, max_value=7
            ),
        }

    # 頂部抬頭
    st.title("🏋️ 個人健康 & 運動數據看板")

    # 區塊與對應渲染函式的映射字典 (已移除慢跑心率 vs. 配速散佈圖)
    section_mapping = {
        "新增紀錄區塊": lambda: render_add_records(date_str),
        "當日攝取進度與目標": lambda: render_daily_progress(
            date_str, target_cal, target_p, target_carbs, target_fat
        ),
        "週重訓彙總表格": lambda: render_weekly_workout_summary(
            selected_date
        ),
        "月跑量與跑鞋追蹤": lambda: render_monthly_run_and_shoes(
            selected_date
        ),
        "當日明細清單": lambda: render_daily_logs(date_str),
        "近30天體重與體脂趨勢圖": render_weight_chart,
        "熱量與營養趨勢圖": render_cal_chart,
    }

    # 根據側邊欄設定的數字大小進行排序
    ordered_sections = sorted(sec_order.keys(), key=lambda x: sec_order[x])

    # 依序渲染各個模組
    for sec_name in ordered_sections:
        if sec_name in section_mapping:
            section_mapping[sec_name]()
            st.divider()


if __name__ == "__main__":
    main()
