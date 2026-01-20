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
    holidays = {
        1: [1], 2: [16, 17, 18], 3: [1, 2], 
        5: [5, 24, 25], 6: [6], 8: [15, 17], 
        9: [24, 25, 26], 10: [3, 5, 9], 12: [25]
    }
    return holidays.get(month, [])

# --- 1. 초기화 로직 (에러 방지 및 필수 키 생성) ---
REQUIRED_KEYS = {
    'quotas': {},
    'selection_order': [],
    'current_picker_idx': 0,
    'slots': [],
    'absentees': set(),
    'absentee_prefs': {name: "" for name in ["양기윤", "전소영", "임채성", "홍부휘", "이지용", "조현진", "정용채", "강창신", "김덕기", "우성대", "홍그린"]},
    'history': [],
    'manual_mode': False,
    'quota_info': None,
    'pass_log': "" # 누가 추가 당직을 받았는지 기록
}

for key, default_value in REQUIRED_KEYS.items():
    if key not in st.session_state:
        st.session_state[key] = default_value

# --- 2. 순서 이동 최적화 함수 ---
def move_to_next_picker():
    """횟수가 남아있는 다음 사람을 찾을 때까지 인덱스 이동"""
    if not st.session_state.selection_order:
        return

    # 최대 인원수만큼 순회하며 횟수가 있는 사람 탐색
    for _ in range(len(st.session_state.selection_order)):
        curr_name = st.session_state.selection_order[st.session_state.current_picker_idx]
        if st.session_state.quotas.get(curr_name, 0) > 0:
            return # 횟수가 남아있는 사람 발견 시 중단
        
        # 횟수가 0이면 다음 사람으로 인덱스 증가
        st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(st.session_state.selection_order)

# --- 3. 패스 및 배분 로직 ---
def pass_turn(name):
    rem = st.session_state.quotas.get(name, 0)
    if rem <= 0: return

    # 현재 상태 저장 (Undo용)
    snapshot = {
        'slots': copy.deepcopy(st.session_state.slots),
        'quotas': copy.deepcopy(st.session_state.quotas),
        'current_picker_idx': st.session_state.current_picker_idx,
        'pass_log': st.session_state.pass_log
    }
    st.session_state.history.append(snapshot)

    # 본인을 제외하고 횟수가 남아있는(대상자) 사람 찾기
    others = [n for n in st.session_state.selection_order if n != name and st.session_state.quotas.get(n, 0) > 0]
    
    if others:
        dist_log = []
        for _ in range(rem):
            target = random.choice(others)
            st.session_state.quotas[target] += 1
            dist_log.append(target)
        
        # 누가 받았는지 요약 생성
        summary = {x: dist_log.count(x) for x in set(dist_log)}
        log_msg = f"📢 **{name}**님 패스 → " + ", ".join([f"**{k}**(+{v}회)" for k, v in summary.items()])
        st.session_state.pass_log = log_msg
    else:
        st.session_state.pass_log = f"⚠️ {name}님 패스 (배분 대상이 없어 {rem}회 소멸)"
    
    st.session_state.quotas[name] = 0
    move_to_next_picker()
    st.rerun()

# --- 4. 화면 출력 부분 (col_info 내부) ---
with col_info:
    # ... (추첨 버튼 생략) ...

    # 패스 결과 알림 표시
    if st.session_state.pass_log:
        st.success(st.session_state.pass_log)

    st.subheader("📋 실시간 대기 순서")
    if st.session_state.selection_order:
        # 현재 차례인 사람이 횟수가 0이면 자동으로 다음 사람으로 넘김
        move_to_next_picker()
        
        # 순서 목록 출력
        for idx, name in enumerate(st.session_state.selection_order):
            q = st.session_state.quotas.get(name, 0)
            
            # 핵심 변경: 횟수가 0인 사람은 화면에서 제외
            if q <= 0:
                continue
            
            is_turn = (idx == st.session_state.current_picker_idx)
            
            # 희망 잔여 번호 계산
            pref_ids = [int(x.strip()) for x in st.session_state.absentee_prefs.get(name, "").split(',') if x.strip().isdigit()]
            rem_prefs = [p_id for p_id in pref_ids if p_id < len(st.session_state.slots) and st.session_state.slots[p_id]['owner'] is None]
            
            prefix = "👉" if is_turn else "•"
            tag = " [부재]" if name in st.session_state.absentees else ""
            pref_txt = f" | 🌟남음: {', '.join(map(str, rem_prefs))}" if rem_prefs else ""
            
            if is_turn:
                st.markdown(f"<div style='background-color:#fff3cd; padding:8px; border-radius:5px; border-left:5px solid #ffa000;'><b>{prefix} {name} ({q}회){tag}{pref_txt}</b></div>", unsafe_allow_html=True)
                
                # 부재자 자동 처리 로직
                if name in st.session_state.absentees:
                    if rem_prefs:
                        # 희망 날짜 배정 로직 (생략 - 기존과 동일하게 save_history 후 배정)
                        pass 
                    else:
                        pass_turn(name) # 희망 날짜 없으면 자동 패스
            else:
                st.write(f"{prefix} {name} ({q}회){tag}{pref_txt}")

