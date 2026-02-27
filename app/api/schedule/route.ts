import { NextRequest, NextResponse } from 'next/server';
import { readJSON, writeJSON } from '@/lib/storage';
import { generateSlots } from '@/lib/schedule';
import { ScheduleData } from '@/types';

function scheduleKey(year: number, month: number) {
  return `schedule_${year}_${String(month).padStart(2, '0')}.json`;
}

// GET /api/schedule?year=2026&month=1
export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl;
  const year = parseInt(searchParams.get('year') ?? '0');
  const month = parseInt(searchParams.get('month') ?? '0');
  if (!year || !month) {
    return NextResponse.json({ error: 'year, month 필요' }, { status: 400 });
  }
  const data = readJSON<ScheduleData | null>(scheduleKey(year, month), null);
  return NextResponse.json(data);
}

// POST /api/schedule
// body: { year, month, action: 'init' } | { year, month, slots: Slot[] }
export async function POST(request: Request) {
  try {
    const body = await request.json();
    const { year, month } = body;
    if (!year || !month) {
      return NextResponse.json({ error: 'year, month 필요' }, { status: 400 });
    }

    if (body.action === 'init') {
      const data = generateSlots(year, month);
      writeJSON(scheduleKey(year, month), data);
      return NextResponse.json(data);
    }

    if (body.slots) {
      const data: ScheduleData = { year, month, slots: body.slots };
      writeJSON(scheduleKey(year, month), data);
      return NextResponse.json(data);
    }

    return NextResponse.json({ error: '잘못된 요청' }, { status: 400 });
  } catch (e) {
    console.error('schedule POST 오류:', e);
    return NextResponse.json(
      { error: e instanceof Error ? e.message : '서버 오류' },
      { status: 500 }
    );
  }
}
