export interface Slot {
  id: number;
  day: number;
  type: 'Day' | 'Night';
  owner: string | null;
  isHeavy: boolean; // 주말/공휴일 여부
}

export interface ScheduleData {
  year: number;
  month: number;
  slots: Slot[];
}

export interface QuotaInfo {
  highCount: number;
  highMembers: string[];
  lowCount: number;
  lowMembers: string[];
}

export interface HistorySnapshot {
  slots: Slot[];
  quotas: Record<string, number>;
  currentPickerIdx: number;
  passLog: string;
}
