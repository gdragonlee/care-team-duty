import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'CARE팀 당직 시스템',
  description: '당직 일정 배정 관리 앱',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <body>{children}</body>
    </html>
  );
}