# --- 주요 로직 함수 ---
def save_history():
    """현재 상태를 이력에 저장 (최대 20개)"""
    snapshot = {
        'slots': copy.deepcopy(st.session_state.slots),
        'quotas': copy.deepcopy(st.session_state.quotas),
        'current_picker_idx': st.session_state.current_picker_idx
    }
    st.session_state.history.append(snapshot)
    if len(st.session_state.history) > 20:
        st.session_state.history.pop(0)

def undo():
    """마지막 작업 되돌리기"""
    if st.session_state.history:
        last_state = st.session_state.history.pop()
        st.session_state.slots = last_state['slots']
        st.session_state.quotas = last_state['quotas']
        st.session_state.current_picker_idx = last_state['current_picker_idx']
        st.rerun()

def pass_turn(name):
    """현재 인원의 남은 횟수를 타인에게 랜덤 배분하고 패스"""
    rem = st.session_state.quotas.get(name, 0)
    if rem <= 0: return

    save_history()
    others = [n for n in MEMBER_LIST if n != name and st.session_state.quotas.get(n, 0) > 0]
    
    dist_log = []
    if others:
        for _ in range(rem):
            target = random.choice(others)
            st.session_state.quotas[target] += 1
            dist_log.append(target)
        
        # 누가 받았는지 요약
        summary = {x: dist_log.count(x) for x in set(dist_log)}
        msg = ", ".join([f"{k}(+{v}회)" for k, v in summary.items()])
        st.toast(f"✅ {name}님 패스! 배분 결과: {msg}")
    else:
        st.toast(f"⚠️ 배분할 대상이 없어 {name}님의 {rem}회는 소멸됩니다.")
    
    st.session_state.quotas[name] = 0
    # 다음 순서로 이동
    st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(MEMBER_LIST)
    st.rerun()

# --- 페이지 레이아웃 ---
st.set_page_config(page_title="2026 CARE팀 당직 시스템", layout="wide")

with st.sidebar:
    st.header("⚙️ 설정 및 관리")
    sel_month = st.number_input("배정 월", min_value=1, max_value=12, value=1)
    
    if st.button("📅 데이터 초기화", use_container_width=True):
        st.session_state.update({
            'slots': [], 'quotas': {}, 'selection_order': [], 
            'current_picker_idx': 0, 'history': [], 'quota_info': None
        })
        # 슬롯 생성 로직 (중략 - 기존과 동일)
        cal = calendar.monthcalendar(2026, sel_month)
        heavy_days = set(get_2026_holidays(sel_month))
        new_slots = []
        slot_id = 0
        for week in cal:
            for c_idx, day in enumerate(week):
                if day == 0: continue
                is_heavy = (c_idx == 0 or c_idx == 6 or day in heavy_days)
                if is_heavy:
                    new_slots.append({"day": day, "type": "Day", "owner": None, "id": slot_id, "is_heavy": True})
                    slot_id += 1
                new_slots.append({"day": day, "type": "Night", "owner": None, "id": slot_id, "is_heavy": is_heavy})
                slot_id += 1
        st.session_state.slots = new_slots
        st.rerun()

    st.divider()
    st.session_state.manual_mode = st.toggle("🛠️ 수동 관리자 모드 전환")
    if st.session_state.manual_mode:
        st.session_state.admin_selected_member = st.selectbox("배정할 사람 선택", MEMBER_LIST)
        st.caption("수동 모드에서는 순서와 상관없이 달력을 눌러 배정할 수 있습니다.")

    st.divider()
    st.header("👤 부재자 설정")
    for name in sorted(MEMBER_LIST):
        with st.expander(f"{name} 설정"):
            is_absent = st.checkbox("부재자", key=f"abs_{name}", value=(name in st.session_state.absentees))
            if is_absent: st.session_state.absentees.add(name)
            else: st.session_state.absentees.discard(name)
            st.session_state.absentee_prefs[name] = st.text_input("희망 ID", value=st.session_state.absentee_prefs[name], key=f"p_{name}")

# --- 메인 화면 ---
st.title(f"📅 2026년 {sel_month}월 CARE팀 당직")

col_info, col_cal = st.columns([1, 2.5])

