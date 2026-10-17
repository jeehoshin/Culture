import Link from "next/link";
import { notFound } from "next/navigation";
import DetailActions from "@/components/DetailActions";
import { getEvent } from "@/lib/api";

const labels = { exhibition: "전시", play: "연극", musical: "뮤지컬" };

export default async function EventDetail({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const event = await getEvent(id);
  if (!event) notFound();
  return (
    <main className="detailPage">
      <Link href="/" className="backLink">← 목록으로</Link>
      <div className="detailGrid">
        <div className={`detailPoster ${event.category}`}><span>{labels[event.category]}</span><strong>{event.title}</strong></div>
        <article className="detailContent">
          <span className="categoryPill">{labels[event.category]}</span>
          <h1>{event.title}</h1>
          <dl><div><dt>기간</dt><dd>{event.start_date} – {event.end_date}</dd></div><div><dt>장소</dt><dd>{event.venue_name} · {event.district}</dd></div><div><dt>가격</dt><dd>{event.price_text ?? "가격 정보 없음"}</dd></div></dl>
          {event.description && <p className="description">{event.description}</p>}
          <DetailActions eventId={event.id} bookingUrl={event.booking_url} />
          <section className="sourceBox"><h2>데이터 출처</h2>{event.sources.map((source) => <p key={source.source}>{source.attribution}{source.external_url && <> · <a href={source.external_url}>원문 보기</a></>}</p>)}<small>마지막 갱신 {new Date(event.updated_at).toLocaleString("ko-KR")}</small></section>
        </article>
      </div>
    </main>
  );
}

