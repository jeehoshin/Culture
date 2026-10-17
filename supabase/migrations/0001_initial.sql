create extension if not exists pgcrypto;
create extension if not exists pg_trgm;

create type public.event_category as enum ('exhibition', 'play', 'musical');
create type public.price_type as enum ('free', 'paid', 'unknown');
create type public.source_kind as enum ('culture_portal', 'kopis', 'seoul');
create type public.sync_status as enum ('running', 'succeeded', 'partial', 'failed');
create type public.duplicate_status as enum ('pending', 'merged', 'rejected');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.venues (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  normalized_name text not null,
  address text,
  district text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  normalized_title text not null,
  category public.event_category not null,
  venue_id uuid references public.venues(id) on delete set null,
  start_date date not null,
  end_date date not null,
  price_kind public.price_type not null default 'unknown',
  min_price integer check (min_price is null or min_price >= 0),
  max_price integer check (max_price is null or max_price >= min_price),
  price_text text,
  description text,
  booking_url text,
  image_url text,
  is_active boolean not null default true,
  first_seen_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (end_date >= start_date)
);

create table public.raw_events (
  id bigint generated always as identity primary key,
  source public.source_kind not null,
  external_id text not null,
  payload jsonb not null,
  payload_hash text not null,
  fetched_at timestamptz not null default now(),
  unique (source, external_id, payload_hash)
);

create table public.event_sources (
  id uuid primary key default gen_random_uuid(),
  event_id uuid not null references public.events(id) on delete cascade,
  raw_event_id bigint not null references public.raw_events(id) on delete restrict,
  source public.source_kind not null,
  external_id text not null,
  source_url text,
  api_documentation_url text,
  attribution text not null,
  license_note text,
  license_checked_at timestamptz,
  is_primary boolean not null default false,
  created_at timestamptz not null default now(),
  unique (source, external_id),
  unique (event_id, raw_event_id)
);

create table public.duplicate_candidates (
  id uuid primary key default gen_random_uuid(),
  left_event_id uuid not null references public.events(id) on delete cascade,
  right_event_id uuid not null references public.events(id) on delete cascade,
  score numeric(5,4) not null check (score between 0 and 1),
  reasons jsonb not null default '{}'::jsonb,
  status public.duplicate_status not null default 'pending',
  reviewed_by uuid references auth.users(id) on delete set null,
  reviewed_at timestamptz,
  created_at timestamptz not null default now(),
  check (left_event_id <> right_event_id),
  unique (left_event_id, right_event_id)
);

create table public.favorites (
  user_id uuid not null references auth.users(id) on delete cascade,
  event_id uuid not null references public.events(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, event_id)
);

create table public.attendance (
  user_id uuid not null references auth.users(id) on delete cascade,
  event_id uuid not null references public.events(id) on delete cascade,
  attended_on date,
  rating smallint check (rating between 1 and 5),
  note text check (char_length(note) <= 2000),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (user_id, event_id)
);

create table public.sync_runs (
  id uuid primary key default gen_random_uuid(),
  source public.source_kind not null,
  status public.sync_status not null default 'running',
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  fetched_count integer not null default 0,
  inserted_count integer not null default 0,
  updated_count integer not null default 0,
  error_count integer not null default 0,
  cursor jsonb,
  errors jsonb not null default '[]'::jsonb
);

create index events_active_dates_idx on public.events (is_active, end_date, start_date);
create index events_category_dates_idx on public.events (category, end_date);
create index events_title_trgm_idx on public.events using gin (normalized_title gin_trgm_ops);
create index venues_name_trgm_idx on public.venues using gin (normalized_name gin_trgm_ops);
create index venues_district_idx on public.venues (district);
create index raw_events_lookup_idx on public.raw_events (source, external_id, fetched_at desc);

alter table public.profiles enable row level security;
alter table public.venues enable row level security;
alter table public.events enable row level security;
alter table public.raw_events enable row level security;
alter table public.event_sources enable row level security;
alter table public.duplicate_candidates enable row level security;
alter table public.favorites enable row level security;
alter table public.attendance enable row level security;
alter table public.sync_runs enable row level security;

create policy "public venues are readable" on public.venues for select using (true);
create policy "public active events are readable" on public.events for select using (is_active);
create policy "public event sources are readable" on public.event_sources for select using (true);
create policy "users read own profile" on public.profiles for select using (auth.uid() = id);
create policy "users update own profile" on public.profiles for update using (auth.uid() = id) with check (auth.uid() = id);
create policy "users read own favorites" on public.favorites for select using (auth.uid() = user_id);
create policy "users insert own favorites" on public.favorites for insert with check (auth.uid() = user_id);
create policy "users delete own favorites" on public.favorites for delete using (auth.uid() = user_id);
create policy "users read own attendance" on public.attendance for select using (auth.uid() = user_id);
create policy "users insert own attendance" on public.attendance for insert with check (auth.uid() = user_id);
create policy "users update own attendance" on public.attendance for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "users delete own attendance" on public.attendance for delete using (auth.uid() = user_id);

revoke all on public.raw_events, public.sync_runs, public.duplicate_candidates from anon, authenticated;
grant select on public.events, public.venues, public.event_sources to anon, authenticated;
grant select, insert, delete on public.favorites to authenticated;
grant select, insert, update, delete on public.attendance to authenticated;
grant select, update on public.profiles to authenticated;

create function public.handle_new_user() returns trigger language plpgsql security definer set search_path = '' as $$
begin
  insert into public.profiles (id, display_name) values (new.id, new.raw_user_meta_data ->> 'display_name');
  return new;
end;
$$;

create trigger on_auth_user_created after insert on auth.users for each row execute procedure public.handle_new_user();

