"use client";

import { useEffect, useState } from "react";

export default function DetailActions({ eventId, bookingUrl }: { eventId: string; bookingUrl?: string }) {
  const [saved, setSaved] = useState(false);
  const [attended, setAttended] = useState(false);
  const [rating, setRating] = useState(0);

  useEffect(() => {
    const favorites = JSON.parse(localStorage.getItem("culture-favorites") ?? "[]") as string[];
    const attendance = JSON.parse(localStorage.getItem("culture-attendance") ?? "{}") as Record<string, number>;
    queueMicrotask(() => {
      setSaved(favorites.includes(eventId));
      setAttended(eventId in attendance);
      setRating(attendance[eventId] ?? 0);
    });
  }, [eventId]);

  const toggleFavorite = () => {
    const favorites = new Set(JSON.parse(localStorage.getItem("culture-favorites") ?? "[]") as string[]);
    saved ? favorites.delete(eventId) : favorites.add(eventId);
    localStorage.setItem("culture-favorites", JSON.stringify([...favorites]));
    window.dispatchEvent(new Event("culture-favorites-changed"));
    setSaved(!saved);
  };

  const saveAttendance = (nextRating: number) => {
    const attendance = JSON.parse(localStorage.getItem("culture-attendance") ?? "{}") as Record<string, number>;
    attendance[eventId] = nextRating;
    localStorage.setItem("culture-attendance", JSON.stringify(attendance));
    setAttended(true);
    setRating(nextRating);
  };

  return (
    <>
      <div className="detailActions">
        <button onClick={toggleFavorite}>{saved ? "♥ 관심 저장됨" : "♡ 관심 목록"}</button>
        <button onClick={() => saveAttendance(rating || 5)}>{attended ? "✓ 관람 완료" : "관람 완료로 표시"}</button>
        {bookingUrl && <a href={bookingUrl} target="_blank" rel="noreferrer">공식 페이지 ↗</a>}
      </div>
      {attended && <div className="rating" aria-label="개인 평점"><span>내 평점</span>{[1, 2, 3, 4, 5].map((value) => <button key={value} onClick={() => saveAttendance(value)} aria-label={`${value}점`}>{value <= rating ? "★" : "☆"}</button>)}</div>}
      <p className="prototypeNote">로그인 연결 전에는 이 브라우저에 저장됩니다. Supabase 연결 후 계정 데이터로 이전합니다.</p>
    </>
  );
}

