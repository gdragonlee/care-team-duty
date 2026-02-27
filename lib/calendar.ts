// 월 달력 계산 - 일요일 시작 (Python calendar.monthcalendar 동일 로직)
export function getMonthCalendar(year: number, month: number): number[][] {
  const firstDay = new Date(year, month - 1, 1).getDay(); // 0=일
  const daysInMonth = new Date(year, month, 0).getDate();

  const weeks: number[][] = [];
  let week: number[] = new Array(7).fill(0);

  for (let day = 1; day <= daysInMonth; day++) {
    const colIdx = (firstDay + day - 1) % 7;
    week[colIdx] = day;
    if (colIdx === 6 || day === daysInMonth) {
      weeks.push([...week]);
      week = new Array(7).fill(0);
    }
  }

  return weeks;
}
