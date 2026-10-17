-- Keep event history and user records intact while removing expired events from
-- the active catalogue. This is intentionally a soft delete.
create or replace function public.deactivate_expired_events()
returns integer
language plpgsql
security definer
set search_path = public
as $$
declare
  affected integer;
begin
  update public.events
  set is_active = false,
      updated_at = now()
  where is_active = true
    and end_date < current_date;
  get diagnostics affected = row_count;
  return affected;
end;
$$;

revoke all on function public.deactivate_expired_events() from public, anon, authenticated;
grant execute on function public.deactivate_expired_events() to service_role;

-- KOPIS currently serves public detail pages reliably through its mobile route.
update public.event_sources
set source_url = 'https://kopis.or.kr/mob/db/pblprfrView.do?mt20Id=' || external_id
where source = 'kopis';

update public.events e
set booking_url = es.source_url,
    updated_at = now()
from public.event_sources es
where es.event_id = e.id
  and es.source = 'kopis';
