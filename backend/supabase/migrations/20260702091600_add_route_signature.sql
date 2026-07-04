alter table public.routes
add column if not exists route_signature text;

create index if not exists idx_routes_route_signature
on public.routes (route_signature);
