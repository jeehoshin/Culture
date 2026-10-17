import { Suspense } from "react";
import EventExplorer from "@/components/EventExplorer";
import { getEvents } from "@/lib/api";

export const dynamic = "force-dynamic";

export default async function Home({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const resolved = await searchParams;
  const params = new URLSearchParams();
  Object.entries(resolved).forEach(([key, value]) => Array.isArray(value) ? value.forEach((item) => params.append(key, item)) : value && params.set(key, value));
  const data = await getEvents(params.toString());
  return <Suspense><EventExplorer initialData={data} /></Suspense>;
}

