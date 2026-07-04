const image = id => `https://picsum.photos/seed/wuhan-${id}/420/240`

export const mockPoiDetails = {
  poi_001: {
    id: 'poi_001', category_code: 'scenic_spot', name_zh: '黄鹤楼', name_en: 'Yellow Crane Tower', longitude: 114.306, latitude: 30.546, address: '武汉市武昌区蛇山西山坡特1号',
    profile: { short_intro_zh: '黄鹤楼是武汉最具代表性的历史文化地标之一，适合安排在城市经典线路中。', full_description_zh: '黄鹤楼位于武昌蛇山，是武汉城市意象中最醒目的文化符号之一。', recommended_duration_minutes: 90, opening_hours: '08:30-18:00', ticket_info: '以景区实际公告为准' },
    images: [{ image_url: image('yellow-crane'), caption_zh: '黄鹤楼占位图' }]
  },
  poi_002: {
    id: 'poi_002', category_code: 'scenic_spot', name_zh: '东湖风景区', name_en: 'East Lake Scenic Area', longitude: 114.400, latitude: 30.565, address: '武汉市武昌区沿湖大道16号',
    profile: { short_intro_zh: '东湖适合骑行、散步和轻松游览，是武汉自然风景体验的核心区域。', full_description_zh: '东湖水域开阔，绿道完善，适合半日到一日的城市休闲游。', recommended_duration_minutes: 180, opening_hours: '全天开放', ticket_info: '部分园区或项目另行收费' },
    images: [{ image_url: image('east-lake'), caption_zh: '东湖占位图' }]
  },
  poi_003: {
    id: 'poi_003', category_code: 'scenic_spot', name_zh: '湖北省博物馆', name_en: 'Hubei Provincial Museum', longitude: 114.367, latitude: 30.561, address: '武汉市武昌区东湖路160号',
    profile: { short_intro_zh: '湖北省博物馆以曾侯乙编钟等馆藏闻名，适合文化主题行程。', full_description_zh: '馆内展示楚文化与湖北历史，是理解武汉与荆楚文化的重要窗口。', recommended_duration_minutes: 150, opening_hours: '09:00-17:00，周一闭馆', ticket_info: '通常需预约，以官方公告为准' },
    images: [{ image_url: image('hubei-museum'), caption_zh: '湖北省博物馆占位图' }]
  },
  poi_004: {
    id: 'poi_004', category_code: 'scenic_spot', name_zh: '武汉大学', name_en: 'Wuhan University', longitude: 114.365, latitude: 30.536, address: '武汉市武昌区八一路299号',
    profile: { short_intro_zh: '武汉大学以校园风景和历史建筑著称，樱花季尤其热门。', full_description_zh: '珞珈山下的校园空间兼具自然景观与人文气质。', recommended_duration_minutes: 90, opening_hours: '以学校开放管理为准', ticket_info: '校园参观政策以官方公告为准' },
    images: [{ image_url: image('wuhan-university'), caption_zh: '武汉大学占位图' }]
  },
  poi_005: {
    id: 'poi_005', category_code: 'scenic_spot', name_zh: '古德寺', name_en: 'Gude Temple', longitude: 114.306, latitude: 30.623, address: '武汉市江岸区工农兵路24号',
    profile: { short_intro_zh: '古德寺建筑风格独特，是汉口片区适合拍照和慢游的景点。', full_description_zh: '寺院建筑融合多种风格，空间尺度不大但辨识度很高。', recommended_duration_minutes: 60, opening_hours: '以景区实际公告为准', ticket_info: '以现场公告为准' },
    images: [{ image_url: image('gude-temple'), caption_zh: '古德寺占位图' }]
  },
  poi_006: {
    id: 'poi_006', category_code: 'scenic_spot', name_zh: '江汉路步行街', name_en: 'Jianghan Road Pedestrian Street', longitude: 114.285, latitude: 30.584, address: '武汉市江汉区江汉路',
    profile: { short_intro_zh: '江汉路适合购物、夜游和串联汉口历史建筑街区。', full_description_zh: '这里商业氛围浓厚，周边交通便利，适合作为晚间行程。', recommended_duration_minutes: 120, opening_hours: '全天开放', ticket_info: '免费' },
    images: [{ image_url: image('jianghan-road'), caption_zh: '江汉路占位图' }]
  },
  poi_007: {
    id: 'poi_007', category_code: 'scenic_spot', name_zh: '汉口江滩', name_en: 'Hankou River Beach', longitude: 114.302, latitude: 30.590, address: '武汉市江岸区沿江大道',
    profile: { short_intro_zh: '汉口江滩适合看江景、散步和夜间轻松活动。', full_description_zh: '江滩空间开阔，能很好地感受长江与汉口城市界面。', recommended_duration_minutes: 90, opening_hours: '全天开放', ticket_info: '免费' },
    images: [{ image_url: image('hankou-river'), caption_zh: '汉口江滩占位图' }]
  },
  poi_008: {
    id: 'poi_008', category_code: 'scenic_spot', name_zh: '归元寺', name_en: 'Guiyuan Temple', longitude: 114.258, latitude: 30.548, address: '武汉市汉阳区归元寺路20号',
    profile: { short_intro_zh: '归元寺是汉阳代表性寺院，适合与晴川阁、龟山一带串联。', full_description_zh: '寺院历史悠久，周边汉阳生活气息浓厚。', recommended_duration_minutes: 75, opening_hours: '以景区实际公告为准', ticket_info: '以现场公告为准' },
    images: [{ image_url: image('guiyuan-temple'), caption_zh: '归元寺占位图' }]
  },
  poi_009: {
    id: 'poi_009', category_code: 'scenic_spot', name_zh: '昙华林', name_en: 'Tanhualin', longitude: 114.312, latitude: 30.555, address: '武汉市武昌区昙华林',
    profile: { short_intro_zh: '昙华林是武昌老城里适合步行和拍照的文艺街区。', full_description_zh: '街区尺度轻松，适合和黄鹤楼、粮道街等点位串联。', recommended_duration_minutes: 90, opening_hours: '全天开放', ticket_info: '免费' },
    images: [{ image_url: image('tanhualin'), caption_zh: '昙华林占位图' }]
  },
  poi_010: {
    id: 'poi_010', category_code: 'scenic_spot', name_zh: '木兰天池', name_en: 'Mulan Heavenly Lake', longitude: 114.381, latitude: 31.125, address: '武汉市黄陂区长轩岭街道',
    profile: { short_intro_zh: '木兰天池位于黄陂，适合安排为郊野一日游。', full_description_zh: '景区距离中心城区较远，更适合自驾或专门安排一天。', recommended_duration_minutes: 240, opening_hours: '以景区实际公告为准', ticket_info: '以景区实际公告为准' },
    images: [{ image_url: image('mulan-lake'), caption_zh: '木兰天池占位图' }]
  }
}
