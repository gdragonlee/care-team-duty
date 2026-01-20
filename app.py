import streamlit as st
import random
import calendar
import io
import copy
from openpyxl import Workbook
from openpyxl.styles import Alignment, PatternFill, Border, Side, Font

# --- 전역 설정 ---
calendar.setfirstweekday(calendar.SUNDAY)
MEMBER_LIST = ["양기윤", "전소영", "임채성", "홍부휘", "이지용", 
               "조현진", "정용채", "강창신", "김덕기", "우성대", "홍그린"]

def get_2026_holidays(month):
    """2026년 공휴일 데이터"""
    holidays = {1: [1], 2: [16, 17, 18], 3: [1, 2], 5: [5, 24, 25], 
                6: [6], 8: [15, 17], 9: [24, 25, 26], 10: [3, 5, 9], 12: [25]}
    return holidays.get(month, [])

# --- 세션 상태 초기화 ---
REQUIRED_KEYS = {
    'quotas': {}, 'selection_order': [], 'current_picker_idx': 0, 'slots': [],
    'absentees': set(), 'absentee_prefs': {name: "" for name in MEMBER_LIST},
    'history': [], 'manual_mode': False, 'admin_selected_member': MEMBER_LIST[0],
    'quota_info': None, 'pass_log': ""
}
for key, default in REQUIRED_KEYS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# --- 핵심 로직 함수 ---
def save_history():
    snapshot = {'slots': copy.deepcopy(st.session_state.slots), 'quotas': copy.deepcopy(st.session_state.quotas),
                'current_picker_idx': st.session_state.current_picker_idx, 'pass_log': st.session_state.pass_log}
    st.session_state.history.append(snapshot)
    if len(st.session_state.history) > 20: st.session_state.history.pop(0)

def move_to_next_picker():
    if not st.session_state.selection_order: return
    for _ in range(len(st.session_state.selection_order)):
        st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(st.session_state.selection_order)
        curr_name = st.session_state.selection_order[st.session_state.current_picker_idx]
        if st.session_state.quotas.get(curr_name, 0) > 0: return

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

# --- 화면 레이아웃 및 강제 다크 모드 CSS ---
st.set_page_config(page_title="CARE팀 다크 당직 시스템", layout="wide")

