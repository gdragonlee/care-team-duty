import streamlit as st
import random
import calendar
import io
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Border, Side, Font

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
        'slots': [], # {day, type, owner, id, is_heavy}
        'absentees': set(),
        'absentee_prefs': {name: "" for name in MEMBER_LIST},
        'history': [],
        'year': 2026
    })

st.set_page_config(page_title="2026 CARE팀 당직", layout="wide")

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
                # 휴일/주말 판정
                is_heavy = (c_idx == 0 or c_idx == 6 or day in heavy_days)
                if is_heavy:
                    new_slots.append({"day": day, "type": "Day", "owner": None, "id": slot_id, "is_heavy": True})
                    slot_id += 1
                new_slots.append({"day": day, "type": "Night", "owner": None, "id": slot_id, "is_heavy": is_heavy})
                slot_id += 1
        st.session_state.slots = new_slots
        st.session_state.quotas = {}
        st.session_state.selection_order = []
        st.session_state.current_picker_idx = 0
        st.rerun()

    st.divider()
    st.header("👤 부재자 및 희망번호")
    for name in MEMBER_LIST:
        with st.expander(f"{name} 설정"):
            is_absent = st.checkbox("부재자로 지정", key=f"abs_{name}")
            if is_absent: st.session_state.absentees.add(name)
            else: st.session_state.absentees.discard(name)
            
            prefs = st.text_input("희망 슬롯 ID (쉼표 구분)", 
                                 value=st.session_state.absentee_prefs[name],
                                 placeholder="예: 5, 12, 14",
                                 key=f"pref_{name}")
            st.session_state.absentee_prefs[name] = prefs

# --- 메인 영역 ---
st.title(f"📅 2026년 {sel_month}월 CARE팀 당직 배정")

col_info, col_cal = st.columns([1, 3])

with col_info:
    st.subheader("🎲 배정 진행")
    if st.button("1. 근무 횟수 추첨", use_container_width=True):
        total = len(st.session_state.slots)
        base, extra = divmod(total, len(MEMBER_LIST))
        temp = MEMBER_LIST.copy(); random.shuffle(temp)
        p1 = temp[:extra]
        st.session_state.quotas = {n: base + 1 if n in p1 else base for n in MEMBER_LIST}
        st.success("배분 완료!")

    if st.button("2. 선택 순서 추첨", use_container_width=True):
        order = MEMBER_LIST.copy(); random.shuffle(order)
        st.session_state.selection_order = order
        st.session_state.current_picker_idx = 0
        st.success("순서 확정!")

    st.divider()
    st.subheader("📋 실시간 순서")
    if st.session_state.selection_order:
        for idx, name in enumerate(st.session_state.selection_order):
            q = st.session_state.quotas.get(name, 0)
            is_turn = (idx == st.session_state.current_picker_idx and sum(st.session_state.quotas.values()) > 0)
            prefix = "▶️" if is_turn else "•"
            st.write(f"{prefix} **{name}** ({q}회 남음) {'[부재]' if name in st.session_state.absentees else ''}")
            
            # 자동 배정 로직 (부재자일 경우)
            if is_turn and name in st.session_state.absentees and q > 0:
                pref_list = [int(x.strip()) for x in st.session_state.absentee_prefs[name].split(',') if x.strip().isdigit()]
                for p_id in pref_list:
                    if p_id < len(st.session_state.slots) and st.session_state.slots[p_id]['owner'] is None:
                        st.session_state.slots[p_id]['owner'] = name
                        st.session_state.quotas[name] -= 1
                        st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(MEMBER_LIST)
                        st.rerun()

