import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "오늘의 문화 — 서울 전시·공연 찾기",
  description: "서울의 전시, 연극, 뮤지컬을 날짜·지역·가격으로 빠르게 찾아보세요.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="ko" data-scroll-behavior="smooth">
      <body>
        <header className="siteHeader">
          <Link href="/" className="brand" aria-label="오늘의 문화 홈">
            <span className="brandMark">오</span>
            <span>오늘의 문화</span>
          </Link>
          <nav aria-label="주요 메뉴">
            <Link href="/">둘러보기</Link>
            <Link href="/?saved=1">관심 목록</Link>
          </nav>
        </header>
        {children}
        <footer>공공 문화 데이터를 더 가볍게 만나는 방법 · 출처는 각 행사 상세에서 확인하세요.</footer>
      </body>
    </html>
  );
}