st.markdown("""
    <style>
    /* 전체 배경을 다크 모드로 강제 설정 */
    .stApp {
        background-color: #0e1117;
        color: #ffffff;
    }
    
    /* 사이드바 다크 설정 */
    [data-testid="stSidebar"] {
        background-color: #262730;
    }

    /* 요일 헤더: 아주 어두운 회색 배경 + 하얀색 글씨 */
    .day-header-box {
        background-color: #1c1e21;
        color: #ffffff !important;
        text-align: center;
        font-weight: 900;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 15px;
        font-size: 1.1rem;
        border: 1px solid #495057;
    }

    /* 평일 날짜: 진한 회색 배경 + 하얀색 글씨 */
    .date-tag-normal {
        background-color: #495057; 
        color: #ffffff !important;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 8px;
        border: 1px solid #adb5bd;
    }

    /* 공휴일/주말: 진한 빨간 배경 + 하얀색 글씨 */
    .date-tag-holiday {
        background-color: #c92a2a;
        color: #ffffff !important;
        padding: 4px 12px;
        border-radius: 6px;
        font-weight: 800;
        display: inline-block;
        margin-bottom: 8px;
        border: 1px solid #ffa8a8;
    }

    /* 모든 버튼 내 글씨 하얀색 고정 */
    div[data-testid="stButton"] button p {
        color: white !important;
        font-weight: 700;
    }

    /* 배정 완료된 버튼: 아주 어두운 배경 */
    div[data-testid="stButton"] button[disabled] {
        background-color: #212529 !important;
        border: 1px solid #343a40 !important;
        opacity: 0.8 !important;
    }

    /* 현재 순번 강조 박스 (다크 대비 오렌지) */
    .turn-box {
        background-color: #2b2f36;
        border-left: 8px solid #fd7e14;
        padding: 15px;
        border-radius: 10px;
        color: #ffffff;
        margin-bottom: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.5);
    }

    /* 부재중 뱃지 */
    .absent-badge {
        color: #ff8787;
        font-weight: bold;
        background-color: #c92a2a33;
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.8rem;
        margin-left: 8px;
        border: 1px solid #c92a2a;
    }

    /* 일반 텍스트 하얗게 */
    span, p, label {
        color: #ffffff !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 사이드바 영역 ---
with st.sidebar:
    st.title("🌑 다크 관리자")
    sel_month = st.number_input("배정 월", 1, 12, 1)
    if st.button("📅 새 달력 데이터 초기화", use_container_width=True):
        cal = calendar.monthcalendar(2026, sel_month); h_days = set(get_2026_holidays(sel_month))
        new_slots = []; slot_id = 0
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

    st.session_state.manual_mode = st.toggle("🛡️ 수동 모드")
    if st.session_state.manual_mode:
        st.session_state.admin_selected_member = st.selectbox("강제 배정 대상", MEMBER_LIST)

    st.divider()
    for name in sorted(MEMBER_LIST):
        with st.expander(f"⚙️ {name} 설정"):
            is_abs = st.checkbox("부재중 체크", key=f"abs_{name}", value=(name in st.session_state.absentees))
            if is_abs: st.session_state.absentees.add(name)
            else: st.session_state.absentees.discard(name)
            st.session_state.absentee_prefs[name] = st.text_input("희망 ID(쉼표)", value=st.session_state.absentee_prefs[name], key=f"p_{name}")

# --- 메인 화면 ---
st.title(f"🌑 2026년 {sel_month}월 당직 배정 (DARK)")

col_info, col_cal = st.columns([1, 2.3])

with col_info:
    st.subheader("🎲 추첨 제어")
    c1, c2 = st.columns(2)
    if c1.button("🔢 횟수 추첨", use_container_width=True):
        t = len(st.session_state.slots); b, e = divmod(t, 11)
        tmp = MEMBER_LIST.copy(); random.shuffle(tmp)
        h, l = sorted(tmp[:e]), sorted(tmp[e:])
        st.session_state.quotas = {n: b+1 if n in h else b for n in MEMBER_LIST}
        st.session_state.quota_info = (b+1, h, b, l)
    
    if c2.button("🏃 순위 추첨", use_container_width=True):
        st.session_state.selection_order = random.sample(MEMBER_LIST, len(MEMBER_LIST))
        st.session_state.current_picker_idx = 0

    if st.session_state.quota_info:
        b1, h1, b2, l2 = st.session_state.quota_info
        st.info(f"✨ {b1}회: {', '.join(h1)}")
        st.success(f"✨ {b2}회: {', '.join(l2)}")

    st.divider()
    ctrl1, ctrl2 = st.columns(2)
    if ctrl1.button("↩️ 되돌리기", use_container_width=True, disabled=not st.session_state.history):
        last = st.session_state.history.pop()
        st.session_state.update({'slots': last['slots'], 'quotas': last['quotas'], 'current_picker_idx': last['current_picker_idx'], 'pass_log': last['pass_log']})
        st.rerun()
    if ctrl2.button("🚫 패스", use_container_width=True):
        if st.session_state.selection_order: pass_turn(st.session_state.selection_order[st.session_state.current_picker_idx])

    if st.session_state.pass_log:
        st.warning(st.session_state.pass_log)

    st.subheader("📋 순위별 대기열")
    if st.session_state.selection_order:
        curr_p = st.session_state.selection_order[st.session_state.current_picker_idx]
        if st.session_state.quotas.get(curr_p, 0) <= 0: move_to_next_picker()

        for rank, name in enumerate(st.session_state.selection_order, 1):
            q = st.session_state.quotas.get(name, 0)
            if q <= 0: continue
            
            raw_prefs = [x.strip() for x in st.session_state.absentee_prefs.get(name, "").split(',') if x.strip().isdigit()]
            rem_prefs = [p for p in raw_prefs if int(p) < len(st.session_state.slots) and st.session_state.slots[int(p)]['owner'] is None]
            
            pref_display = f" | 🌟 남음: {', '.join(rem_prefs)}" if rem_prefs else ""
            abs_display = '<span class="absent-badge">[부재중]</span>' if name in st.session_state.absentees else ""
            is_turn = ((rank - 1) == st.session_state.current_picker_idx)

            if is_turn:
                st.markdown(f"""<div class="turn-box"><b>👉 {rank}위: {name}{abs_display} ({q}회){pref_display}</b></div>""", unsafe_allow_html=True)
                if name in st.session_state.absentees:
                    if rem_prefs:
                        target_id = int(rem_prefs[0])
                        save_history(); st.session_state.slots[target_id]['owner'] = name
                        st.session_state.quotas[name] -= 1; move_to_next_picker(); st.rerun()
                    else: pass_turn(name)
            else:
                st.markdown(f"<span style='color:white;'>**{rank}위: {name}**{abs_display} ({q}회){pref_display}</span>", unsafe_allow_html=True)

with col_cal:
    h_cols = st.columns(7); days_kr = ["일", "월", "화", "수", "목", "금", "토"]
    for i, h in enumerate(days_kr):
        h_cols[i].markdown(f'<div class="day-header-box">{h}</div>', unsafe_allow_html=True)

    if st.session_state.slots:
        cal = calendar.monthcalendar(2026, sel_month); h_days = get_2026_holidays(sel_month)
        for week in cal:
            w_cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: continue
                is_h = (i == 0 or i == 6 or day in h_days)
                tag_class = "date-tag-holiday" if is_h else "date-tag-normal"
                with w_cols[i]:
                    st.markdown(f'<div class="{tag_class}">{day}일</div>', unsafe_allow_html=True)
                    for s in [sl for sl in st.session_state.slots if sl['day'] == day]:
                        label = f"{s['type'][0]}:{s['id']}"
                        if s['owner']:
                            st.button(f"👤 {s['owner']}", key=f"b{s['id']}", disabled=True, use_container_width=True)
                        else:
                            if st.button(label, key=f"b{s['id']}", use_container_width=True):
                                save_history()
                                target = st.session_state.admin_selected_member if st.session_state.manual_mode else st.session_state.selection_order[st.session_state.current_picker_idx]
                                if st.session_state.quotas.get(target, 0) > 0 or st.session_state.manual_mode:
                                    s['owner'] = target; st.session_state.quotas[target] -= 1
                                    if not st.session_state.manual_mode: move_to_next_picker()
                                    st.rerun()

# --- 엑셀 저장 ---
def make_excel():
    output = io.BytesIO(); wb = Workbook(); ws = wb.active; ws.title = f"{sel_month}월"
    headers = ["일", "월", "화", "수", "목", "금", "토"]
    for c, h in enumerate(headers, 1):
        cell = ws.cell(1, c, h); cell.fill = PatternFill("solid", "333333"); cell.font = Font(color="FFFFFF", bold=True); ws.column_dimensions[cell.column_letter].width = 18
    day_map = {d: {"Day": "", "Night": ""} for d in range(1, 32)}
    for s in st.session_state.slots:
        if s['owner']: day_map[s['day']][s['type']] = s['owner']
    for r_idx, week in enumerate(calendar.monthcalendar(2026, sel_month), 2):
        ws.row_dimensions[r_idx].height = 60
        for c_idx, day in enumerate(week):
            if day == 0: continue
            cell = ws.cell(r_idx, c_idx + 1, f"[{day}일]\n주: {day_map[day]['Day']}\n야: {day_map[day]['Night']}")
            cell.alignment = Alignment(wrap_text=True, vertical="top"); cell.border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
            if c_idx == 0 or day in h_days: cell.fill = PatternFill("solid", "ffc9c9")
            elif c_idx == 6: cell.fill = PatternFill("solid", "d0ebff")
    wb.save(output); return output.getvalue()

st.divider()
if st.session_state.slots:
    st.download_button("💾 엑셀 저장 (다크 테마 결과)", data=make_excel(), file_name=f"CARE팀_{sel_month}월.xlsx", use_container_width=True, type="primary")