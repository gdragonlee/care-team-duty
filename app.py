import streamlit as st
import random
import calendar
import io
import copy
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Border, Side, Font

# --- 시스템 설정 ---
calendar.setfirstweekday(calendar.SUNDAY)
MEMBER_LIST = ["양기윤", "전소영", "임채성", "홍부휘", "이지용", 
               "조현진", "정용채", "강창신", "김덕기", "우성대", "홍그린"]

def get_2026_holidays(month):
    holidays = {1: [1], 2: [16, 17, 18], 3: [1, 2], 5: [5, 24, 25], 6: [6], 8: [15, 17], 9: [24, 25, 26], 10: [3, 5, 9], 12: [25]}
    return holidays.get(month, [])

# --- 세션 상태 초기화 (AttributeError 방지) ---
REQUIRED_KEYS = {
    'quotas': {}, 'selection_order': [], 'current_picker_idx': 0, 'slots': [],
    'absentees': set(), 'absentee_prefs': {name: "" for name in MEMBER_LIST},
    'history': [], 'manual_mode': False, 'admin_selected_member': MEMBER_LIST[0],
    'quota_info': None, 'pass_log': ""
}
for key, default in REQUIRED_KEYS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- 로직 함수 ---
def save_history():
    snapshot = {'slots': copy.deepcopy(st.session_state.slots), 'quotas': copy.deepcopy(st.session_state.quotas),
                'current_picker_idx': st.session_state.current_picker_idx, 'pass_log': st.session_state.pass_log}
    st.session_state.history.append(snapshot)
    if len(st.session_state.history) > 20: st.session_state.history.pop(0)

def move_to_next_picker():
    """횟수가 있는 다음 사람으로 순서 이동"""
    if not st.session_state.selection_order: return
    for _ in range(len(st.session_state.selection_order)):
        curr_name = st.session_state.selection_order[st.session_state.current_picker_idx]
        if st.session_state.quotas.get(curr_name, 0) > 0: return
        st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(st.session_state.selection_order)

def pass_turn(name):
    rem = st.session_state.quotas.get(name, 0)
    if rem <= 0: return
    save_history()
    others = [n for n in st.session_state.selection_order if n != name and st.session_state.quotas.get(n, 0) > 0]
    if others:
        dist = [random.choice(others) for _ in range(rem)]
        for t in dist: st.session_state.quotas[t] += 1
        summary = {x: dist.count(x) for x in set(dist)}
        st.session_state.pass_log = f"🚫 **{name}** 패스 ➔ " + ", ".join([f"**{k}**(+{v}회)" for k, v in summary.items()])
    st.session_state.quotas[name] = 0
    move_to_next_picker()
    st.rerun()

# --- 화면 레이아웃 및 강력한 CSS 디자인 ---
st.set_page_config(page_title="CARE팀 당직 시스템", layout="wide")

st.markdown("""
    <style>
    /* 배경 및 기본 폰트 색상 */
    .main { background-color: #ffffff; }
    h1, h2, h3 { color: #1a1a1a !important; font-weight: 800 !important; }
    
    /* 날짜 숫자 강조 */
    .date-num {
        font-size: 1.5rem !important;
        font-weight: 900 !important;
        margin-bottom: 5px;
        display: block;
    }

    /* 버튼 스타일 (고대비) */
    .stButton>button {
        border: 2px solid #212529 !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        color: #212529 !important;
        height: 3rem !important;
    }

    /* 배정된 버튼 (검정 배경 + 흰색 글씨) */
    div[data-testid="stButton"] button[disabled] {
        background-color: #212529 !important;
        color: #ffffff !important;
        border: none !important;
        opacity: 1 !important;
    }

    /* 현재 차례 강조 박스 (매우 밝은 노랑 + 굵은 테두리) */
    .turn-highlight {
        background-color: #fff3bf;
        border: 4px solid #f08c00;
        padding: 20px;
        border-radius: 15px;
        color: #000000;
        margin-bottom: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    
    /* 대기열 텍스트 강화 */
    .waiting-list {
        font-size: 1.1rem;
        color: #495057;
        margin-bottom: 8px;
    }
    
    /* 요일 헤더 */
    .day-header {
        font-size: 1.2rem;
        font-weight: 800;
        padding: 10px;
        background-color: #f1f3f5;
        border-radius: 5px;
        margin-bottom: 15px;
        text-align: center;
    }
    </style>
""", unsafe_allow_html=True)

