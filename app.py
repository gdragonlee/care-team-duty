import streamlit as st
import random
import calendar
import io
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Border, Side, Font

# 일요일부터 시작하도록 설정
calendar.setfirstweekday(calendar.SUNDAY)

# --- 11인 명단 설정 ---
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
    st.session_state.update({
        'initialized': True,
        'quotas': {},
        'selection_order': [],
        'current_picker_idx': 0,
        'slots': [],
        'absentees': set(),
        'absentee_prefs': {name: "" for name in MEMBER_LIST},
        'year': 2026
    })

st.set_page_config(page_title="2026 CARE팀 당직", layout="wide")

# --- 사이드바 ---
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    sel_month = st.number_input("배정 월 선택", min_value=1, max_value=12, value=1)
    
    if st.button("📅 새 달력 생성 및 초기화", use_container_width=True):
        cal = calendar.monthcalendar(2026, sel_month)
        heavy_days = set(get_2026_holidays(sel_month))
        new_slots = []
        slot_id = 0
        for week in cal:
            for c_idx, day in enumerate(week):
                if day == 0: continue
                # 일요일(0) 또는 토요일(6) 또는 공휴일 판정
                is_heavy = (c_idx == 0 or c_idx == 6 or day in heavy_days)
                if is_heavy:
                    new_slots.append({"day": day, "type": "Day", "owner": None, "id": slot_id, "is_heavy": True})
                    slot_id += 1
                new_slots.append({"day": day, "type": "Night", "owner": None, "id": slot_id, "is_heavy": is_heavy})
                slot_id += 1
        st.session_state.slots = new_slots
        st.session_state.quotas = {}
        st.session_state.selection_order = []
        st.rerun()

    st.divider()
    st.header("👤 부재자 설정")
    for name in MEMBER_LIST:
        with st.expander(f"{name} 설정"):
            is_absent = st.checkbox("부재자", key=f"abs_{name}")
            if is_absent: st.session_state.absentees.add(name)
            else: st.session_state.absentees.discard(name)
            prefs = st.text_input("희망 슬롯 ID", value=st.session_state.absentee_prefs[name], key=f"p_{name}")
            st.session_state.absentee_prefs[name] = prefs

# --- 메인 영역 ---
st.title(f"📅 2026년 {sel_month}월 당직 배정")

col_info, col_cal = st.columns([1, 3])

with col_info:
    st.subheader("🎲 추첨")
    if st.button("1. 근무 횟수 추첨", use_container_width=True):
        total_slots = len(st.session_state.slots)
        base, extra = divmod(total_slots, len(MEMBER_LIST))
        temp = MEMBER_LIST.copy()
        random.shuffle(temp)
        
        high_group = sorted(temp[:extra])
        low_group = sorted(temp[extra:])
        
        st.session_state.quotas = {n: base + 1 if n in high_group else base for n in MEMBER_LIST}
        
        # 4회/3회 등 결과 표시
        st.info(f"✅ **{base+1}회 대상자 ({len(high_group)}명):**\n{', '.join(high_group)}")
        st.success(f"✅ **{base}회 대상자 ({len(low_group)}명):**\n{', '.join(low_group)}")

    if st.button("2. 선택 순서 추첨", use_container_width=True):
        order = MEMBER_LIST.copy(); random.shuffle(order)
        st.session_state.selection_order = order
        st.session_state.current_picker_idx = 0
        st.success("순서 확정!")

    # 순서 및 상태 표시 (생략 - 이전 코드와 동일)

with col_cal:
    # 달력 헤더 (주말/공휴일 빨간색 표시)
    days_kr = ["일", "월", "화", "수", "목", "금", "토"]
    headers = st.columns(7)
    for i, h in enumerate(days_kr):
        color = "red" if (i == 0 or i == 6) else "black" # 토, 일 모두 빨간색
        headers[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{color};'>{h}</p>", unsafe_allow_html=True)

    if st.session_state.slots:
        cal = calendar.monthcalendar(2026, sel_month)
        heavy_days = get_2026_holidays(sel_month)
        
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: continue
                
                # 주말 및 공휴일 빨간색 강조
                is_holiday = (i == 0 or i == 6 or day in heavy_days)
                day_color = "red" if is_holiday else "black"
                
                with cols[i]:
                    st.markdown(f"<p style='color:{day_color}; font-weight:bold;'>{day}일</p>", unsafe_allow_html=True)
                    day_slots = [s for s in st.session_state.slots if s['day'] == day]
                    for s in day_slots:
                        # 버튼 표시 및 선택 로직 (동일)