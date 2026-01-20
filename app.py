import streamlit as st
import random
import calendar
import io
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Border, Side, Font

# --- 전역 설정: 일요일부터 시작 ---
calendar.setfirstweekday(calendar.SUNDAY)

# --- 11인 명단 설정 ---
MEMBER_LIST = ["양기윤", "전소영", "임채성", "홍부휘", "이지용", 
               "조현진", "정용채", "강창신", "김덕기", "우성대", "홍그린"]

def get_2026_holidays(month):
    """2026년 대한민국 주요 공휴일 정보"""
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
        'slots': [],  # {day, type, owner, id, is_heavy}
        'absentees': set(),
        'absentee_prefs': {name: "" for name in MEMBER_LIST},
        'year': 2026,
        'quota_info': ""  # 4회/3회 추첨 결과 텍스트 저장용
    })

# --- 페이지 설정 ---
st.set_page_config(page_title="2026 CARE팀 당직 시스템", layout="wide")

# --- 사이드바: 설정 및 부재자 관리 ---
with st.sidebar:
    st.header("⚙️ 시스템 설정")
    sel_month = st.number_input("배정 월 선택", min_value=1, max_value=12, value=1)
    
    if st.button("📅 새 달력 및 데이터 초기화", use_container_width=True):
        cal = calendar.monthcalendar(2026, sel_month)
        heavy_days = set(get_2026_holidays(sel_month))
        new_slots = []
        slot_id = 0
        for week in cal:
            for c_idx, day in enumerate(week):
                if day == 0: continue
                # 토요일(6), 일요일(0), 공휴일 판정
                is_heavy = (c_idx == 0 or c_idx == 6 or day in heavy_days)
                # 휴일인 경우 주간(Day) 슬롯 추가
                if is_heavy:
                    new_slots.append({"day": day, "type": "Day", "owner": None, "id": slot_id, "is_heavy": True})
                    slot_id += 1
                # 야간(Night) 슬롯은 매일 추가
                new_slots.append({"day": day, "type": "Night", "owner": None, "id": slot_id, "is_heavy": is_heavy})
                slot_id += 1
        st.session_state.slots = new_slots
        st.session_state.quotas = {}
        st.session_state.selection_order = []
        st.session_state.current_picker_idx = 0
        st.session_state.quota_info = ""
        st.rerun()

    st.divider()
    st.header("👤 부재자 및 희망번호")
    st.caption("달력의 ID(예: D:5의 '5')를 입력하세요.")
    for name in sorted(MEMBER_LIST):
        with st.expander(f"{name} 설정"):
            is_absent = st.checkbox("부재자 지정", key=f"abs_{name}", value=(name in st.session_state.absentees))
            if is_absent: st.session_state.absentees.add(name)
            else: st.session_state.absentees.discard(name)
            
            prefs = st.text_input("희망 슬롯 ID (쉼표 구분)", 
                                 value=st.session_state.absentee_prefs[name],
                                 key=f"pref_{name}")
            st.session_state.absentee_prefs[name] = prefs

# --- 메인 영역 상단 ---
st.title(f"📅 2026년 {sel_month}월 CARE팀 당직 배정")

col_info, col_cal = st.columns([1, 2.5])

# --- 왼쪽 컬럼: 추첨 및 순서 현황 ---
with col_info:
    st.subheader("🎲 배정 진행")
    
    # 1. 근무 횟수 추첨
    if st.button("1️⃣ 근무 횟수 추첨", use_container_width=True):
        total_slots = len(st.session_state.slots)
        base, extra = divmod(total_slots, len(MEMBER_LIST))
        temp = MEMBER_LIST.copy()
        random.shuffle(temp)
        
        high_group = sorted(temp[:extra])
        low_group = sorted(temp[extra:])
        
        st.session_state.quotas = {n: base + 1 if n in high_group else base for n in MEMBER_LIST}
        st.session_state.quota_info = {
            "high_val": base + 1, "high_names": high_group,
            "low_val": base, "low_names": low_group
        }

    # 추첨 결과 표시
    if st.session_state.quota_info:
        info = st.session_state.quota_info
        st.info(f"📍 **{info['high_val']}회 대상자:** {', '.join(info['high_names'])}")
        st.success(f"📍 **{info['low_val']}회 대상자:** {', '.join(info['low_names'])}")

    # 2. 선택 순서 추첨
    if st.button("2️⃣ 선택 순서 추첨", use_container_width=True):
        order = MEMBER_LIST.copy()
        random.shuffle(order)
        st.session_state.selection_order = order
        st.session_state.current_picker_idx = 0
        st.toast("선택 순서가 확정되었습니다!")

    st.divider()
    st.subheader("📋 실시간 순서 현황")
    
    if st.session_state.selection_order:
        for idx, name in enumerate(st.session_state.selection_order):
            q = st.session_state.quotas.get(name, 0)
            is_turn = (idx == st.session_state.current_picker_idx and sum(st.session_state.quotas.values()) > 0)
            
            # 실시간 희망 잔여 번호 계산
            pref_str = st.session_state.absentee_prefs.get(name, "")
            pref_ids = [int(x.strip()) for x in pref_str.split(',') if x.strip().isdigit()]
            remaining_prefs = [p_id for p_id in pref_ids if p_id < len(st.session_state.slots) and st.session_state.slots[p_id]['owner'] is None]
            
            # 텍스트 구성
            prefix = "👉" if is_turn else "•"
            abs_tag = " [부재]" if name in st.session_state.absentees else ""
            pref_text = f" | 🌟희망잔여: {', '.join(map(str, remaining_prefs))}" if remaining_prefs else ""
            
            # 현재 차례 강조
            if is_turn:
                st.markdown(f"<div style='background-color:#fff3cd; padding:5px; border-radius:5px;'><b>{prefix} {name} ({q}회){abs_tag}{pref_text}</b></div>", unsafe_allow_html=True)
            else:
                st.write(f"{prefix} {name} ({q}회){abs_tag}{pref_text}")
            
            # --- 자동 배정 로직 (부재자) ---
            if is_turn and name in st.session_state.absentees and q > 0:
                if remaining_prefs:
                    target_id = remaining_prefs[0]
                    st.session_state.slots[target_id]['owner'] = name
                    st.session_state.quotas[name] -= 1
                    st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(MEMBER_LIST)
                    st.rerun()

