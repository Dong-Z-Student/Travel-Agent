export const mockRoutes = [
  {
    route_id: 'route_wuhan_2day_easy',
    route_name: '武汉两日轻松游',
    geometry: {
      type: 'LineString',
      coordinates: [
        [114.286, 30.581],
        [114.302, 30.590],
        [114.333, 30.546],
        [114.367, 30.561],
        [114.400, 30.565],
        [114.356, 30.532],
        [114.306, 30.546]
      ]
    },
    stops: [
      { id: 'stop_001', name: '江汉路', longitude: 114.286, latitude: 30.581 },
      { id: 'stop_002', name: '汉口江滩', longitude: 114.302, latitude: 30.590 },
      { id: 'stop_003', name: '洪山广场', longitude: 114.333, latitude: 30.546 },
      { id: 'stop_004', name: '湖北省博物馆', longitude: 114.367, latitude: 30.561 },
      { id: 'stop_005', name: '东湖风景区', longitude: 114.400, latitude: 30.565 },
      { id: 'stop_006', name: '武汉大学', longitude: 114.356, latitude: 30.532 },
      { id: 'stop_007', name: '黄鹤楼', longitude: 114.306, latitude: 30.546 }
    ],
    animation: {
      speed: 0.006,
      loop: true
    }
  }
]

export const getMockRoute = routeId => mockRoutes.find(route => route.route_id === routeId) || mockRoutes[0]
