create or replace function public.ingest_event_batch(p_rows jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  r jsonb;
  v_source public.source_kind;
  v_raw_event_id bigint;
  v_venue_id uuid;
  v_event_id uuid;
  v_existing_event_id uuid;
  v_candidate record;
  v_inserted integer := 0;
  v_updated integer := 0;
begin
  if jsonb_typeof(p_rows) <> 'array' then
    raise exception 'p_rows must be a JSON array';
  end if;

  for r in select value from jsonb_array_elements(p_rows)
  loop
    v_source := (r ->> 'source')::public.source_kind;

    insert into public.raw_events (source, external_id, payload, payload_hash)
    values (v_source, r ->> 'external_id', r -> 'payload', r ->> 'payload_hash')
    on conflict (source, external_id, payload_hash) do nothing;

    select id into v_raw_event_id
    from public.raw_events
    where source = v_source
      and external_id = r ->> 'external_id'
      and payload_hash = r ->> 'payload_hash'
    order by fetched_at desc
    limit 1;

    select id into v_venue_id
    from public.venues
    where normalized_name = r ->> 'normalized_venue_name'
      and coalesce(address, '') = coalesce(r ->> 'address', '')
    order by created_at
    limit 1;

    if v_venue_id is null then
      insert into public.venues (name, normalized_name, address, district)
      values (
        r ->> 'venue_name',
        r ->> 'normalized_venue_name',
        nullif(r ->> 'address', ''),
        nullif(r ->> 'district', '')
      )
      returning id into v_venue_id;
    else
      update public.venues
      set name = r ->> 'venue_name',
          district = coalesce(nullif(r ->> 'district', ''), district),
          updated_at = now()
      where id = v_venue_id;
    end if;

    select event_id into v_existing_event_id
    from public.event_sources
    where source = v_source and external_id = r ->> 'external_id';

    if v_existing_event_id is null then
      select id into v_existing_event_id
      from public.events
      where normalized_title = r ->> 'normalized_title'
        and category = (r ->> 'category')::public.event_category
        and start_date = (r ->> 'start_date')::date
        and end_date = (r ->> 'end_date')::date
        and venue_id = v_venue_id
      order by created_at
      limit 1;
    end if;

    if v_existing_event_id is null then
      insert into public.events (
        title, normalized_title, category, venue_id, start_date, end_date,
        price_kind, min_price, max_price, price_text, description, booking_url
      )
      values (
        r ->> 'title',
        r ->> 'normalized_title',
        (r ->> 'category')::public.event_category,
        v_venue_id,
        (r ->> 'start_date')::date,
        (r ->> 'end_date')::date,
        (r ->> 'price_kind')::public.price_type,
        nullif(r ->> 'min_price', '')::integer,
        nullif(r ->> 'max_price', '')::integer,
        nullif(r ->> 'price_text', ''),
        nullif(r ->> 'description', ''),
        nullif(r ->> 'booking_url', '')
      )
      returning id into v_event_id;
      v_inserted := v_inserted + 1;

      for v_candidate in
        select e.id,
          greatest(
            similarity(e.normalized_title, r ->> 'normalized_title'),
            similarity(v.normalized_name, r ->> 'normalized_venue_name')
          ) as score
        from public.events e
        left join public.venues v on v.id = e.venue_id
        where e.id <> v_event_id
          and e.category = (r ->> 'category')::public.event_category
          and e.start_date = (r ->> 'start_date')::date
          and e.end_date = (r ->> 'end_date')::date
          and similarity(e.normalized_title, r ->> 'normalized_title') >= 0.72
        order by score desc
        limit 5
      loop
        insert into public.duplicate_candidates (
          left_event_id, right_event_id, score, reasons
        )
        values (
          case when v_candidate.id::text < v_event_id::text then v_candidate.id else v_event_id end,
          case when v_candidate.id::text < v_event_id::text then v_event_id else v_candidate.id end,
          v_candidate.score,
          jsonb_build_object('same_dates', true, 'normalized_title_similarity', v_candidate.score)
        )
        on conflict (left_event_id, right_event_id) do update
        set score = excluded.score, reasons = excluded.reasons;
      end loop;
    else
      v_event_id := v_existing_event_id;
      update public.events
      set title = r ->> 'title',
          normalized_title = r ->> 'normalized_title',
          venue_id = v_venue_id,
          start_date = (r ->> 'start_date')::date,
          end_date = (r ->> 'end_date')::date,
          price_kind = case
            when (r ->> 'price_kind')::public.price_type <> 'unknown'
              then (r ->> 'price_kind')::public.price_type
            else price_kind
          end,
          min_price = coalesce(nullif(r ->> 'min_price', '')::integer, min_price),
          max_price = coalesce(nullif(r ->> 'max_price', '')::integer, max_price),
          price_text = coalesce(nullif(r ->> 'price_text', ''), price_text),
          description = coalesce(description, nullif(r ->> 'description', '')),
          booking_url = coalesce(booking_url, nullif(r ->> 'booking_url', '')),
          is_active = true,
          last_seen_at = now(),
          updated_at = now()
      where id = v_event_id;
      v_updated := v_updated + 1;
    end if;

    insert into public.event_sources (
      event_id, raw_event_id, source, external_id, source_url,
      api_documentation_url, attribution, license_note, license_checked_at, is_primary
    )
    values (
      v_event_id,
      v_raw_event_id,
      v_source,
      r ->> 'external_id',
      nullif(r ->> 'source_url', ''),
      nullif(r ->> 'api_documentation_url', ''),
      r ->> 'attribution',
      nullif(r ->> 'license_note', ''),
      current_date,
      not exists (select 1 from public.event_sources where event_id = v_event_id)
    )
    on conflict (source, external_id) do update
    set raw_event_id = excluded.raw_event_id,
        source_url = excluded.source_url,
        api_documentation_url = excluded.api_documentation_url,
        attribution = excluded.attribution,
        license_note = excluded.license_note,
        license_checked_at = excluded.license_checked_at;

    v_raw_event_id := null;
    v_venue_id := null;
    v_event_id := null;
    v_existing_event_id := null;
  end loop;

  return jsonb_build_object(
    'inserted_count', v_inserted,
    'updated_count', v_updated
  );
end;
$$;

revoke all on function public.ingest_event_batch(jsonb) from public, anon, authenticated;
grant execute on function public.ingest_event_batch(jsonb) to service_role;
