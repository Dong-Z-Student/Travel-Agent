create extension if not exists postgis;
create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create table if not exists public.poi_categories (
  id uuid primary key default gen_random_uuid(),
  code text unique not null,
  name_zh text not null,
  name_en text,
  icon_url text,
  color text,
  default_visible boolean not null default true,
  sort_order int not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.pois (
  id uuid primary key default gen_random_uuid(),
  category_code text not null references public.poi_categories(code),
  name_zh text not null,
  name_en text,
  amap_poi_id text,
  amap_type text,
  amap_type_code text,
  address text,
  district text,
  city text not null default '武汉市',
  province text not null default '湖北省',
  longitude double precision not null,
  latitude double precision not null,
  geom geometry(Point, 4326) not null,
  amap_longitude double precision,
  amap_latitude double precision,
  rating numeric,
  popularity_score numeric,
  tags text[] not null default '{}'::text[],
  source text not null default 'amap',
  source_raw jsonb,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint pois_geom_srid check (st_srid(geom) = 4326)
);

create table if not exists public.scenic_spot_profiles (
  id uuid primary key default gen_random_uuid(),
  poi_id uuid unique not null references public.pois(id) on delete cascade,
  name_zh text not null,
  name_en text,
  short_intro_zh text,
  short_intro_en text,
  full_description_zh text,
  full_description_en text,
  recommended_duration_minutes int,
  opening_hours text,
  ticket_info text,
  suitable_time text,
  suitable_for text[] not null default '{}'::text[],
  manual_tags text[] not null default '{}'::text[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.poi_images (
  id uuid primary key default gen_random_uuid(),
  poi_id uuid not null references public.pois(id) on delete cascade,
  image_url text not null,
  storage_path text,
  image_type text not null default 'cover',
  caption_zh text,
  caption_en text,
  source text,
  copyright_note text,
  sort_order int not null default 0,
  created_at timestamptz not null default now()
);

create table if not exists public.import_jobs (
  id uuid primary key default gen_random_uuid(),
  job_type text not null,
  source text not null default 'amap',
  city text not null default '武汉市',
  status text not null default 'pending',
  started_at timestamptz,
  finished_at timestamptz,
  total_count int not null default 0,
  success_count int not null default 0,
  failed_count int not null default 0,
  error_log text,
  created_at timestamptz not null default now()
);

create table if not exists public.raw_amap_pois (
  id uuid primary key default gen_random_uuid(),
  import_job_id uuid references public.import_jobs(id) on delete set null,
  amap_poi_id text,
  keyword text,
  category_code text,
  city text not null default '武汉市',
  raw_json jsonb not null,
  fetched_at timestamptz not null default now()
);

create table if not exists public.user_profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  nickname text,
  avatar_url text,
  home_city text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_preferences (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.user_profiles(id) on delete cascade,
  preference_type text not null,
  preference_value text not null,
  confidence numeric not null default 1.0,
  source text not null default 'user_explicit',
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, preference_type, preference_value)
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.user_profiles(id) on delete set null,
  title text,
  city text not null default '武汉市',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  role text not null,
  content text,
  payload jsonb,
  created_at timestamptz not null default now()
);

create table if not exists public.trip_states (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid unique not null references public.conversations(id) on delete cascade,
  city text not null default '武汉市',
  days int,
  preferences jsonb not null default '[]'::jsonb,
  candidate_poi_ids jsonb not null default '[]'::jsonb,
  selected_poi_ids jsonb not null default '[]'::jsonb,
  selected_hotel_id uuid references public.pois(id) on delete set null,
  route_id uuid,
  state_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.user_draw_features (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references public.user_profiles(id) on delete set null,
  conversation_id uuid references public.conversations(id) on delete set null,
  query_type text not null,
  geom geometry(Geometry, 4326) not null,
  radius_meters numeric,
  buffer_meters numeric,
  properties jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  constraint user_draw_features_geom_srid check (st_srid(geom) = 4326)
);

create table if not exists public.spatial_poi_query_results (
  id uuid primary key default gen_random_uuid(),
  draw_feature_id uuid references public.user_draw_features(id) on delete cascade,
  poi_id uuid references public.pois(id) on delete cascade,
  distance_m numeric,
  relation_type text,
  created_at timestamptz not null default now(),
  unique (draw_feature_id, poi_id)
);

create table if not exists public.routes (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid references public.conversations(id) on delete set null,
  user_id uuid references public.user_profiles(id) on delete set null,
  route_name text,
  route_mode text,
  strategy text,
  geom geometry(LineString, 4326),
  distance_m numeric,
  duration_minutes numeric,
  amap_route_raw jsonb,
  route_json jsonb,
  created_at timestamptz not null default now(),
  constraint routes_geom_srid check (geom is null or st_srid(geom) = 4326)
);

create table if not exists public.route_stops (
  id uuid primary key default gen_random_uuid(),
  route_id uuid not null references public.routes(id) on delete cascade,
  poi_id uuid references public.pois(id) on delete set null,
  stop_order int not null,
  name text,
  longitude double precision,
  latitude double precision,
  arrival_time text,
  stay_minutes int,
  note text,
  created_at timestamptz not null default now()
);

create table if not exists public.population_heat_points (
  id uuid primary key default gen_random_uuid(),
  longitude double precision not null,
  latitude double precision not null,
  geom geometry(Point, 4326) not null,
  weight numeric not null,
  data_source text,
  data_time timestamptz,
  created_at timestamptz not null default now(),
  constraint population_heat_points_geom_srid check (st_srid(geom) = 4326)
);

insert into public.poi_categories (code, name_zh, name_en, color, sort_order)
values
  ('scenic_spot', '景点', 'Scenic Spot', '#e85d3f', 10),
  ('hotel', '酒店', 'Hotel', '#2f80ed', 20),
  ('metro_station', '地铁站', 'Metro Station', '#1b9e77', 30)
on conflict (code) do update
set
  name_zh = excluded.name_zh,
  name_en = excluded.name_en,
  color = excluded.color,
  sort_order = excluded.sort_order,
  updated_at = now();

create index if not exists idx_pois_geom on public.pois using gist (geom);
create index if not exists idx_pois_category_code on public.pois (category_code);
create index if not exists idx_pois_city on public.pois (city);
create index if not exists idx_pois_amap_poi_id on public.pois (amap_poi_id);
create index if not exists idx_pois_active_category on public.pois (is_active, category_code);
create index if not exists idx_scenic_spot_profiles_poi_id on public.scenic_spot_profiles (poi_id);
create index if not exists idx_poi_images_poi_id on public.poi_images (poi_id);
create index if not exists idx_raw_amap_pois_amap_poi_id on public.raw_amap_pois (amap_poi_id);
create index if not exists idx_raw_amap_pois_import_job_id on public.raw_amap_pois (import_job_id);
create index if not exists idx_user_preferences_user_id on public.user_preferences (user_id);
create index if not exists idx_conversations_user_id on public.conversations (user_id);
create index if not exists idx_messages_conversation_id on public.messages (conversation_id);
create index if not exists idx_trip_states_conversation_id on public.trip_states (conversation_id);
create index if not exists idx_user_draw_features_user_id on public.user_draw_features (user_id);
create index if not exists idx_user_draw_features_geom on public.user_draw_features using gist (geom);
create index if not exists idx_spatial_poi_query_results_draw_feature_id on public.spatial_poi_query_results (draw_feature_id);
create index if not exists idx_spatial_poi_query_results_poi_id on public.spatial_poi_query_results (poi_id);
create index if not exists idx_routes_user_id on public.routes (user_id);
create index if not exists idx_routes_conversation_id on public.routes (conversation_id);
create index if not exists idx_routes_geom on public.routes using gist (geom);
create index if not exists idx_route_stops_route_id on public.route_stops (route_id);
create index if not exists idx_population_heat_points_geom on public.population_heat_points using gist (geom);

create or replace trigger set_updated_at_poi_categories
before update on public.poi_categories
for each row execute function public.set_updated_at();

create or replace trigger set_updated_at_pois
before update on public.pois
for each row execute function public.set_updated_at();

create or replace trigger set_updated_at_scenic_spot_profiles
before update on public.scenic_spot_profiles
for each row execute function public.set_updated_at();

create or replace trigger set_updated_at_user_profiles
before update on public.user_profiles
for each row execute function public.set_updated_at();

create or replace trigger set_updated_at_user_preferences
before update on public.user_preferences
for each row execute function public.set_updated_at();

create or replace trigger set_updated_at_conversations
before update on public.conversations
for each row execute function public.set_updated_at();

create or replace trigger set_updated_at_trip_states
before update on public.trip_states
for each row execute function public.set_updated_at();

alter table public.poi_categories enable row level security;
alter table public.pois enable row level security;
alter table public.scenic_spot_profiles enable row level security;
alter table public.poi_images enable row level security;
alter table public.import_jobs enable row level security;
alter table public.raw_amap_pois enable row level security;
alter table public.user_profiles enable row level security;
alter table public.user_preferences enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.trip_states enable row level security;
alter table public.user_draw_features enable row level security;
alter table public.spatial_poi_query_results enable row level security;
alter table public.routes enable row level security;
alter table public.route_stops enable row level security;
alter table public.population_heat_points enable row level security;

grant usage on schema public to anon, authenticated;
grant select on public.poi_categories, public.pois, public.scenic_spot_profiles, public.poi_images, public.population_heat_points to anon, authenticated;
grant select, insert, update, delete on public.user_profiles, public.user_preferences, public.conversations, public.messages, public.trip_states, public.user_draw_features, public.spatial_poi_query_results, public.routes, public.route_stops to authenticated;

drop policy if exists "public read poi categories" on public.poi_categories;
create policy "public read poi categories" on public.poi_categories for select to anon, authenticated using (true);

drop policy if exists "public read pois" on public.pois;
create policy "public read pois" on public.pois for select to anon, authenticated using (is_active = true);

drop policy if exists "public read scenic profiles" on public.scenic_spot_profiles;
create policy "public read scenic profiles" on public.scenic_spot_profiles for select to anon, authenticated using (true);

drop policy if exists "public read poi images" on public.poi_images;
create policy "public read poi images" on public.poi_images for select to anon, authenticated using (true);

drop policy if exists "public read population heat points" on public.population_heat_points;
create policy "public read population heat points" on public.population_heat_points for select to anon, authenticated using (true);

drop policy if exists "users can read own profile" on public.user_profiles;
create policy "users can read own profile" on public.user_profiles for select to authenticated using ((select auth.uid()) = id);

drop policy if exists "users can insert own profile" on public.user_profiles;
create policy "users can insert own profile" on public.user_profiles for insert to authenticated with check ((select auth.uid()) = id);

drop policy if exists "users can update own profile" on public.user_profiles;
create policy "users can update own profile" on public.user_profiles for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

drop policy if exists "users can manage own preferences" on public.user_preferences;
create policy "users can manage own preferences" on public.user_preferences for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

drop policy if exists "users can manage own conversations" on public.conversations;
create policy "users can manage own conversations" on public.conversations for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

drop policy if exists "users can manage messages in own conversations" on public.messages;
create policy "users can manage messages in own conversations" on public.messages for all to authenticated
using (
  exists (
    select 1 from public.conversations c
    where c.id = messages.conversation_id and c.user_id = (select auth.uid())
  )
)
with check (
  exists (
    select 1 from public.conversations c
    where c.id = messages.conversation_id and c.user_id = (select auth.uid())
  )
);

drop policy if exists "users can manage trip states in own conversations" on public.trip_states;
create policy "users can manage trip states in own conversations" on public.trip_states for all to authenticated
using (
  exists (
    select 1 from public.conversations c
    where c.id = trip_states.conversation_id and c.user_id = (select auth.uid())
  )
)
with check (
  exists (
    select 1 from public.conversations c
    where c.id = trip_states.conversation_id and c.user_id = (select auth.uid())
  )
);

drop policy if exists "users can manage own draw features" on public.user_draw_features;
create policy "users can manage own draw features" on public.user_draw_features for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

drop policy if exists "users can manage own spatial query results" on public.spatial_poi_query_results;
create policy "users can manage own spatial query results" on public.spatial_poi_query_results for all to authenticated
using (
  exists (
    select 1 from public.user_draw_features f
    where f.id = spatial_poi_query_results.draw_feature_id and f.user_id = (select auth.uid())
  )
)
with check (
  exists (
    select 1 from public.user_draw_features f
    where f.id = spatial_poi_query_results.draw_feature_id and f.user_id = (select auth.uid())
  )
);

drop policy if exists "users can manage own routes" on public.routes;
create policy "users can manage own routes" on public.routes for all to authenticated using ((select auth.uid()) = user_id) with check ((select auth.uid()) = user_id);

drop policy if exists "users can manage stops in own routes" on public.route_stops;
create policy "users can manage stops in own routes" on public.route_stops for all to authenticated
using (
  exists (
    select 1 from public.routes r
    where r.id = route_stops.route_id and r.user_id = (select auth.uid())
  )
)
with check (
  exists (
    select 1 from public.routes r
    where r.id = route_stops.route_id and r.user_id = (select auth.uid())
  )
);

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values ('poi-images', 'poi-images', true, 5242880, array['image/jpeg', 'image/png', 'image/webp'])
on conflict (id) do update
set
  public = excluded.public,
  file_size_limit = excluded.file_size_limit,
  allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists "public read poi image objects" on storage.objects;
create policy "public read poi image objects" on storage.objects for select to anon, authenticated
using (bucket_id = 'poi-images');
