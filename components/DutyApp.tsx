'use client';

import { useState, useEffect, useCallback } from 'react';
import { Slot, QuotaInfo, HistorySnapshot } from '@/types';
import { getHolidays } from '@/lib/holidays';
import { getMonthCalendar } from '@/lib/calendar';

// ─── 유틸 ─────────────────────────────────────────────────────────────────────

function shuffle<T>(arr: T[]): T[] {
  const a = [...arr];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

function findNextValid(
  order: string[],
  fromIdx: number,
  quotas: Record<string, number>
): number {
  for (let i = 1; i <= order.length; i++) {
    const idx = (fromIdx + i) % order.length;
    if ((quotas[order[idx]] ?? 0) > 0) return idx;
  }
  return fromIdx;
}

// ─── DutyApp ──────────────────────────────────────────────────────────────────

export default function DutyApp({ initMembers }: { initMembers: string[] }) {
  const today = new Date();

  // 날짜
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth() + 1);

  // 데이터
  const [members, setMembers] = useState<string[]>(initMembers);
  const [slots, setSlots] = useState<Slot[]>([]);

  // 추첨/배정 상태 (세션 전용)
  const [quotas, setQuotas] = useState<Record<string, number>>({});
  const [selOrder, setSelOrder] = useState<string[]>([]);
  const [pickerIdx, setPickerIdx] = useState(0);
  const [history, setHistory] = useState<HistorySnapshot[]>([]);
  const [absentees, setAbsentees] = useState<Set<string>>(new Set());
  const [absentPrefs, setAbsentPrefs] = useState<Record<string, string>>({});
  const [manualMode, setManualMode] = useState(false);
  const [adminMember, setAdminMember] = useState(initMembers[0] ?? '');
  const [quotaInfo, setQuotaInfo] = useState<QuotaInfo | null>(null);
  const [passLog, setPassLog] = useState('');
  const [undoTriggered, setUndoTriggered] = useState(false);

  // UI
  const [newMemberInput, setNewMemberInput] = useState('');
  const [showSidebar, setShowSidebar] = useState(true);
  const [manualOrder, setManualOrder] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);

  // 탭 & 달력 관리자
  const [activeTab, setActiveTab] = useState<'assign' | 'calendar'>('assign');
  const [calAdminMode, setCalAdminMode] = useState(false);
  const [calPinInput, setCalPinInput] = useState('');
  const [editingSlotId, setEditingSlotId] = useState<number | null>(null);
  const ADMIN_PIN = '1234'; // 필요시 변경

  // ── 스케줄 로드 ────────────────────────────────────────────────────────────
  const loadSchedule = useCallback(async (y: number, m: number) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/schedule?year=${y}&month=${m}`);
      const data = await res.json();
      setSlots(data?.slots ?? []);
      setQuotas({});
      setSelOrder([]);
      setPickerIdx(0);
      setHistory([]);
      setPassLog('');
      setQuotaInfo(null);
      setUndoTriggered(false);
    } catch (e) {
      console.error('스케줄 로드 실패:', e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadSchedule(year, month);
  }, [year, month, loadSchedule]);

  // ── 스케줄 저장 ────────────────────────────────────────────────────────────
  const saveSchedule = useCallback(async (newSlots: Slot[]) => {
    await fetch('/api/schedule', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ year, month, slots: newSlots }),
    });
  }, [year, month]);

  // ── 달력 초기화 ────────────────────────────────────────────────────────────
  const initSchedule = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/schedule', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ year, month, action: 'init' }),
      });
      const data = await res.json();
      if (!res.ok) {
        alert(`초기화 실패: ${data.error ?? res.status}`);
        return;
      }
      setSlots(data.slots ?? []);
      setQuotas({});
      setSelOrder([]);
      setPickerIdx(0);
      setHistory([]);
      setPassLog('');
      setQuotaInfo(null);
      setUndoTriggered(false);
    } catch (e) {
      console.error('달력 초기화 실패:', e);
      alert('서버 오류가 발생했습니다. 콘솔을 확인하세요.');
    } finally {
      setLoading(false);
    }
  };

  // ── 히스토리 저장 ──────────────────────────────────────────────────────────
  const saveHistory = (
    curSlots: Slot[],
    curQuotas: Record<string, number>,
    curIdx: number,
    curLog: string
  ) => {
    const snap: HistorySnapshot = {
      slots: curSlots,
      quotas: { ...curQuotas },
      currentPickerIdx: curIdx,
      passLog: curLog,
    };
    setHistory((prev) => [...prev.slice(-19), snap]);
  };

  // ── 횟수 추첨 ──────────────────────────────────────────────────────────────
  const drawQuotas = () => {
    const total = slots.length;
    const n = members.length;
    if (!n || !total) return;
    const base = Math.floor(total / n);
    const extra = total % n;
    const shuffled = shuffle(members);
    const high = shuffled.slice(0, extra).sort();
    const low = shuffled.slice(extra).sort();
    const newQ: Record<string, number> = {};
    members.forEach((m) => { newQ[m] = high.includes(m) ? base + 1 : base; });
    setQuotas(newQ);
    setQuotaInfo({ highCount: base + 1, highMembers: high, lowCount: base, lowMembers: low });
  };

  // ── 순위 추첨 ──────────────────────────────────────────────────────────────
  const drawOrder = () => {
    setSelOrder(shuffle(members));
    setPickerIdx(0);
    setUndoTriggered(false);
  };

  // ── 수동 순위 적용 ─────────────────────────────────────────────────────────
  const applyManualOrder = () => {
    if (manualOrder.length !== members.length) return;
    setSelOrder([...manualOrder]);
    setPickerIdx(0);
    setUndoTriggered(false);
  };

  // ── 패스 ──────────────────────────────────────────────────────────────────
  const passTurn = useCallback(
    (name: string, curSlots: Slot[], curQuotas: Record<string, number>, curIdx: number, curLog: string) => {
      const rem = curQuotas[name] ?? 0;
      if (rem <= 0) return;
      saveHistory(curSlots, curQuotas, curIdx, curLog);

      const others = members.filter((m) => m !== name);
      const newQ = { ...curQuotas };
      if (others.length > 0) {
        const dist = Array.from({ length: rem }, () => others[Math.floor(Math.random() * others.length)]);
        dist.forEach((t) => { newQ[t] = (newQ[t] ?? 0) + 1; });
        const summary = dist.reduce((acc, t) => { acc[t] = (acc[t] ?? 0) + 1; return acc; }, {} as Record<string, number>);
        const logStr = Object.entries(summary).map(([k, v]) => `${k}(+${v}회)`).join(', ');
        setPassLog(`🚫 ${name} 패스 → ${logStr}`);
      }
      newQ[name] = 0;
      setQuotas(newQ);
      const nextIdx = findNextValid(selOrder, curIdx, newQ);
      setPickerIdx(nextIdx);
      setUndoTriggered(false);
    },
    [members, selOrder]
  );

  // ── 슬롯 배정 ──────────────────────────────────────────────────────────────
  const assignSlot = (slotId: number) => {
    const target = manualMode
      ? adminMember
      : selOrder.length > 0 ? selOrder[pickerIdx] : null;

    if (!target) return;
    if (!manualMode && (quotas[target] ?? 0) <= 0) return;

    saveHistory(slots, quotas, pickerIdx, passLog);
    setUndoTriggered(false);

    const newSlots = slots.map((s) => s.id === slotId ? { ...s, owner: target } : s);
    setSlots(newSlots);
    saveSchedule(newSlots);

    if (!manualMode) {
      const newQ = { ...quotas, [target]: (quotas[target] ?? 0) - 1 };
      setQuotas(newQ);
      setPickerIdx(findNextValid(selOrder, pickerIdx, newQ));
    }
  };

  // ── 되돌리기 ──────────────────────────────────────────────────────────────
  const undo = () => {
    if (!history.length) return;
    const last = history[history.length - 1];
    setHistory((prev) => prev.slice(0, -1));
    setSlots(last.slots);
    setQuotas(last.quotas);
    setPickerIdx(last.currentPickerIdx);
    setPassLog(last.passLog);
    setUndoTriggered(true);
    saveSchedule(last.slots);
  };

  // ── 팀원 관리 ──────────────────────────────────────────────────────────────
  const addMember = async () => {
    const name = newMemberInput.trim();
    if (!name) return;
    const res = await fetch('/api/members', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (res.ok) {
      const updated: string[] = await res.json();
      setMembers(updated);
      setNewMemberInput('');
      if (!adminMember) setAdminMember(updated[0]);
    } else {
      const { error } = await res.json();
      alert(error);
    }
  };

  const removeMember = async (name: string) => {
    const res = await fetch('/api/members', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name }),
    });
    if (res.ok) {
      const updated: string[] = await res.json();
      setMembers(updated);
    }
  };

  // ── 관리자 PIN 검증 ────────────────────────────────────────────────────────
  const verifyAdminPin = () => {
    if (calPinInput === ADMIN_PIN) {
      setCalAdminMode(true);
      setCalPinInput('');
    } else {
      alert('PIN이 올바르지 않습니다.');
      setCalPinInput('');
    }
  };

  // ── 달력 탭: 슬롯 담당자 직접 변경 (관리자 전용) ──────────────────────────
  const updateSlotOwner = (slotId: number, newOwner: string | null) => {
    const newSlots = slots.map((s) =>
      s.id === slotId ? { ...s, owner: newOwner } : s
    );
    setSlots(newSlots);
    saveSchedule(newSlots);
    setEditingSlotId(null);
  };

  // ── 엑셀 내보내기 ──────────────────────────────────────────────────────────
  const exportExcel = async () => {
    const XLSX = await import('xlsx');

    const wb = XLSX.utils.book_new();

    // ── 당직표 시트 ──
    const calWeeks = getMonthCalendar(year, month);
    const calHolidays = new Set(getHolidays(year, month));
    const dayMap: Record<number, { Day: string; Night: string }> = {};
    for (let d = 1; d <= 31; d++) dayMap[d] = { Day: '', Night: '' };
    slots.forEach((s) => {
      if (s.owner) dayMap[s.day][s.type] = s.owner;
    });

    const aoa: string[][] = [['일', '월', '화', '수', '목', '금', '토']];
    for (const week of calWeeks) {
      const row: string[] = week.map((day, i) => {
        if (!day) return '';
        const isH = i === 0 || i === 6 || calHolidays.has(day);
        let txt = `[${day}일]`;
        if (isH && dayMap[day].Day) txt += `\n주: ${dayMap[day].Day}`;
        if (dayMap[day].Night) txt += `\n야: ${dayMap[day].Night}`;
        return txt;
      });
      aoa.push(row);
    }
    const ws = XLSX.utils.aoa_to_sheet(aoa);
    ws['!cols'] = Array.from({ length: 7 }, () => ({ wch: 16 }));
    XLSX.utils.book_append_sheet(wb, ws, `${year}.${month}월`);

    // ── 현황요약 시트 ──
    const summary: string[][] = [['이름', '주간', '야간', '합계']];
    const stats: Record<string, { Day: number; Night: number }> = {};
    members.forEach((m) => { stats[m] = { Day: 0, Night: 0 }; });
    slots.forEach((s) => {
      if (s.owner && stats[s.owner]) stats[s.owner][s.type]++;
    });
    members.forEach((m) => {
      summary.push([
        m,
        String(stats[m].Day),
        String(stats[m].Night),
        String(stats[m].Day + stats[m].Night),
      ]);
    });
    const ws2 = XLSX.utils.aoa_to_sheet(summary);
    XLSX.utils.book_append_sheet(wb, ws2, '현황요약');

    // ── 브라우저 다운로드 (fs 사용 안 함) ──
    const buf: ArrayBuffer = XLSX.write(wb, { bookType: 'xlsx', type: 'array' });
    const blob = new Blob([buf], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `CARE팀_${year}_${String(month).padStart(2, '0')}월.xlsx`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // ── 요약 통계 계산 ─────────────────────────────────────────────────────────
  const totalSlots = slots.length;
  const assignedCount = slots.filter((s) => s.owner).length;
  const progress = totalSlots ? Math.round((assignedCount / totalSlots) * 100) : 0;

  const memberStats = members.map((name) => {
    const day = slots.filter((s) => s.owner === name && s.type === 'Day').length;
    const night = slots.filter((s) => s.owner === name && s.type === 'Night').length;
    return { name, day, night, total: day + night };
  });

  // ── 희망슬롯 파싱 ────────────────────────────────────────────────────────────
  // 입력 형식: 평일 → "7" (야간), 주말/공휴일 → "7주"(주간) | "7야"(야간)
  function parsePrefs(prefStr: string, curSlots: Slot[]): { token: string; slot: Slot }[] {
    return prefStr
      .split(',')
      .map((t) => t.trim())
      .filter(Boolean)
      .flatMap((token) => {
        const m = token.match(/^(\d+)(주|야)?$/);
        if (!m) return [];
        const day = parseInt(m[1]);
        const typeHint = m[2];
        const slotType: 'Day' | 'Night' = typeHint === '주' ? 'Day' : 'Night';
        const found = curSlots.find((s) => s.day === day && s.type === slotType);
        return found && found.owner === null ? [{ token, slot: found }] : [];
      });
  }

  // 현재 순번자 부재중 자동 처리
  const currentPicker = selOrder[pickerIdx] ?? null;
  useEffect(() => {
    if (!currentPicker) return;
    if (!absentees.has(currentPicker)) return;
    if (undoTriggered) return;
    const rem = quotas[currentPicker] ?? 0;
    if (rem <= 0) return;

    const availPrefs = parsePrefs(absentPrefs[currentPicker] ?? '', slots);

    if (availPrefs.length > 0) {
      const targetSlot = availPrefs[0].slot;
      saveHistory(slots, quotas, pickerIdx, passLog);
      const newSlots = slots.map((s) => s.id === targetSlot.id ? { ...s, owner: currentPicker } : s);
      setSlots(newSlots);
      saveSchedule(newSlots);
      const newQ = { ...quotas, [currentPicker]: rem - 1 };
      setQuotas(newQ);
      setPickerIdx(findNextValid(selOrder, pickerIdx, newQ));
    } else {
      passTurn(currentPicker, slots, quotas, pickerIdx, passLog);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentPicker]);

  // ─── 렌더링 ────────────────────────────────────────────────────────────────
  const weeks = getMonthCalendar(year, month);
  const holidays = new Set(getHolidays(year, month));
  const DAY_KR = ['일', '월', '화', '수', '목', '금', '토'];

  return (
    <div className="flex min-h-screen bg-gray-950 text-gray-100">
      {/* ── 사이드바 ── */}
      <aside
        className={`${showSidebar ? 'w-72' : 'w-0 overflow-hidden'} shrink-0 transition-all duration-300 bg-gray-900 border-r border-gray-800 flex flex-col`}
      >
        <div className="p-4 space-y-4 overflow-y-auto flex-1">
          {/* 날짜 선택 */}
          <section>
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">달력 설정</h2>
            <div className="flex gap-2 mb-2">
              <input
                type="number" min={2025} max={2030} value={year}
                onChange={(e) => setYear(parseInt(e.target.value))}
                className="w-24 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
              />
              <input
                type="number" min={1} max={12} value={month}
                onChange={(e) => setMonth(parseInt(e.target.value))}
                className="w-16 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
              />
              <span className="self-center text-gray-400 text-sm">년 / 월</span>
            </div>
            <button
              onClick={initSchedule}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white rounded py-2 text-sm font-semibold"
            >
              📅 달력 초기화 (새 달 시작)
            </button>
          </section>

          {/* 추첨 제어 */}
          {slots.length > 0 && (
            <section className="space-y-2">
              <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider">추첨 & 제어</h2>

              <button
                onClick={drawQuotas}
                className="w-full bg-purple-700 hover:bg-purple-600 rounded py-2 text-sm font-semibold"
              >
                🔢 1. 근무 횟수 추첨
              </button>

              {quotaInfo && (
                <div className="bg-gray-800 rounded p-2 text-xs space-y-1">
                  <p><span className="text-yellow-400 font-bold">{quotaInfo.highCount}회</span>: {quotaInfo.highMembers.join(', ')}</p>
                  <p><span className="text-blue-400 font-bold">{quotaInfo.lowCount}회</span>: {quotaInfo.lowMembers.join(', ')}</p>
                </div>
              )}

              <button
                onClick={drawOrder}
                className="w-full bg-teal-700 hover:bg-teal-600 rounded py-2 text-sm font-semibold"
              >
                🏃 2-A. 순위 랜덤 추첨
              </button>

              <details className="bg-gray-800 rounded p-2">
                <summary className="text-sm cursor-pointer font-semibold">🏃 2-B. 순위 수동 조정</summary>
                <div className="mt-2 space-y-1">
                  {members.map((name) => (
                    <label key={name} className="flex items-center gap-2 text-xs cursor-pointer">
                      <input
                        type="checkbox"
                        checked={manualOrder.includes(name)}
                        onChange={(e) => {
                          if (e.target.checked) setManualOrder((p) => [...p, name]);
                          else setManualOrder((p) => p.filter((x) => x !== name));
                        }}
                        className="accent-teal-500"
                      />
                      {name}
                    </label>
                  ))}
                  <button
                    onClick={applyManualOrder}
                    disabled={manualOrder.length !== members.length}
                    className="w-full mt-1 bg-teal-700 disabled:opacity-40 rounded py-1 text-xs"
                  >
                    ✅ 적용 ({manualOrder.length}/{members.length})
                  </button>
                </div>
              </details>

              <div className="flex gap-2">
                <button
                  onClick={undo}
                  disabled={!history.length}
                  className="flex-1 bg-gray-700 hover:bg-gray-600 disabled:opacity-40 rounded py-2 text-sm font-semibold"
                >
                  ↩️ 되돌리기
                </button>
                <button
                  onClick={() => selOrder.length > 0 && passTurn(selOrder[pickerIdx], slots, quotas, pickerIdx, passLog)}
                  className="flex-1 bg-red-800 hover:bg-red-700 rounded py-2 text-sm font-semibold"
                >
                  🚫 패스
                </button>
              </div>

              {passLog && (
                <div className="bg-yellow-900/50 border border-yellow-700 rounded p-2 text-xs">{passLog}</div>
              )}
            </section>
          )}

          {/* 수동 모드 */}
          <section className="space-y-2">
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider">배정 모드</h2>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={manualMode}
                onChange={(e) => setManualMode(e.target.checked)}
                className="accent-orange-500 w-4 h-4"
              />
              <span className="text-sm">🛡️ 수동 모드 (순번 무시)</span>
            </label>
            {manualMode && (
              <select
                value={adminMember}
                onChange={(e) => setAdminMember(e.target.value)}
                className="w-full bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
              >
                {members.map((m) => <option key={m}>{m}</option>)}
              </select>
            )}
          </section>

          {/* 팀원 관리 */}
          <section className="space-y-2">
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider">👥 팀원 관리</h2>
            <div className="flex gap-1">
              <input
                value={newMemberInput}
                onChange={(e) => setNewMemberInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && addMember()}
                placeholder="새 팀원 이름"
                className="flex-1 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
              />
              <button
                onClick={addMember}
                className="bg-green-700 hover:bg-green-600 rounded px-3 py-1 text-sm font-bold"
              >
                ➕
              </button>
            </div>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {members.map((name) => (
                <div key={name} className="flex items-center justify-between bg-gray-800 rounded px-2 py-1">
                  <span className="text-sm">👤 {name}</span>
                  <button
                    onClick={() => removeMember(name)}
                    className="text-red-400 hover:text-red-300 text-xs"
                  >
                    🗑️
                  </button>
                </div>
              ))}
            </div>
          </section>

          {/* 개인 설정 */}
          <section className="space-y-2">
            <h2 className="text-sm font-bold text-gray-400 uppercase tracking-wider">📋 개인 설정</h2>
            {members.map((name) => (
              <details key={name} className="bg-gray-800 rounded">
                <summary className="px-2 py-1 text-sm cursor-pointer flex items-center justify-between">
                  <span>{name}</span>
                  {absentees.has(name) && <span className="text-red-400 text-xs">[부재중]</span>}
                </summary>
                <div className="px-2 pb-2 space-y-1">
                  <label className="flex items-center gap-2 text-xs cursor-pointer">
                    <input
                      type="checkbox"
                      checked={absentees.has(name)}
                      onChange={(e) => {
                        setAbsentees((prev) => {
                          const next = new Set(prev);
                          if (e.target.checked) next.add(name); else next.delete(name);
                          return next;
                        });
                      }}
                      className="accent-red-500"
                    />
                    부재중
                  </label>
                  <input
                    value={absentPrefs[name] ?? ''}
                    onChange={(e) => setAbsentPrefs((p) => ({ ...p, [name]: e.target.value }))}
                    placeholder="평일:7 / 주말·공휴일:7주,7야"
                    className="w-full bg-gray-700 rounded px-1 py-0.5 text-xs"
                  />
                  <p className="text-gray-500 text-xs mt-0.5">
                    평일 야간 → 날짜만 (예: 7)<br/>
                    주말/공휴일 주간 → 날짜+주 (예: 7주)<br/>
                    주말/공휴일 야간 → 날짜+야 (예: 7야)
                  </p>
                </div>
              </details>
            ))}
          </section>
        </div>
      </aside>

      {/* ── 메인 영역 ── */}
      <main className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* 헤더 */}
        <header className="shrink-0 px-4 py-3 border-b border-gray-800 flex items-center gap-3 bg-gray-900">
          <button
            onClick={() => setShowSidebar((p) => !p)}
            className="text-gray-400 hover:text-white"
          >
            ☰
          </button>
          <h1 className="text-lg font-bold">
            📅 {year}년 {month}월 당직
          </h1>
          {loading && <span className="text-gray-400 text-sm animate-pulse">로딩중...</span>}

          {/* 탭 버튼 */}
          <div className="flex bg-gray-800 rounded-lg p-0.5 ml-2">
            <button
              onClick={() => setActiveTab('assign')}
              className={`px-3 py-1 rounded text-sm font-semibold transition-colors ${
                activeTab === 'assign'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              ✏️ 배정
            </button>
            <button
              onClick={() => { setActiveTab('calendar'); setEditingSlotId(null); }}
              className={`px-3 py-1 rounded text-sm font-semibold transition-colors ${
                activeTab === 'calendar'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              📋 확정 달력
            </button>
          </div>

          <div className="ml-auto flex items-center gap-2">
            {slots.length > 0 && (
              <button
                onClick={exportExcel}
                className="bg-green-700 hover:bg-green-600 rounded px-3 py-1.5 text-sm font-semibold"
              >
                💾 엑셀 저장
              </button>
            )}
          </div>
        </header>

        {/* ── 배정 탭 ── */}
        {activeTab === 'assign' && (<><div className="flex-1 flex overflow-hidden">
          {/* 순번 큐 */}
          {selOrder.length > 0 && (
            <div className="w-48 shrink-0 bg-gray-900 border-r border-gray-800 overflow-y-auto p-3">
              <h3 className="text-xs font-bold text-gray-400 uppercase mb-2">순위별 대기열</h3>
              {selOrder.map((name, idx) => {
                const q = quotas[name] ?? 0;
                if (q <= 0) return null;
                const isTurn = idx === pickerIdx;
                const availPrefs = parsePrefs(absentPrefs[name] ?? '', slots);
                return (
                  <div
                    key={name}
                    className={`mb-1.5 rounded px-2 py-1.5 text-xs ${
                      isTurn
                        ? 'bg-orange-900/70 border border-orange-600'
                        : 'bg-gray-800'
                    }`}
                  >
                    <div className="flex items-center gap-1">
                      {isTurn && <span>👉</span>}
                      <span className="font-bold">{idx + 1}위 {name}</span>
                      {absentees.has(name) && <span className="text-red-400">[부재]</span>}
                    </div>
                    <div className="text-gray-400">{q}회 남음</div>
                    {availPrefs.length > 0 && (
                      <div className="text-yellow-400 mt-0.5">
                        🌟 {availPrefs.map((p) => p.token).join(', ')}
                      </div>
                    )}
                    {undoTriggered && isTurn && (
                      <button
                        onClick={() => setUndoTriggered(false)}
                        className="mt-1 w-full bg-gray-700 rounded py-0.5 text-xs"
                      >
                        자동배정 재개
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* 캘린더 그리드 */}
          <div className="flex-1 overflow-auto p-3">
            {slots.length === 0 ? (
              <div className="flex items-center justify-center h-full text-gray-500">
                <div className="text-center">
                  <p className="text-4xl mb-3">📅</p>
                  <p className="text-lg">달력을 초기화하세요</p>
                  <p className="text-sm mt-1">왼쪽 패널에서 <strong>달력 초기화</strong>를 클릭하세요</p>
                </div>
              </div>
            ) : (
              <>
                {/* 요일 헤더 */}
                <div className="grid grid-cols-7 gap-1 mb-1">
                  {DAY_KR.map((d, i) => (
                    <div
                      key={d}
                      className={`text-center text-sm font-bold py-1.5 rounded ${
                        i === 0 ? 'text-red-400' : i === 6 ? 'text-blue-400' : 'text-gray-300'
                      }`}
                    >
                      {d}
                    </div>
                  ))}
                </div>

                {/* 주 행 */}
                {weeks.map((week, wi) => (
                  <div key={wi} className="grid grid-cols-7 gap-1 mb-1">
                    {week.map((day, ci) => {
                      if (!day) return <div key={ci} />;
                      const isH = ci === 0 || ci === 6 || holidays.has(day);
                      const daySlots = slots.filter((s) => s.day === day);
                      return (
                        <div
                          key={ci}
                          className={`min-h-20 rounded p-1 border ${
                            isH ? 'bg-red-950/30 border-red-900/50' : 'bg-gray-900 border-gray-800'
                          }`}
                        >
                          <div
                            className={`text-xs font-bold mb-1 ${
                              ci === 0 ? 'text-red-400' : ci === 6 ? 'text-blue-400' : 'text-gray-300'
                            }`}
                          >
                            {day}
                          </div>
                          {daySlots.map((s) => (
                            <button
                              key={s.id}
                              onClick={() => !s.owner && assignSlot(s.id)}
                              disabled={!!s.owner}
                              className={`w-full text-xs rounded px-1 py-0.5 mb-0.5 text-left truncate transition-colors ${
                                s.owner
                                  ? 'bg-gray-700 text-gray-300 cursor-default'
                                  : s.type === 'Day'
                                  ? 'bg-blue-800 hover:bg-blue-700 text-blue-100'
                                  : 'bg-purple-900 hover:bg-purple-800 text-purple-100'
                              }`}
                            >
                              {s.owner
                                ? `👤 ${s.owner}`
                                : s.type === 'Day' ? '🌅 주간' : '🌙 야간'}
                            </button>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                ))}
              </>
            )}
          </div>
        </div>

        {/* 하단 요약 */}
        {slots.length > 0 && (
          <footer className="shrink-0 border-t border-gray-800 bg-gray-900 p-3 flex-none">
            <div className="flex items-center gap-3 mb-3">
              <span className="text-xs text-gray-400 shrink-0">배정 진행률</span>
              <div className="flex-1 bg-gray-800 rounded-full h-2">
                <div
                  className="bg-green-500 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
              <span className="text-xs text-gray-300 shrink-0">
                {assignedCount}/{totalSlots} ({progress}%)
              </span>
            </div>
            <div className="grid grid-cols-4 gap-1 md:grid-cols-6 lg:grid-cols-12">
              {memberStats.map(({ name, day, night, total }) => (
                <div key={name} className="bg-gray-800 rounded p-1.5 text-center">
                  <div className="text-xs font-bold truncate">{name}</div>
                  <div className="text-base font-bold text-white">{total}</div>
                  <div className="text-xs text-gray-400">주{day}/야{night}</div>
                </div>
              ))}
            </div>
          </footer>
        )}</>)}

        {/* ── 확정 달력 탭 ── */}
        {activeTab === 'calendar' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* 관리자 바 */}
            <div className="shrink-0 px-4 py-2 bg-gray-900 border-b border-gray-800 flex items-center gap-3">
              {calAdminMode ? (
                <>
                  <span className="text-green-400 text-sm font-semibold">🔓 관리자 편집 모드</span>
                  <span className="text-gray-400 text-xs">슬롯을 클릭하면 담당자를 변경할 수 있습니다</span>
                  <button
                    onClick={() => { setCalAdminMode(false); setEditingSlotId(null); }}
                    className="ml-auto bg-gray-700 hover:bg-gray-600 rounded px-3 py-1 text-xs font-semibold"
                  >
                    🔒 잠금
                  </button>
                </>
              ) : (
                <>
                  <input
                    type="password"
                    value={calPinInput}
                    onChange={(e) => setCalPinInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && verifyAdminPin()}
                    placeholder="관리자 PIN"
                    className="w-32 bg-gray-800 border border-gray-700 rounded px-2 py-1 text-sm"
                  />
                  <button
                    onClick={verifyAdminPin}
                    className="bg-amber-700 hover:bg-amber-600 rounded px-3 py-1 text-sm font-semibold"
                  >
                    🔐 관리자 접속
                  </button>
                  <span className="text-gray-500 text-xs">관리자만 일정을 수정할 수 있습니다</span>
                </>
              )}
            </div>

            {/* 달력 본체 */}
            <div className="flex-1 overflow-auto p-4">
              {slots.length === 0 ? (
                <div className="flex items-center justify-center h-48 text-gray-500">
                  <div className="text-center">
                    <p className="text-3xl mb-2">📅</p>
                    <p>배정 탭에서 먼저 달력을 초기화하세요</p>
                  </div>
                </div>
              ) : (
                <>
                  {/* 요일 헤더 */}
                  <div className="grid grid-cols-7 gap-2 mb-2">
                    {DAY_KR.map((d, i) => (
                      <div
                        key={d}
                        className={`text-center text-sm font-bold py-2 rounded bg-gray-900 ${
                          i === 0 ? 'text-red-400' : i === 6 ? 'text-blue-400' : 'text-gray-300'
                        }`}
                      >
                        {d}
                      </div>
                    ))}
                  </div>

                  {/* 주 행 */}
                  {weeks.map((week, wi) => (
                    <div key={wi} className="grid grid-cols-7 gap-2 mb-2">
                      {week.map((day, ci) => {
                        if (!day) return <div key={ci} />;
                        const isH = ci === 0 || ci === 6 || holidays.has(day);
                        const daySlots = slots.filter((s) => s.day === day);
                        return (
                          <div
                            key={ci}
                            className={`rounded-lg p-2 border min-h-24 ${
                              isH
                                ? 'bg-red-950/40 border-red-900/50'
                                : 'bg-gray-900/80 border-gray-800'
                            }`}
                          >
                            {/* 날짜 */}
                            <div className={`text-sm font-bold mb-2 flex items-center gap-1 ${
                              ci === 0 ? 'text-red-400' : ci === 6 ? 'text-blue-400' : 'text-gray-200'
                            }`}>
                              {day}일
                              {isH && ci !== 0 && ci !== 6 && (
                                <span className="text-xs text-red-400 font-normal">공휴</span>
                              )}
                            </div>

                            {/* 슬롯 */}
                            {daySlots.map((s) => (
                              <div key={s.id} className="mb-1.5">
                                <div className={`text-xs mb-0.5 ${
                                  s.type === 'Day' ? 'text-blue-400' : 'text-purple-400'
                                }`}>
                                  {s.type === 'Day' ? '🌅 주간' : '🌙 야간'}
                                </div>
                                {editingSlotId === s.id ? (
                                  <select
                                    autoFocus
                                    value={s.owner ?? ''}
                                    onChange={(e) =>
                                      updateSlotOwner(s.id, e.target.value || null)
                                    }
                                    onBlur={() => setEditingSlotId(null)}
                                    className="w-full bg-gray-700 border border-amber-500 rounded px-1 py-0.5 text-xs text-white"
                                  >
                                    <option value="">미배정</option>
                                    {members.map((m) => (
                                      <option key={m} value={m}>{m}</option>
                                    ))}
                                  </select>
                                ) : (
                                  <div
                                    onClick={() => calAdminMode && setEditingSlotId(s.id)}
                                    className={`rounded px-2 py-1 text-xs font-medium transition-all ${
                                      s.owner
                                        ? s.type === 'Day'
                                          ? 'bg-blue-900/60 text-blue-100'
                                          : 'bg-purple-900/60 text-purple-100'
                                        : 'bg-gray-800 text-gray-500 italic'
                                    } ${
                                      calAdminMode
                                        ? 'cursor-pointer hover:ring-1 hover:ring-amber-500 hover:brightness-110'
                                        : ''
                                    }`}
                                  >
                                    {s.owner ? `👤 ${s.owner}` : '미배정'}
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>
                        );
                      })}
                    </div>
                  ))}
                </>
              )}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
