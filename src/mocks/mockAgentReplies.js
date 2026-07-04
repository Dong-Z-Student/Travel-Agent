const chooseReply = message => {
  const text = message || ''
  if (text.includes('东湖') || text.includes('湖')) {
    return '可以，我建议把东湖作为核心游览区，搭配湖北省博物馆和楚河汉街，行程会比较顺。'
  }
  if (text.includes('地铁') || text.includes('交通')) {
    return '我会优先选择靠近地铁站的景点和酒店，减少换乘和步行压力。'
  }
  if (text.includes('两天') || text.includes('2天')) {
    return '两天行程可以按“武昌文化线 + 汉口江滩城市线”组织，第一天偏景点，第二天偏休闲。'
  }
  if (text.includes('酒店')) {
    return '酒店建议优先看楚河汉街、江汉路、光谷或汉口江滩附近，方便夜间活动和地铁出行。'
  }
  return '我已经收到你的需求。第一版会先基于武汉景点、酒店和地铁站的 Mock 数据给出规划建议。'
}

export const createMockAgentReply = payload => {
  const message = payload?.message || ''
  return {
    conversation_id: payload?.conversation_id || 'conv_mock_wuhan',
    reply: chooseReply(message),
    trip_state: {
      city: '武汉市',
      days: message.includes('三天') || message.includes('3天') ? 3 : 2,
      preferences: payload?.preferences || ['轻松', '地铁优先'],
      candidate_poi_ids: payload?.context?.poi_ids || ['poi_scenic_001', 'poi_scenic_002']
    },
    cards: [
      { id: 'card_mock_route', type: 'trip_hint', title: '武汉轻量规划建议', summary: '围绕景点、酒店和地铁站生成第一版 Mock 行程。' }
    ],
    map_commands: [
      { type: 'ADD_ROUTE', payload: { route_id: 'route_wuhan_2day_easy' } },
      { type: 'PLAY_ROUTE_ANIMATION', payload: { route_id: 'route_wuhan_2day_easy' } }
    ]
  }
}