# --- 사이드바 ---
with st.sidebar:
    st.title("⚙️ 관리 메뉴")
    sel_month = st.number_input("배정 월", 1, 12, 1)
    if st.button("📅 새 달력 생성", use_container_width=True):
        cal = calendar.monthcalendar(2026, sel_month)
        h_days = set(get_2026_holidays(sel_month))
        new_slots = []
        slot_id = 0
        for week in cal:
            for c_idx, day in enumerate(week):
                if day == 0: continue
                is_h = (c_idx == 0 or c_idx == 6 or day in h_days)
                if is_h:
                    new_slots.append({"day": day, "type": "Day", "owner": None, "id": slot_id, "is_heavy": True})
                    slot_id += 1
                new_slots.append({"day": day, "type": "Night", "owner": None, "id": slot_id, "is_heavy": is_h})
                slot_id += 1
        st.session_state.update({'slots': new_slots, 'quotas': {}, 'selection_order': [], 'current_picker_idx': 0, 'history': [], 'pass_log': ""})
        st.rerun()

    st.session_state.manual_mode = st.toggle("🛡️ 수동 관리자 모드")
    if st.session_state.manual_mode:
        st.session_state.admin_selected_member = st.selectbox("강제 배정 대상", MEMBER_LIST)

    st.divider()
    st.header("👤 부재자/희망설정")
    for name in sorted(MEMBER_LIST):
        with st.expander(f"⚙️ {name}"):
            is_abs = st.checkbox("부재자", key=f"abs_{name}", value=(name in st.session_state.absentees))
            if is_abs: st.session_state.absentees.add(name)
            else: st.session_state.absentees.discard(name)
            st.session_state.absentee_prefs[name] = st.text_input("희망 ID (쉼표 구분)", value=st.session_state.absentee_prefs[name], key=f"p_{name}")

# --- 메인 화면 ---
st.title(f"📅 2026년 {sel_month}월 CARE팀 당직 배정")

col_info, col_cal = st.columns([1, 2.2])

with col_info:
    st.subheader("🎲 추첨 및 제어")
    c1, c2 = st.columns(2)
    if c1.button("🔢 횟수 추첨", use_container_width=True):
        t = len(st.session_state.slots); base, extra = divmod(t, 11)
        temp = MEMBER_LIST.copy(); random.shuffle(temp)
        high, low = sorted(temp[:extra]), sorted(temp[extra:])
        st.session_state.quotas = {n: base+1 if n in high else base for n in MEMBER_LIST}
        st.session_state.quota_info = (base+1, high, base, low)
    if c2.button("🏃 순서 추첨", use_container_width=True):
        order = MEMBER_LIST.copy(); random.shuffle(order); st.session_state.selection_order = order; st.session_state.current_picker_idx = 0

    if st.session_state.quota_info:
        b1, h1, b2, l2 = st.session_state.quota_info
        st.info(f"✨ **{b1}회**: {', '.join(h1)}\n\n✨ **{b2}회**: {', '.join(l2)}")

    st.divider()
    ctrl1, ctrl2 = st.columns(2)
    if ctrl1.button("↩️ 되돌리기", use_container_width=True, disabled=not st.session_state.history):
        undo()
    if ctrl2.button("🚫 패스(배분)", use_container_width=True):
        if st.session_state.selection_order: pass_turn(st.session_state.selection_order[st.session_state.current_picker_idx])

    if st.session_state.pass_log:
        st.warning(st.session_state.pass_log)

    st.subheader("📋 실시간 대기 순서")
    if st.session_state.selection_order:
        move_to_next_picker()
        for idx, name in enumerate(st.session_state.selection_order):
            q = st.session_state.quotas.get(name, 0)
            if q <= 0: continue # 횟수 0인 사람 목록에서 제외
            
            is_turn = (idx == st.session_state.current_picker_idx)
            # 남은 희망 번호 계산
            pref_ids = [int(x.strip()) for x in st.session_state.absentee_prefs.get(name, "").split(',') if x.strip().isdigit()]
            rem_prefs = [p_id for p_id in pref_ids if p_id < len(st.session_state.slots) and st.session_state.slots[p_id]['owner'] is None]
            
            pref_txt = f"<span style='color:#e67e22; font-weight:bold;'> [🌟희망: {', '.join(map(str, rem_prefs))}]</span>" if rem_prefs else ""
            
            if is_turn:
                st.markdown(f"""<div class="turn-highlight">
                    <b style="font-size:1.3rem;">👉 {name} ({q}회 남음)</b><br>
                    <b style="font-size:1rem;">{"[부재중]" if name in st.session_state.absentees else ""}{pref_txt}</b>
                </div>""", unsafe_allow_html=True)
                # 부재자 자동 처리
                if name in st.session_state.absentees:
                    if rem_prefs:
                        save_history(); st.session_state.slots[rem_prefs[0]]['owner'] = name
                        st.session_state.quotas[name] -= 1; move_to_next_picker(); st.rerun()
                    else: pass_turn(name)
            else:
                st.markdown(f"<div class='waiting-list'>• <b>{name}</b> ({q}회){pref_txt}</div>", unsafe_allow_html=True)

