import { createClient, type SupabaseClient, type User } from "@supabase/supabase-js";

let client: SupabaseClient | null | undefined;

export function getSupabase(): SupabaseClient | null {
  if (client !== undefined) return client;
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  client = url && key ? createClient(url, key) : null;
  return client;
}

export async function getCurrentUser(): Promise<User | null> {
  const supabase = getSupabase();
  if (!supabase) return null;
  const { data } = await supabase.auth.getUser();
  return data.user;
}

const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

export async function migrateBrowserData(userId: string) {
  const supabase = getSupabase();
  if (!supabase) return;
  const favoriteIds = (JSON.parse(localStorage.getItem("culture-favorites") ?? "[]") as string[])
    .filter((id) => UUID_PATTERN.test(id));
  const attendance = JSON.parse(localStorage.getItem("culture-attendance") ?? "{}") as Record<string, number>;

  if (favoriteIds.length) {
    const { error } = await supabase.from("favorites").upsert(
      favoriteIds.map((eventId) => ({ user_id: userId, event_id: eventId })),
      { onConflict: "user_id,event_id", ignoreDuplicates: true },
    );
    if (error) throw error;
  }
  const attendanceRows = Object.entries(attendance)
    .filter(([eventId, rating]) => UUID_PATTERN.test(eventId) && rating >= 1 && rating <= 5)
    .map(([eventId, rating]) => ({ user_id: userId, event_id: eventId, rating }));
  if (attendanceRows.length) {
    const { error } = await supabase.from("attendance").upsert(attendanceRows, { onConflict: "user_id,event_id" });
    if (error) throw error;
  }
  localStorage.removeItem("culture-favorites");
  localStorage.removeItem("culture-attendance");
}

export async function loadFavoriteIds(): Promise<string[]> {
  const supabase = getSupabase();
  const user = await getCurrentUser();
  if (!supabase || !user) return JSON.parse(localStorage.getItem("culture-favorites") ?? "[]") as string[];
  const { data, error } = await supabase.from("favorites").select("event_id");
  if (error) throw error;
  return (data ?? []).map((row) => row.event_id as string);
}

export async function setFavorite(eventId: string, saved: boolean) {
  const supabase = getSupabase();
  const user = await getCurrentUser();
  if (!supabase || !user) {
    const ids = new Set(JSON.parse(localStorage.getItem("culture-favorites") ?? "[]") as string[]);
    saved ? ids.add(eventId) : ids.delete(eventId);
    localStorage.setItem("culture-favorites", JSON.stringify([...ids]));
    return;
  }
  const query = saved
    ? supabase.from("favorites").upsert({ user_id: user.id, event_id: eventId })
    : supabase.from("favorites").delete().eq("user_id", user.id).eq("event_id", eventId);
  const { error } = await query;
  if (error) throw error;
}

export async function loadAttendance(eventId: string): Promise<number | null> {
  const supabase = getSupabase();
  const user = await getCurrentUser();
  if (!supabase || !user) {
    const attendance = JSON.parse(localStorage.getItem("culture-attendance") ?? "{}") as Record<string, number>;
    return attendance[eventId] ?? null;
  }
  const { data, error } = await supabase.from("attendance").select("rating").eq("user_id", user.id).eq("event_id", eventId).maybeSingle();
  if (error) throw error;
  return data?.rating ?? null;
}

export async function setAttendance(eventId: string, rating: number) {
  const supabase = getSupabase();
  const user = await getCurrentUser();
  if (!supabase || !user) {
    const attendance = JSON.parse(localStorage.getItem("culture-attendance") ?? "{}") as Record<string, number>;
    attendance[eventId] = rating;
    localStorage.setItem("culture-attendance", JSON.stringify(attendance));
    return;
  }
  const { error } = await supabase.from("attendance").upsert(
    { user_id: user.id, event_id: eventId, rating, attended_on: new Date().toISOString().slice(0, 10) },
    { onConflict: "user_id,event_id" },
  );
  if (error) throw error;
}