with col_info:
    st.subheader("🎲 배정 진행")
    c1, c2 = st.columns(2)
    if c1.button("횟수 추첨", use_container_width=True):
        total = len(st.session_state.slots)
        base, extra = divmod(total, len(MEMBER_LIST))
        temp = MEMBER_LIST.copy(); random.shuffle(temp)
        high = sorted(temp[:extra]); low = sorted(temp[extra:])
        st.session_state.quotas = {n: base+1 if n in high else base for n in MEMBER_LIST}
        st.session_state.quota_info = (base+1, high, base, low)

    if c2.button("순서 추첨", use_container_width=True):
        order = MEMBER_LIST.copy(); random.shuffle(order)
        st.session_state.selection_order = order
        st.session_state.current_picker_idx = 0

    if st.session_state.quota_info:
        b1, h1, b2, l2 = st.session_state.quota_info
        st.caption(f"📍 {b1}회: {', '.join(h1)} / {b2}회: {', '.join(l2)}")

    st.divider()
    # 순서 제어 버튼
    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("↩️ 되돌리기", use_container_width=True, disabled=not st.session_state.history):
        undo()
    
    curr_picker = st.session_state.selection_order[st.session_state.current_picker_idx] if st.session_state.selection_order else None
    if btn_col2.button("🚫 패스(배분)", use_container_width=True, disabled=not curr_picker):
        pass_turn(curr_picker)

    st.subheader("📋 실시간 순서")
    if st.session_state.selection_order:
        for idx, name in enumerate(st.session_state.selection_order):
            q = st.session_state.quotas.get(name, 0)
            is_turn = (idx == st.session_state.current_picker_idx and sum(st.session_state.quotas.values()) > 0)
            
            pref_ids = [int(x.strip()) for x in st.session_state.absentee_prefs.get(name, "").split(',') if x.strip().isdigit()]
            rem_prefs = [p_id for p_id in pref_ids if p_id < len(st.session_state.slots) and st.session_state.slots[p_id]['owner'] is None]
            
            prefix = "👉" if is_turn else "•"
            tag = " [부재]" if name in st.session_state.absentees else ""
            pref_txt = f" | 🌟남음: {', '.join(map(str, rem_prefs))}" if rem_prefs else ""
            
            if is_turn:
                st.markdown(f"<div style='background-color:#fff3cd; padding:5px; border-radius:5px;'><b>{prefix} {name} ({q}회){tag}{pref_txt}</b></div>", unsafe_allow_html=True)
                # 부재자 자동 로직
                if name in st.session_state.absentees and q > 0:
                    if rem_prefs: # 희망 날짜 있으면 자동 배정
                        target_id = rem_prefs[0]
                        save_history()
                        st.session_state.slots[target_id]['owner'] = name
                        st.session_state.quotas[name] -= 1
                        st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(MEMBER_LIST)
                        st.rerun()
                    else: # 희망 날짜 없으면 자동 패스
                        st.warning(f"{name}님은 희망 날짜가 없어 자동 패스됩니다.")
                        pass_turn(name)
            else:
                st.write(f"{prefix} {name} ({q}회){tag}{pref_txt}")

with col_cal:
    days_kr = ["일", "월", "화", "수", "목", "금", "토"]
    h_cols = st.columns(7)
    for i, h in enumerate(days_kr):
        h_cols[i].markdown(f"<p style='text-align:center; font-weight:bold; color:{'red' if i in [0,6] else 'black'};'>{h}</p>", unsafe_allow_html=True)

    if st.session_state.slots:
        cal = calendar.monthcalendar(2026, sel_month)
        h_days = get_2026_holidays(sel_month)
        for week in cal:
            w_cols = st.columns(7)
            for i, day in enumerate(week):
                if day == 0: continue
                is_h = (i == 0 or i == 6 or day in h_days)
                with w_cols[i]:
                    st.markdown(f"<p style='color:{'red' if is_h else 'black'}; font-weight:bold;'>{day}일</p>", unsafe_allow_html=True)
                    for s in [sl for sl in st.session_state.slots if sl['day'] == day]:
                        label = f"{s['type'][0]}:{s['id']}"
                        if s['owner']:
                            if st.button(f"[{s['owner']}]", key=f"b{s['id']}", use_container_width=True):
                                if st.session_state.manual_mode: # 수동 모드일 땐 이미 배정된 것도 해제 가능
                                    save_history()
                                    st.session_state.quotas[s['owner']] += 1
                                    s['owner'] = None
                                    st.rerun()
                        else:
                            if st.button(label, key=f"b{s['id']}", use_container_width=True):
                                save_history()
                                if st.session_state.manual_mode:
                                    target = st.session_state.admin_selected_member
                                    s['owner'] = target
                                    st.session_state.quotas[target] -= 1
                                else:
                                    curr = st.session_state.selection_order[st.session_state.current_picker_idx]
                                    if st.session_state.quotas[curr] > 0:
                                        s['owner'] = curr
                                        st.session_state.quotas[curr] -= 1
                                        st.session_state.current_picker_idx = (st.session_state.current_picker_idx + 1) % len(MEMBER_LIST)
                                st.rerun()

# --- 엑셀 및 기타 기능 (중략) ---