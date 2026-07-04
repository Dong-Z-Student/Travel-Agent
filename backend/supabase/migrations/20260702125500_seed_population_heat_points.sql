insert into public.population_heat_points (longitude, latitude, geom, weight, data_source)
values
  (114.286, 30.581, ST_SetSRID(ST_MakePoint(114.286, 30.581), 4326), 0.92, 'stage1_seed'),
  (114.333, 30.546, ST_SetSRID(ST_MakePoint(114.333, 30.546), 4326), 0.85, 'stage1_seed'),
  (114.405, 30.506, ST_SetSRID(ST_MakePoint(114.405, 30.506), 4326), 0.80, 'stage1_seed'),
  (114.255, 30.617, ST_SetSRID(ST_MakePoint(114.255, 30.617), 4326), 0.76, 'stage1_seed'),
  (114.317, 30.529, ST_SetSRID(ST_MakePoint(114.317, 30.529), 4326), 0.73, 'stage1_seed'),
  (114.340, 30.558, ST_SetSRID(ST_MakePoint(114.340, 30.558), 4326), 0.70, 'stage1_seed'),
  (114.392, 30.562, ST_SetSRID(ST_MakePoint(114.392, 30.562), 4326), 0.66, 'stage1_seed'),
  (114.270, 30.552, ST_SetSRID(ST_MakePoint(114.270, 30.552), 4326), 0.58, 'stage1_seed'),
  (114.365, 30.536, ST_SetSRID(ST_MakePoint(114.365, 30.536), 4326), 0.62, 'stage1_seed'),
  (114.306, 30.590, ST_SetSRID(ST_MakePoint(114.306, 30.590), 4326), 0.68, 'stage1_seed'),
  (114.302, 30.623, ST_SetSRID(ST_MakePoint(114.302, 30.623), 4326), 0.52, 'stage1_seed'),
  (114.410, 30.515, ST_SetSRID(ST_MakePoint(114.410, 30.515), 4326), 0.74, 'stage1_seed'),
  (114.220, 30.580, ST_SetSRID(ST_MakePoint(114.220, 30.580), 4326), 0.50, 'stage1_seed'),
  (114.180, 30.610, ST_SetSRID(ST_MakePoint(114.180, 30.610), 4326), 0.48, 'stage1_seed'),
  (114.450, 30.475, ST_SetSRID(ST_MakePoint(114.450, 30.475), 4326), 0.46, 'stage1_seed')
on conflict do nothing;
