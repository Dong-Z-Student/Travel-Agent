export const POI_CATEGORIES = {
  scenic_spot: { label: '景点', layerId: 'poi_scenic', group: 'poi_scenic' },
  hotel: { label: '酒店', layerId: 'poi_hotel', group: 'poi_hotel' },
  metro_station: { label: '地铁站', layerId: 'poi_metro', group: 'poi_metro' }
}

export const mockPois = [
  { id: 'poi_001', category_code: 'scenic_spot', name_zh: '黄鹤楼', name_en: 'Yellow Crane Tower', longitude: 114.306, latitude: 30.546, address: '武汉市武昌区蛇山西山坡特1号', tags: ['历史文化', '城市地标'], popularity_score: 0.95 },
  { id: 'poi_002', category_code: 'scenic_spot', name_zh: '东湖风景区', name_en: 'East Lake Scenic Area', longitude: 114.400, latitude: 30.565, address: '武汉市武昌区沿湖大道16号', tags: ['湖泊', '骑行'], popularity_score: 0.93 },
  { id: 'poi_003', category_code: 'scenic_spot', name_zh: '湖北省博物馆', name_en: 'Hubei Provincial Museum', longitude: 114.367, latitude: 30.561, address: '武汉市武昌区东湖路160号', tags: ['博物馆', '编钟'], popularity_score: 0.91 },
  { id: 'poi_004', category_code: 'scenic_spot', name_zh: '武汉大学', name_en: 'Wuhan University', longitude: 114.365, latitude: 30.536, address: '武汉市武昌区八一路299号', tags: ['校园', '樱花'], popularity_score: 0.88 },
  { id: 'poi_005', category_code: 'scenic_spot', name_zh: '古德寺', name_en: 'Gude Temple', longitude: 114.306, latitude: 30.623, address: '武汉市江岸区工农兵路24号', tags: ['建筑', '寺庙'], popularity_score: 0.82 },
  { id: 'poi_006', category_code: 'scenic_spot', name_zh: '江汉路步行街', name_en: 'Jianghan Road Pedestrian Street', longitude: 114.285, latitude: 30.584, address: '武汉市江汉区江汉路', tags: ['商业', '夜游'], popularity_score: 0.87 },
  { id: 'poi_007', category_code: 'scenic_spot', name_zh: '汉口江滩', name_en: 'Hankou River Beach', longitude: 114.302, latitude: 30.590, address: '武汉市江岸区沿江大道', tags: ['江景', '散步'], popularity_score: 0.84 },
  { id: 'poi_008', category_code: 'scenic_spot', name_zh: '归元寺', name_en: 'Guiyuan Temple', longitude: 114.258, latitude: 30.548, address: '武汉市汉阳区归元寺路20号', tags: ['寺庙', '文化'], popularity_score: 0.80 },
  { id: 'poi_009', category_code: 'scenic_spot', name_zh: '昙华林', name_en: 'Tanhualin', longitude: 114.312, latitude: 30.555, address: '武汉市武昌区昙华林', tags: ['街区', '文艺'], popularity_score: 0.79 },
  { id: 'poi_010', category_code: 'scenic_spot', name_zh: '木兰天池', name_en: 'Mulan Heavenly Lake', longitude: 114.381, latitude: 31.125, address: '武汉市黄陂区长轩岭街道', tags: ['山水', '郊游'], popularity_score: 0.76 },

  { id: 'hotel_001', category_code: 'hotel', name_zh: '武汉江滩城市酒店', name_en: 'Wuhan Riverfront Hotel', longitude: 114.296, latitude: 30.595, address: '武汉市江岸区沿江大道88号', tags: ['江景', '汉口'], popularity_score: 0.78 },
  { id: 'hotel_002', category_code: 'hotel', name_zh: '武昌黄鹤楼雅居酒店', name_en: 'Yellow Crane Boutique Hotel', longitude: 114.309, latitude: 30.542, address: '武汉市武昌区民主路128号', tags: ['武昌', '景区周边'], popularity_score: 0.74 },
  { id: 'hotel_003', category_code: 'hotel', name_zh: '东湖湖畔酒店', name_en: 'East Lake Lakeside Hotel', longitude: 114.392, latitude: 30.562, address: '武汉市武昌区东湖路188号', tags: ['东湖', '安静'], popularity_score: 0.81 },
  { id: 'hotel_004', category_code: 'hotel', name_zh: '光谷未来酒店', name_en: 'Optics Valley Future Hotel', longitude: 114.410, latitude: 30.507, address: '武汉市洪山区珞喻路726号', tags: ['光谷', '商务'], popularity_score: 0.72 },
  { id: 'hotel_005', category_code: 'hotel', name_zh: '汉阳晴川酒店', name_en: 'Hanyang Qingchuan Hotel', longitude: 114.270, latitude: 30.552, address: '武汉市汉阳区晴川大道56号', tags: ['汉阳', '江景'], popularity_score: 0.70 },
  { id: 'hotel_006', category_code: 'hotel', name_zh: '江汉路轻居酒店', name_en: 'Jianghan Road Light Hotel', longitude: 114.286, latitude: 30.581, address: '武汉市江汉区中山大道818号', tags: ['步行街', '地铁'], popularity_score: 0.83 },
  { id: 'hotel_007', category_code: 'hotel', name_zh: '汉口站旅居酒店', name_en: 'Hankou Station Stay Hotel', longitude: 114.255, latitude: 30.618, address: '武汉市江汉区发展大道185号', tags: ['火车站', '交通'], popularity_score: 0.68 },
  { id: 'hotel_008', category_code: 'hotel', name_zh: '楚河汉街精选酒店', name_en: 'Han Street Select Hotel', longitude: 114.341, latitude: 30.558, address: '武汉市武昌区楚河汉街', tags: ['购物', '夜游'], popularity_score: 0.77 },
  { id: 'hotel_009', category_code: 'hotel', name_zh: '武汉大学樱园酒店', name_en: 'Wuhan University Sakura Hotel', longitude: 114.356, latitude: 30.532, address: '武汉市武昌区珞珈山路', tags: ['校园', '安静'], popularity_score: 0.73 },

  { id: 'metro_001', category_code: 'metro_station', name_zh: '洪山广场站', name_en: 'Hongshan Square Station', longitude: 114.333, latitude: 30.546, address: '武汉市武昌区洪山广场', tags: ['2号线', '4号线'], popularity_score: 0.84 },
  { id: 'metro_002', category_code: 'metro_station', name_zh: '江汉路站', name_en: 'Jianghan Road Station', longitude: 114.286, latitude: 30.581, address: '武汉市江汉区江汉路', tags: ['2号线', '6号线'], popularity_score: 0.87 },
  { id: 'metro_003', category_code: 'metro_station', name_zh: '光谷广场站', name_en: 'Optics Valley Square Station', longitude: 114.405, latitude: 30.506, address: '武汉市洪山区光谷广场', tags: ['2号线'], popularity_score: 0.82 },
  { id: 'metro_004', category_code: 'metro_station', name_zh: '武昌火车站', name_en: 'Wuchang Railway Station', longitude: 114.317, latitude: 30.529, address: '武汉市武昌区中山路', tags: ['4号线', '7号线'], popularity_score: 0.80 },
  { id: 'metro_005', category_code: 'metro_station', name_zh: '汉口火车站', name_en: 'Hankou Railway Station', longitude: 114.255, latitude: 30.617, address: '武汉市江汉区发展大道', tags: ['2号线'], popularity_score: 0.79 },
  { id: 'metro_006', category_code: 'metro_station', name_zh: '楚河汉街站', name_en: 'Chuhe Hanjie Station', longitude: 114.340, latitude: 30.558, address: '武汉市武昌区楚河汉街', tags: ['4号线'], popularity_score: 0.76 },
  { id: 'metro_007', category_code: 'metro_station', name_zh: '黄鹤楼站', name_en: 'Yellow Crane Tower Station', longitude: 114.306, latitude: 30.545, address: '武汉市武昌区解放路', tags: ['5号线'], popularity_score: 0.74 },
  { id: 'metro_008', category_code: 'metro_station', name_zh: '钟家村站', name_en: 'Zhongjiacun Station', longitude: 114.265, latitude: 30.549, address: '武汉市汉阳区钟家村', tags: ['4号线', '6号线'], popularity_score: 0.71 },
  { id: 'metro_009', category_code: 'metro_station', name_zh: '街道口站', name_en: 'Jiedaokou Station', longitude: 114.353, latitude: 30.526, address: '武汉市洪山区珞喻路', tags: ['2号线', '8号线'], popularity_score: 0.75 }
]
