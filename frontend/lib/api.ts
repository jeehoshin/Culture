import type { CultureEvent, EventResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function getEvents(search = ""): Promise<EventResponse> {
  const response = await fetch(`${API_URL}/api/v1/events${search ? `?${search}` : ""}`, {
    cache: "no-store",
  });
  if (!response.ok) throw new Error("행사 목록을 불러오지 못했습니다.");
  return response.json();
}

export async function getEvent(id: string): Promise<CultureEvent | null> {
  const response = await fetch(`${API_URL}/api/v1/events/${id}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error("행사 정보를 불러오지 못했습니다.");
  return response.json();
}

