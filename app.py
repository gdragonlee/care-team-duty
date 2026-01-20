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