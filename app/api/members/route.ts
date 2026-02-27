import { NextResponse } from 'next/server';
import { readJSON, writeJSON } from '@/lib/storage';

const DEFAULT_MEMBERS = [
  '양기윤', '전소영', '임채성', '홍부휘', '이지용',
  '조현진', '정용채', '강창신', '김덕기', '우성대', '홍그린', '강다현',
];

export async function GET() {
  const members = readJSON<string[]>('members.json', DEFAULT_MEMBERS);
  return NextResponse.json(members);
}

export async function POST(request: Request) {
  const { name } = await request.json();
  const trimmed = name?.trim();
  if (!trimmed) {
    return NextResponse.json({ error: '이름을 입력하세요.' }, { status: 400 });
  }
  const members = readJSON<string[]>('members.json', DEFAULT_MEMBERS);
  if (members.includes(trimmed)) {
    return NextResponse.json({ error: '이미 존재하는 이름입니다.' }, { status: 409 });
  }
  members.push(trimmed);
  writeJSON('members.json', members);
  return NextResponse.json(members);
}

export async function DELETE(request: Request) {
  const { name } = await request.json();
  const members = readJSON<string[]>('members.json', DEFAULT_MEMBERS);
  const updated = members.filter((m) => m !== name);
  writeJSON('members.json', updated);
  return NextResponse.json(updated);
}
