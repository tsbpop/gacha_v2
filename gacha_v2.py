import streamlit as st
import pandas as pd
import random
import math

st.set_page_config(page_title="🎮 뽑기+합성 기대비용 시뮬레이터", layout="wide")
st.title("🎯 뽑기+합성 기대비용 시뮬레이터")

uploaded_file = st.file_uploader("🎲 확률표 엑셀 업로드 (등급, 구성품, 확률)", type="xlsx")

if uploaded_file:
    try:
        df = pd.read_excel(uploaded_file)
        if df["확률"].max() <= 1:
            df["확률"] *= 100
        df = df.sort_values(by="확률", ascending=False).reset_index(drop=True)
        df["누적확률"] = df["확률"].cumsum()

        st.success("✅ 확률표 로드 완료")
        st.dataframe(df)

        st.subheader("🎰 뽑기 설정")
        draw_cost = st.number_input("11회 뽑기 비용 (원)", min_value=0, value=27500)
        pity_S = st.number_input("S등급 천장 (회)", min_value=1, value=100)
        pity_R = st.number_input("R등급 천장 (회)", min_value=1, value=500)

        st.subheader("🔨 합성 설정")
        synth_rates = {}
        synth_pities = {}
        default_rates = {"C": 25, "B": 21, "A": 18, "S": 16, "R": 15}
        default_pities = {"A": 20, "S": 15, "R": 10}
        grades = ["C", "B", "A", "S", "R"]

        for grade in grades:
            synth_rates[grade] = st.number_input(
                f"{grade} > 상위 등급 확률 (%)", min_value=0, max_value=100, value=default_rates[grade]
            )

        for grade, pity_default in default_pities.items():
            synth_pities[grade] = st.number_input(
                f"{grade} > 상위 등급 합성 천장 (회)", min_value=1, value=pity_default
            )

        sim_count = st.number_input("🔁 시뮬레이션 반복 횟수", min_value=1, value=1000)

        st.header("등급별 개별 시뮬레이션")

        target_grades = ["A", "S", "R"]

        if st.button("시뮬레이션 시작"):
            with st.spinner("시뮬레이션 진행 중..."):
                final_results = {g: [] for g in target_grades + ["SR"]}
                synth_log_total = {g: {"try": 0, "success": 0} for g in ["A", "S", "R"]}

                for _ in range(sim_count):
                    results = {}
                    for goal in target_grades:
                        obtained = {g: 0 for g in grades}
                        synth_inventory = {g: 0 for g in grades}
                        synth_pity_counter = {g: 0 for g in ["A", "S", "R"]}
                        local_log = {g: {"try": 0, "success": 0} for g in ["A", "S", "R"]}
                        draw_count = 0

                        while obtained[goal] < 1:
                            draw_count += 1

                            if goal == "R" and draw_count % pity_R == 0:
                                grade = "R"
                            elif goal == "S" and draw_count % pity_S == 0:
                                grade = "S"
                            else:
                                rand = random.uniform(0, 100)
                                item = df[df["누적확률"] > rand].iloc[0]
                                grade = item["등급"]

                            if grade in obtained:
                                obtained[grade] += 1
                            elif grade in synth_inventory:
                                synth_inventory[grade] += 1

                            changed = True
                            while changed:
                                changed = False
                                for g in grades[:-1]:
                                    if g in ["C", "B"]:
                                        pity_limit = 999999
                                    else:
                                        pity_limit = synth_pities[g]

                                    next_g = grades[grades.index(g) + 1]
                                    while synth_inventory[g] >= 4:
                                        synth_inventory[g] -= 4
                                        if g not in ["C", "B"]:
                                            synth_pity_counter[g] += 1
                                            local_log[g]["try"] += 1

                                        is_success = (
                                            random.randint(1, 100) <= synth_rates[g]
                                            or (g not in ["C", "B"] and synth_pity_counter[g] >= pity_limit)
                                        )

                                        if is_success:
                                            if g not in ["C", "B"]:
                                                synth_pity_counter[g] = 0
                                                local_log[g]["success"] += 1

                                            if next_g in obtained:
                                                obtained[next_g] += 1
                                            else:
                                                synth_inventory[next_g] += 1
                                        else:
                                            synth_inventory[g] += 1  # 실패 시 재료 등급 1개 반환
                                        changed = True

                        cost = math.ceil(draw_count / 11) * draw_cost
                        results[goal] = cost
                        for g in ["A", "S", "R"]:
                            synth_log_total[g]["try"] += local_log[g]["try"]
                            synth_log_total[g]["success"] += local_log[g]["success"]

                    # SR 등급 시뮬레이션
                    sr_obtained = 0
                    r_inventory = 0
                    r_pity = 0
                    sr_draw_count = 0
                    sr_log = {"try": 0, "success": 0}

                    while sr_obtained < 1:
                        sr_draw_count += 1
                        if sr_draw_count % pity_R == 0:
                            r_inventory += 1
                        else:
                            rand = random.uniform(0, 100)
                            item = df[df["누적확률"] > rand].iloc[0]
                            if item["등급"] == "R":
                                r_inventory += 1

                        while r_inventory >= 4:
                            r_inventory -= 4
                            r_pity += 1
                            sr_log["try"] += 1

                            is_success = (
                                random.randint(1, 100) <= synth_rates["R"]
                                or r_pity >= synth_pities["R"]
                            )
                            if is_success:
                                sr_obtained += 1
                                sr_log["success"] += 1
                                r_pity = 0
                                break
                            else:
                                r_inventory += 1  # 실패 시 R 등급 1개 반환

                    sr_cost = math.ceil(sr_draw_count / 11) * draw_cost
                    results["SR"] = sr_cost

                    for g in results:
                        final_results[g].append(results[g])

                    synth_log_total["R"]["try"] += sr_log["try"]
                    synth_log_total["R"]["success"] += sr_log["success"]

                st.subheader("📈 평균 기대 비용")
                for g in final_results:
                    avg_cost = sum(final_results[g]) / len(final_results[g])
                    st.write(f"{g} 등급 1개 획득 평균 비용: {avg_cost:,.0f}원")

                st.subheader("📊 합성 시도 로그")
                for g in ["A", "S", "R"]:
                    tries = synth_log_total[g]["try"]
                    successes = synth_log_total[g]["success"]
                    fails = tries - successes
                    rate = (successes / tries * 100) if tries > 0 else 0
                    st.write(f"{g} 등급 합성 시도: {tries}회, 성공: {successes}회, 실패: {fails}회, 성공률: {rate:.2f}%")

                st.success("🎉 시뮬레이션 완료")

    except Exception as e:
        st.error(f"❌ 파일 처리 중 오류 발생: {e}")
else:
    st.info("📌 엑셀 파일을 업로드해 주세요 (등급, 구성품, 확률 포함)")
