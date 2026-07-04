create table if not exists public.district_adcodes (
  id uuid primary key default gen_random_uuid(),
  city text not null default '武汉市',
  district text not null,
  adcode text not null,
  amap_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (city, district)
);

create table if not exists public.weather_cache (
  id uuid primary key default gen_random_uuid(),
  city text not null default '武汉市',
  district text,
  adcode text not null,
  extensions text not null,
  forecast_date date,
  response_json jsonb not null,
  normalized_json jsonb not null,
  report_time timestamptz,
  expire_at timestamptz not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint weather_cache_extensions_check check (extensions in ('base', 'all'))
);

create index if not exists idx_district_adcodes_adcode on public.district_adcodes(adcode);
create index if not exists idx_weather_cache_adcode on public.weather_cache(adcode);
create index if not exists idx_weather_cache_expire_at on public.weather_cache(expire_at);
create index if not exists idx_weather_cache_forecast_date on public.weather_cache(forecast_date);
create index if not exists idx_weather_cache_lookup
  on public.weather_cache(adcode, extensions, forecast_date, expire_at desc);

create or replace trigger set_updated_at_district_adcodes
before update on public.district_adcodes
for each row execute function public.set_updated_at();

create or replace trigger set_updated_at_weather_cache
before update on public.weather_cache
for each row execute function public.set_updated_at();

alter table public.district_adcodes enable row level security;
alter table public.weather_cache enable row level security;

do $$
begin
  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'district_adcodes'
      and policyname = 'district_adcodes_select_public'
  ) then
    create policy district_adcodes_select_public
    on public.district_adcodes
    for select
    to anon, authenticated
    using (true);
  end if;

  if not exists (
    select 1 from pg_policies
    where schemaname = 'public'
      and tablename = 'weather_cache'
      and policyname = 'weather_cache_select_public'
  ) then
    create policy weather_cache_select_public
    on public.weather_cache
    for select
    to anon, authenticated
    using (true);
  end if;
end
$$;

insert into public.district_adcodes (city, district, adcode, amap_name)
values
  ('武汉市', '江岸区', '420102', '江岸区'),
  ('武汉市', '江汉区', '420103', '江汉区'),
  ('武汉市', '硚口区', '420104', '硚口区'),
  ('武汉市', '汉阳区', '420105', '汉阳区'),
  ('武汉市', '武昌区', '420106', '武昌区'),
  ('武汉市', '洪山区', '420111', '洪山区'),
  ('武汉市', '东西湖区', '420112', '东西湖区'),
  ('武汉市', '汉南区', '420113', '汉南区'),
  ('武汉市', '蔡甸区', '420114', '蔡甸区'),
  ('武汉市', '江夏区', '420115', '江夏区'),
  ('武汉市', '黄陂区', '420116', '黄陂区'),
  ('武汉市', '新洲区', '420117', '新洲区')
on conflict (city, district)
do update set
  adcode = excluded.adcode,
  amap_name = excluded.amap_name,
  updated_at = now();