with col_cal:
    # 달력 헤더
    days_kr = ["일", "월", "화", "수", "목", "금", "토"]
    headers = st.columns(7)
    for i, h in enumerate(days_kr):
        color = "red" if i == 0 else "blue" if i == 6 else "black"
        headers[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{color};'>{h}</p>", unsafe_allow_html=True)

    # 달력 본문
    if st.session_state.slots:
        cal = calendar.monthcalendar(2026, sel_month)
        for week in cal:
            cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0:
                    cols[i].write("")
                    continue
                
                # 해당 날짜의 모든 슬롯 필터링
                day_slots = [s for s in st.session_state.slots if s['day'] == day]
                
                with cols[i]:
                    st.markdown(f"**{day}일**")
                    for s in day_slots:
                        label = f"{s['type'][0]}:{s['id']}" # D:5 또는 N:6 형태
                        if s['owner']:
                            st.button(f"[{s['owner']}]", key=f"btn_{s['id']}", disabled=True, use_container_width=True)
                        else:
                            if st.button(label, key=f"btn_{s['id']}", use_container_width=True):
                                # 직접 선택 로직
                                curr_name = st.session_state.selection_order[st.session_state.current_picker_idx]
                                if st.session_state.quotas[curr_name] > 0:
                                    s['owner'] = curr_name
                                    st.session_state.quotas[curr_name] -= 1
                                    st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(MEMBER_LIST)
                                    st.rerun()
    else:
        st.info("사이드바에서 '새 달력 생성'을 눌러주세요.")
import streamlit as st
import io
import calendar
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Border, Side, Font

# ... (기존 설정 및 세션 초기화 코드 생략) ...

# --- 엑셀 생성 함수 ---
def generate_excel(year, month, slots):
    output = io.BytesIO()
    wb = Workbook()
    ws = wb.active
    ws.title = f"{year}년 {month}월 당직표"

    # 헤더 스타일 설정
    headers = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"]
    header_fill = PatternFill(start_color="333333", end_color="333333", fill_type="solid")
    header_font = Font(color="FFFFFF", bold=True)
    
    for col_idx, day_name in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=day_name)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = 22 # 열 너비 조정

    # 달력 데이터 매핑
    day_map = {}
    for s in slots:
        d = s['day']
        if d not in day_map: day_map[d] = {"Day": "", "Night": ""}
        day_map[d][s['type']] = s['owner'] if s['owner'] else ""

    # 테두리 스타일
    thin_border = Border(
        left=Side(style='thin'), right=Side(style='thin'), 
        top=Side(style='thin'), bottom=Side(style='thin')
    )
    holiday_fill = PatternFill(start_color="FFD9D9", end_color="FFD9D9", fill_type="solid") # 빨간색(휴일)
    saturday_fill = PatternFill(start_color="D9EAD3", end_color="D9EAD3", fill_type="solid") # 초록색(토요일)

    # 달력 그리기
    cal = calendar.monthcalendar(year, month)
    heavy_days = get_2026_holidays(month)
    
    for r_idx, week in enumerate(cal, 2):
        ws.row_dimensions[r_idx].height = 80 # 행 높이 조정
        for c_idx, day in enumerate(week):
            if day == 0: continue
            
            col = c_idx + 1
            cell = ws.cell(row=r_idx, column=col)
            
            # 내용 입력 (D: 이름 / N: 이름)
            d_name = day_map.get(day, {}).get("Day", "")
            n_name = day_map.get(day, {}).get("Night", "")
            cell.value = f"[{day}일]\n\n주간(D): {d_name}\n야간(N): {n_name}"
            
            # 스타일 적용
            cell.alignment = Alignment(wrap_text=True, vertical="top", horizontal="left")
            cell.border = thin_border
            
            # 색상 적용 (일요일/공휴일 vs 토요일)
            if c_idx == 0 or day in heavy_days:
                cell.fill = holiday_fill
            elif c_idx == 6:
                cell.fill = saturday_fill

    wb.save(output)
    return output.getvalue()

# --- 메인 화면 하단 다운로드 섹션 ---
st.divider()
st.subheader("💾 최종 당직표 저장")

if st.session_state.slots:
    # 모든 슬롯이 배정되었는지 확인 (선택 사항)
    unassigned_count = sum(1 for s in st.session_state.slots if s['owner'] is None)
    
    if unassigned_count > 0:
        st.warning(f"아직 배정되지 않은 슬롯이 {unassigned_count}개 있습니다.")
    
    excel_data = generate_excel(st.session_state.year, sel_month, st.session_state.slots)
    
    st.download_button(
        label="📊 엑셀 파일로 다운로드 (.xlsx)",
        data=excel_data,
        file_name=f"CARE팀_{sel_month}월_당직표.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )
else:
    st.info("당직 배정을 완료한 후 엑셀 파일을 생성할 수 있습니다.")