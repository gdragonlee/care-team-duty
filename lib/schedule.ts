import { Slot, ScheduleData } from '@/types';
import { getHolidays } from './holidays';
import { getMonthCalendar } from './calendar';

export function generateSlots(year: number, month: number): ScheduleData {
  const holidays = new Set(getHolidays(year, month));
  const weeks = getMonthCalendar(year, month);
  const slots: Slot[] = [];
  let slotId = 0;

  for (const week of weeks) {
    for (let i = 0; i < 7; i++) {
      const day = week[i];
      if (day === 0) continue;

      // 일요일(0), 토요일(6), 공휴일 → 주간+야간
      const isHeavy = i === 0 || i === 6 || holidays.has(day);

      if (isHeavy) {
        slots.push({ id: slotId++, day, type: 'Day', owner: null, isHeavy: true });
      }
      slots.push({ id: slotId++, day, type: 'Night', owner: null, isHeavy });
    }
  }

  return { year, month, slots };
}
