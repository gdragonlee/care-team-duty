import streamlit as st
import random
import calendar
import io
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Border, Side, Font

# --- 설정 데이터 ---
MEMBER_LIST = ["양기윤", "전소영", "임채성", "홍부휘", "이지용", 
               "조현진", "정용채", "강창신", "김덕기", "우성대", "홍그린"]

def get_2026_holidays(month):
    holidays = {
        1: [1], 2: [16, 17, 18], 3: [1, 2], 
        5: [5, 24, 25], 6: [6], 8: [15, 17], 
        9: [24, 25, 26], 10: [3, 5, 9], 12: [25]
    }
    return holidays.get(month, [])

# --- 세션 상태 초기화 ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.quotas = {}
    st.session_state.selection_order = []
    st.session_state.current_picker_idx = 0
    st.session_state.final_schedule = {name: [] for name in MEMBER_LIST}
    st.session_state.absentees = set()
    st.session_state.absentee_prefs = {name: [] for name in MEMBER_LIST}
    st.session_state.slots = [] # {day, type, owner, id}

# --- UI 구성 ---
st.set_page_config(page_title="2026 CARE팀 당직 배정", layout="wide")
st.title("📅 2026년 CARE팀 당직 배정 시스템")

# 사이드바: 설정
with st.sidebar:
    st.header("1단계: 기본 설정")
    month = st.number_input("배정 월", min_value=1, max_value=12, value=1)
    
    if st.button("📅 새 달력 생성"):
        # 초기화 로직
        cal = calendar.monthcalendar(2026, month)
        heavy_days = set(get_2026_holidays(month))
        new_slots = []
        slot_id = 0
        for week in cal:
            if week[0] != 0: heavy_days.add(week[0])
            if week[6] != 0: heavy_days.add(week[6])
            for c_idx, day in enumerate(week):
                if day == 0: continue
                if day in heavy_days:
                    new_slots.append({"day": day, "type": "Day", "owner": None, "id": slot_id})
                    slot_id += 1
                new_slots.append({"day": day, "type": "Night", "owner": None, "id": slot_id})
                slot_id += 1
        st.session_state.slots = new_slots
        st.session_state.quotas = {}
        st.session_state.selection_order = []
        st.rerun()

    st.divider()
    st.header("2단계: 부재자 설정")
    selected_absentees = st.multiselect("부재자 선택", MEMBER_LIST)
    st.session_state.absentees = set(selected_absentees)

# 메인 화면: 추첨 및 진행
col1, col2 = st.columns([1, 3])

with col1:
    st.subheader("🎲 추첨 진행")
    if st.button("근무 횟수 추첨"):
        total = len(st.session_state.slots)
        base, extra = divmod(total, len(MEMBER_LIST))
        temp = MEMBER_LIST.copy()
        random.shuffle(temp)
        p1 = temp[:extra]
        st.session_state.quotas = {n: base + 1 if n in p1 else base for n in MEMBER_LIST}
        st.success("횟수 배분 완료!")

    if st.button("선택 순서 추첨"):
        order = MEMBER_LIST.copy()
        random.shuffle(order)
        st.session_state.selection_order = order
        st.session_state.current_picker_idx = 0
        st.success("순서 추첨 완료!")

    st.divider()
    st.subheader("📊 배정 현황")
    if st.session_state.selection_order:
        for idx, name in enumerate(st.session_state.selection_order):
            q = st.session_state.quotas.get(name, 0)
            status = "👈 차례" if idx == st.session_state.current_picker_idx else ""
            st.write(f"{idx+1}. **{name}** ({q}회 남음) {status}")

with col2:
    st.subheader("🗓️ 당직 선택 판")
    if not st.session_state.slots:
        st.info("사이드바에서 '새 달력 생성'을 먼저 눌러주세요.")
    else:
        # 달력 형태로 출력
        cols = st.columns(7)
        days = ["일", "월", "화", "수", "목", "금", "토"]
        for i, d in enumerate(days):
            cols[i].centered_text = f"**{d}**"
            cols[i].write(f"**{d}**")

        # 슬롯 배치
        for slot in st.session_state.slots:
            # 단순 리스트 형태로 표시하거나, 로직에 맞게 배치
            btn_label = f"{slot['day']}일 {slot['type']}"
            if slot['owner']:
                st.button(f"{btn_label}\n[{slot['owner']}]", key=f"slot_{slot['id']}", disabled=True)
            else:
                if st.button(btn_label, key=f"slot_{slot['id']}"):
                    # 선택 로직
                    curr_name = st.session_state.selection_order[st.session_state.current_picker_idx]
                    if st.session_state.quotas[curr_name] > 0:
                        slot['owner'] = curr_name
                        st.session_state.quotas[curr_name] -= 1
                        # 다음 사람으로 (횟수 남은 사람 찾기)
                        st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(MEMBER_LIST)
                        st.rerun()

# 엑셀 다운로드 기능
if st.button("💾 최종 당직표 엑셀 다운로드"):
    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    # ... (엑셀 저장 로직 생략 - 기존 코드와 유사하게 구현 가능) ...
    wb.save(output)
    st.download_button(label="엑셀 파일 받기", data=output.getvalue(), file_name="duty_schedule.xlsx")