with col_cal:
    h_cols = st.columns(7)
    days_kr = ["일", "월", "화", "수", "목", "금", "토"]
    for i, h in enumerate(days_kr):
        color = "#ff0000" if i == 0 else "#0000ff" if i == 6 else "#000000"
        h_cols[i].markdown(f'<div class="day-header" style="color:{color};">{h}</div>', unsafe_allow_html=True)

    if st.session_state.slots:
        cal = calendar.monthcalendar(2026, sel_month); h_days = get_2026_holidays(sel_month)
        for week in cal:
            w_cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: continue
                is_h = (i == 0 or i == 6 or day in h_days)
                with w_cols[i]:
                    # 날짜 시인성 강화
                    st.markdown(f'<span class="date-num" style="color:{"#ff0000" if is_h else "#000000"};">{day}일</span>', unsafe_allow_html=True)
                    for s in [sl for sl in st.session_state.slots if sl['day'] == day]:
                        # 버튼 색상 (주간: 노랑바탕, 야간: 파랑바탕)
                        bg = "#fff9db" if s['type'] == "Day" else "#e7f5ff"
                        label = f"{s['type'][0]}:{s['id']}"
                        
                        if s['owner']:
                            # 배정된 칸은 검정 배경에 흰색 이름
                            st.button(f"👤 {s['owner']}", key=f"b{s['id']}", disabled=True, use_container_width=True)
                        else:
                            # 빈 칸 버튼
                            if st.button(label, key=f"b{s['id']}", use_container_width=True):
                                save_history()
                                target = st.session_state.admin_selected_member if st.session_state.manual_mode else st.session_state.selection_order[st.session_state.current_picker_idx]
                                if st.session_state.quotas.get(target, 0) > 0 or st.session_state.manual_mode:
                                    s['owner'] = target; st.session_state.quotas[target] -= 1
                                    move_to_next_picker(); st.rerun()

# --- 엑셀 저장 ---
def make_excel():
    output = io.BytesIO(); wb = Workbook(); ws = wb.active; ws.title = f"{sel_month}월 당직"
    headers = ["일요일", "월요일", "화요일", "수요일", "목요일", "금요일", "토요일"]
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c, h); cell.fill = PatternFill("solid", "333333"); cell.font = Font(color="FFFFFF", bold=True); ws.column_dimensions[cell.column_letter].width = 20
    day_map = {d: {"Day": "", "Night": ""} for d in range(1, 32)}
    for s in st.session_state.slots:
        if s['owner']: day_map[s['day']][s['type']] = s['owner']
    for r_idx, week in enumerate(calendar.monthcalendar(2026, sel_month), 2):
        ws.row_dimensions[r_idx].height = 70
        for c_idx, day in enumerate(week):
            if day == 0: continue
            cell = ws.cell(r_idx, c_idx + 1, f"[{day}일]\n주(D): {day_map[day]['Day']}\n야(N): {day_map[day]['Night']}")
            cell.alignment = Alignment(wrap_text=True, vertical="top"); cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            if c_idx == 0 or day in get_2026_holidays(sel_month): cell.fill = PatternFill("solid", "ffd9d9")
            elif c_idx == 6: cell.fill = PatternFill("solid", "d9eaf7")
    wb.save(output); return output.getvalue()

st.divider()
if st.session_state.slots:
    st.download_button("💾 최종 당직표 엑셀로 저장하기 (완료 후 클릭)", data=make_excel(), file_name=f"CARE팀_{sel_month}월_당직표.xlsx", use_container_width=True, type="primary")