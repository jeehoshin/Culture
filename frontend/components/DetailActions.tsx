"use client";

import { useEffect, useState } from "react";
import { getCurrentUser, loadAttendance, loadFavoriteIds, setAttendance, setFavorite } from "@/lib/supabase";

export default function DetailActions({ eventId, bookingUrl }: { eventId: string; bookingUrl?: string }) {
  const [saved, setSaved] = useState(false);
  const [attended, setAttended] = useState(false);
  const [rating, setRating] = useState(0);
  const [signedIn, setSignedIn] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const refresh = async () => {
      try {
        const [favorites, attendance, user] = await Promise.all([loadFavoriteIds(), loadAttendance(eventId), getCurrentUser()]);
        setSaved(favorites.includes(eventId));
        setAttended(attendance !== null);
        setRating(attendance ?? 0);
        setSignedIn(Boolean(user));
      } catch { setError("저장 정보를 불러오지 못했습니다."); }
    };
    void refresh();
    window.addEventListener("culture-auth-changed", refresh);
    return () => window.removeEventListener("culture-auth-changed", refresh);
  }, [eventId]);

  const toggleFavorite = async () => {
    const next = !saved;
    try {
      await setFavorite(eventId, next);
      setSaved(next);
      window.dispatchEvent(new Event("culture-favorites-changed"));
    } catch { setError("관심 목록을 저장하지 못했습니다."); }
  };

  const saveAttendance = async (nextRating: number) => {
    try {
      await setAttendance(eventId, nextRating);
      setAttended(true);
      setRating(nextRating);
    } catch { setError("관람 기록을 저장하지 못했습니다."); }
  };

  return (
    <>
      <div className="detailActions">
        <button onClick={toggleFavorite}>{saved ? "♥ 관심 저장됨" : "♡ 관심 목록"}</button>
        <button onClick={() => saveAttendance(rating || 5)}>{attended ? "✓ 관람 완료" : "관람 완료로 표시"}</button>
        {bookingUrl && <a href={bookingUrl} target="_blank" rel="noreferrer">공식 페이지 ↗</a>}
      </div>
      {attended && <div className="rating" aria-label="개인 평점"><span>내 평점</span>{[1, 2, 3, 4, 5].map((value) => <button key={value} onClick={() => saveAttendance(value)} aria-label={`${value}점`}>{value <= rating ? "★" : "☆"}</button>)}</div>}
      <p className="prototypeNote">{signedIn ? "관심 목록과 관람 기록이 계정에 저장됩니다." : "로그인하지 않은 기록은 이 브라우저에 저장되며, 로그인하면 계정으로 이전됩니다."}</p>
      {error && <p className="actionError">{error}</p>}
    </>
  );
}

