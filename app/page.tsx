import { readJSON } from '@/lib/storage';
import DutyApp from '@/components/DutyApp';

const DEFAULT_MEMBERS = [
  '양기윤', '전소영', '임채성', '홍부휘', '이지용',
  '조현진', '정용채', '강창신', '김덕기', '우성대', '홍그린', '강다현',
];

export default function Page() {
  // 서버에서 초기 팀원 목록을 로드
  const initMembers = readJSON<string[]>('members.json', DEFAULT_MEMBERS);
  return <DutyApp initMembers={initMembers} />;
}