# --- 오른쪽 컬럼: 달력 판 ---
with col_cal:
    # 요일 헤더 (일~토)
    days_kr = ["일", "월", "화", "수", "목", "금", "토"]
    header_cols = st.columns(7)
    for i, h in enumerate(days_kr):
        h_color = "red" if (i == 0 or i == 6) else "black"
        header_cols[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{h_color};'>{h}</p>", unsafe_allow_html=True)

    if st.session_state.slots:
        cal = calendar.monthcalendar(2026, sel_month)
        heavy_days = get_2026_holidays(sel_month)
        
        for week in cal:
            week_cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: continue
                
                # 주말 및 공휴일 빨간색 강조
                is_holiday = (i == 0 or i == 6 or day in heavy_days)
                day_color = "red" if is_holiday else "black"
                
                with week_cols[i]:
                    st.markdown(f"<p style='color:{day_color}; font-weight:bold; margin-bottom:2px;'>{day}일</p>", unsafe_allow_html=True)
                    day_slots = [s for s in st.session_state.slots if s['day'] == day]
                    for s in day_slots:
                        label = f"{s['type'][0]}:{s['id']}"
                        if s['owner']:
                            st.button(f"[{s['owner']}]", key=f"btn_{s['id']}", disabled=True, use_container_width=True)
                        else:
                            if st.button(label, key=f"btn_{s['id']}", use_container_width=True):
                                curr_name = st.session_state.selection_order[st.session_state.current_picker_idx]
                                if st.session_state.quotas[curr_name] > 0:
                                    s['owner'] = curr_name
                                    st.session_state.quotas[curr_name] -= 1
                                    st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(MEMBER_LIST)
                                    st.rerun()
    else:
        st.info("왼쪽 사이드바에서 '새 달력 생성'을 먼저 눌러주세요.")

# --- 엑셀 다운로드 기능 ---
st.divider()
def download_excel():
    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = f"2026년 {sel_month}월 당직표"
    
    # 헤더 스타일
    headers = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"]
    for col_idx, h in enumerate(headers, 1):
        cell = ws.cell(1, col_idx, h)
        cell.fill = PatternFill("solid", fgColor="333333")
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = 20

    # 데이터 매핑
    day_map = {d: {"Day": "", "Night": ""} for d in range(1, 32)}
    for s in st.session_state.slots:
        if s['owner']: day_map[s['day']][s['type']] = s['owner']

    # 달력 채우기
    cal = calendar.monthcalendar(2026, sel_month)
    heavy_days = get_2026_holidays(sel_month)
    border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    for r_idx, week in enumerate(cal, 2):
        ws.row_dimensions[r_idx].height = 60
        for c_idx, day in enumerate(week):
            if day == 0: continue
            cell = ws.cell(r_idx, c_idx + 1, f"[{day}일]\nD: {day_map[day]['Day']}\nN: {day_map[day]['Night']}")
            cell.alignment = Alignment(wrap_text=True, vertical="top")
            cell.border = border
            # 색상 적용
            if c_idx == 0 or day in heavy_days: cell.fill = PatternFill("solid", fgColor="FFD9D9")
            elif c_idx == 6: cell.fill = PatternFill("solid", fgColor="D9EAD3")

    wb.save(output)
    return output.getvalue()

if st.session_state.slots:
    st.download_button(
        label="💾 최종 당직표 엑셀 다운로드",
        data=download_excel(),
        file_name=f"CARE팀_{sel_month}월_당직표.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )