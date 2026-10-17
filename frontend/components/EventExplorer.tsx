"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import type { Category, CultureEvent, EventResponse } from "@/lib/types";

const CATEGORY_LABEL: Record<Category, string> = { exhibition: "전시", play: "연극", musical: "뮤지컬" };
const districts = ["종로구", "중구", "용산구", "송파구"];

function formatDate(value: string) {
  return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric" }).format(new Date(`${value}T00:00:00`));
}

function formatUpdatedAt(value: string) {
  return new Intl.DateTimeFormat("ko-KR", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(new Date(value));
}

function EventCard({ event }: { event: CultureEvent }) {
  const [saved, setSaved] = useState(false);
  useEffect(() => {
    const ids = JSON.parse(localStorage.getItem("culture-favorites") ?? "[]") as string[];
    queueMicrotask(() => setSaved(ids.includes(event.id)));
  }, [event.id]);

  const toggleSaved = () => {
    const ids = new Set(JSON.parse(localStorage.getItem("culture-favorites") ?? "[]") as string[]);
    saved ? ids.delete(event.id) : ids.add(event.id);
    localStorage.setItem("culture-favorites", JSON.stringify([...ids]));
    window.dispatchEvent(new Event("culture-favorites-changed"));
    setSaved(!saved);
  };

  return (
    <article className="eventCard">
      <div className={`posterPlaceholder ${event.category}`} aria-hidden="true">
        <span>{CATEGORY_LABEL[event.category]}</span>
        <b>{event.title.slice(0, 2)}</b>
      </div>
      <div className="cardBody">
        <div className="cardMeta"><span className="categoryPill">{CATEGORY_LABEL[event.category]}</span><span>{event.district}</span></div>
        <Link href={`/events/${event.id}`} className="eventTitle" onClick={() => sessionStorage.setItem("event-list-scroll", String(window.scrollY))}>{event.title}</Link>
        <p>{event.venue_name}</p>
        <p>{formatDate(event.start_date)} – {formatDate(event.end_date)}</p>
        <div className="cardFooter"><strong>{event.price_text ?? "가격 정보 없음"}</strong><button className={saved ? "saveButton saved" : "saveButton"} onClick={toggleSaved} aria-label={saved ? "관심 목록에서 삭제" : "관심 목록에 추가"}>{saved ? "♥" : "♡"}</button></div>
      </div>
    </article>
  );
}

export default function EventExplorer({ initialData }: { initialData: EventResponse }) {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const [data, setData] = useState(initialData);
  const [favoriteIds, setFavoriteIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [query, setQuery] = useState(searchParams.get("q") ?? "");

  const selectedCategories = useMemo(() => new Set(searchParams.getAll("category")), [searchParams]);
  const setParams = (updates: Record<string, string | string[] | null>) => {
    const params = new URLSearchParams(searchParams.toString());
    Object.entries(updates).forEach(([key, value]) => {
      params.delete(key);
      if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
      else if (value) params.set(key, value);
    });
    router.replace(`${pathname}?${params.toString()}`, { scroll: false });
  };

  useEffect(() => {
    const controller = new AbortController();
    fetch(`${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/api/v1/events?${searchParams.toString()}`, { signal: controller.signal })
      .then((response) => response.json())
      .then(setData)
      .catch((error) => { if (error.name !== "AbortError") console.error(error); })
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, [searchParams]);

  useEffect(() => {
    const savedPosition = sessionStorage.getItem("event-list-scroll");
    if (savedPosition) requestAnimationFrame(() => window.scrollTo({ top: Number(savedPosition), behavior: "auto" }));
    const refreshFavorites = () => setFavoriteIds(JSON.parse(localStorage.getItem("culture-favorites") ?? "[]") as string[]);
    refreshFavorites();
    window.addEventListener("culture-favorites-changed", refreshFavorites);
    return () => window.removeEventListener("culture-favorites-changed", refreshFavorites);
  }, []);

  const toggleCategory = (category: Category) => {
    const next = new Set(selectedCategories);
    next.has(category) ? next.delete(category) : next.add(category);
    setParams({ category: [...next] });
  };

  const visibleItems = searchParams.get("saved") === "1"
    ? data.items.filter((event) => favoriteIds.includes(event.id))
    : data.items;

  return (
    <main>
      <section className="hero">
        <p className="eyebrow">SEOUL · CULTURE · NOW</p>
        <h1>오늘, 서울에서<br /><em>무엇을 볼까요?</em></h1>
        <p>흩어진 전시와 공연 정보를 한데 모아, 원하는 순간을 빠르게 찾습니다.</p>
        <form className="searchBar" onSubmit={(event) => { event.preventDefault(); setParams({ q: query || null }); }}>
          <span aria-hidden="true">⌕</span><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="행사명이나 장소를 검색하세요" aria-label="행사 검색" /><button>검색</button>
        </form>
      </section>

      <section className="quickFilters" aria-label="빠른 필터">
        {[['today', '오늘 볼 수 있음'], ['weekend', '이번 주말'], ['ending-soon', '곧 종료']].map(([value, label]) => (
          <button key={value} className={searchParams.get("quick") === value ? "active" : ""} onClick={() => setParams({ quick: searchParams.get("quick") === value ? null : value })}>{label}</button>
        ))}
      </section>

      <div className="contentLayout">
        <aside className="filterPanel">
          <div className="filterTitle"><h2>필터</h2><button onClick={() => { setQuery(""); router.replace(pathname); }}>초기화</button></div>
          <fieldset><legend>분야</legend>{(["exhibition", "play", "musical"] as Category[]).map((category) => <label key={category}><input type="checkbox" checked={selectedCategories.has(category)} onChange={() => toggleCategory(category)} />{CATEGORY_LABEL[category]}</label>)}</fieldset>
          <fieldset><legend>날짜</legend><label>시작일<input type="date" value={searchParams.get("date_from") ?? ""} onChange={(e) => setParams({ date_from: e.target.value || null })} /></label><label>종료일<input type="date" value={searchParams.get("date_to") ?? ""} onChange={(e) => setParams({ date_to: e.target.value || null })} /></label></fieldset>
          <fieldset><legend>지역</legend><select value={searchParams.get("district") ?? ""} onChange={(e) => setParams({ district: e.target.value || null })}><option value="">서울 전체</option>{districts.map((district) => <option key={district}>{district}</option>)}</select></fieldset>
          <fieldset><legend>가격</legend><label><input type="radio" name="price" checked={!searchParams.get("price")} onChange={() => setParams({ price: null })} />전체</label><label><input type="radio" name="price" checked={searchParams.get("price") === "free"} onChange={() => setParams({ price: "free" })} />무료</label><label><input type="radio" name="price" checked={searchParams.get("price") === "paid"} onChange={() => setParams({ price: "paid" })} />유료</label></fieldset>
        </aside>

        <section className="results" aria-live="polite">
          <div className="resultHeader"><div><h2>{searchParams.get("saved") === "1" ? "관심 목록" : "지금 만날 수 있는 문화"}</h2><p><strong>{searchParams.get("saved") === "1" ? visibleItems.length : data.total}</strong>개의 행사를 찾았어요 · {formatUpdatedAt(data.last_synced_at)} 갱신</p></div><select aria-label="정렬" value={searchParams.get("sort") ?? "end_date"} onChange={(e) => setParams({ sort: e.target.value })}><option value="end_date">종료일순</option><option value="price">가격순</option><option value="recent">최근 등록순</option></select></div>
          <div className={loading ? "eventGrid loading" : "eventGrid"}>{visibleItems.map((event) => <EventCard event={event} key={event.id} />)}</div>
          {!visibleItems.length && <div className="emptyState"><b>{searchParams.get("saved") === "1" ? "아직 저장한 행사가 없어요." : "조건에 맞는 행사가 없어요."}</b><p>{searchParams.get("saved") === "1" ? "마음에 드는 행사에서 하트를 눌러보세요." : "날짜나 지역 필터를 조금 넓혀보세요."}</p></div>}
        </section>
      </div>
    </main>
  );
}

