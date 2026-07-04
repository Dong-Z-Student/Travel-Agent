import { mockPois } from './mockPois'

const queryLabels = {
  point_radius: '点附近查询',
  line_buffer: '线附近查询',
  bezier_buffer: '贝塞尔曲线附近查询',
  polygon_contains: '面内查询'
}

const pickPois = queryType => {
  if (queryType === 'point_radius') return mockPois.slice(0, 6)
  if (queryType === 'line_buffer') return mockPois.filter(poi => ['scenic_spot', 'metro_station'].includes(poi.category_code)).slice(0, 8)
  if (queryType === 'bezier_buffer') return mockPois.filter(poi => ['scenic_spot', 'hotel'].includes(poi.category_code)).slice(1, 9)
  if (queryType === 'polygon_contains') return mockPois.slice(3, 12)
  return mockPois.slice(0, 5)
}

export const createMockSpatialQueryResult = payload => {
  const queryType = payload?.query_type || 'point_radius'
  const queryId = payload?.query_id || `query_${Date.now()}`
  const pois = pickPois(queryType)
  const poiIds = pois.map(poi => poi.id)
  const label = queryLabels[queryType] || '空间查询'

  return {
    query_id: queryId,
    pois,
    map_commands: [
      {
        type: 'HIGHLIGHT_POIS',
        payload: {
          poi_ids: poiIds,
          layer_id: `spatial-query-result-${queryId}`,
          title: `${label}结果`
        }
      }
    ],
    agent_context: {
      text: `用户通过${label}选中了 ${pois.length} 个 POI，可作为当前规划候选目标。`,
      poi_ids: poiIds
    }
  }
}
