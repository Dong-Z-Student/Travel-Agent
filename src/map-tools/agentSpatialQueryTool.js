import Draw from 'ol/interaction/Draw.js'
import Feature from 'ol/Feature.js'
import LineString from 'ol/geom/LineString.js'
import VectorLayer from 'ol/layer/Vector.js'
import VectorSource from 'ol/source/Vector.js'
import { Circle, Fill, Stroke, Style } from 'ol/style.js'
import { queryPois } from '@/services/spatialQueryService'
import { createMapCommandExecutor } from '@/map-core/mapCommandExecutor'
import { addLayer, removeLayersByGroup } from '@/map-core/layerManager'
import { featureToGeoJSON4326 } from '@/map-core/projectionUtils'
import { sampleBezierCurve } from './bezierMath'

const AGENT_SPATIAL_DRAW_KEY = 'travel_agent_spatial_query_draw'

const queryTypeMap = {
  point_nearby: 'point_radius',
  line_nearby: 'line_buffer',
  bezier_nearby: 'bezier_buffer',
  polygon_inside: 'polygon_contains'
}

const drawTypeMap = {
  point_nearby: 'Point',
  line_nearby: 'LineString',
  bezier_nearby: 'LineString',
  polygon_inside: 'Polygon'
}

const getDrawHint = tool => {
  if (tool.key === 'point_nearby') return '请在地图上单击放置查询点。'
  if (tool.key === 'bezier_nearby') return '请依次点击起点、多个控制点和终点，双击结束后生成贝塞尔查询曲线。'
  if (tool.key === 'polygon_inside') return '请在地图上绘制查询范围，双击闭合结束。'
  return '请在地图上绘制查询线，双击结束。'
}

const areaStyle = feature => {
  const type = feature.getGeometry()?.getType()
  const isPoint = type === 'Point'
  return new Style({
    image: isPoint
      ? new Circle({
        radius: 7,
        fill: new Fill({ color: '#0f766e' }),
        stroke: new Stroke({ color: '#fff', width: 3 })
      })
      : undefined,
    fill: new Fill({ color: 'rgba(15, 118, 110, 0.12)' }),
    stroke: new Stroke({ color: '#0f766e', width: 3 })
  })
}

const createAreaLayer = feature => new VectorLayer({
  source: new VectorSource({ features: [feature] }),
  style: areaStyle,
  zIndex: 54
})

const removeAllAgentSpatialDraws = map => {
  const interactions = [...map.getInteractions().getArray()]
  interactions.forEach(interaction => {
    if (interaction.get?.(AGENT_SPATIAL_DRAW_KEY)) {
      interaction.setActive(false)
      map.removeInteraction(interaction)
    }
  })
}

const cancelBrowserDoubleClick = event => {
  event.preventDefault()
  event.stopPropagation()
}

const addDrawEndGuard = map => {
  map.getViewport().addEventListener('dblclick', cancelBrowserDoubleClick, { once: true, capture: true })
}

export const startAgentSpatialQueryTool = ({ map, tool, onMessage, onContext, onComplete }) => {
  if (!map || !tool?.key) return null

  removeAllAgentSpatialDraws(map)
  removeLayersByGroup(map, 'spatial_query_area')
  removeLayersByGroup(map, 'spatial_query_result')

  const draw = new Draw({
    type: drawTypeMap[tool.key],
    source: new VectorSource(),
    stopClick: true
  })
  draw.set(AGENT_SPATIAL_DRAW_KEY, true)

  const cleanup = () => {
    removeAllAgentSpatialDraws(map)
  }

  draw.on('drawstart', () => {
    onMessage?.(`${tool.label}：${getDrawHint(tool)}`)
  })

  draw.on('drawend', async event => {
    cleanup()
    addDrawEndGuard(map)
    const queryId = `query_${Date.now()}`
    let feature = event.feature
    let geometry = feature.getGeometry()

    if (tool.key === 'bezier_nearby') {
      feature = new Feature(new LineString(sampleBezierCurve(geometry.getCoordinates())))
      geometry = feature.getGeometry()
    }

    addLayer(map, createAreaLayer(feature), {
      layer_id: `spatial-query-area-${queryId}`,
      group: 'spatial_query_area',
      title: `${tool.label}范围`,
      visible: true
    })

    const response = await queryPois({
      query_id: queryId,
      query_type: queryTypeMap[tool.key],
      geometry: featureToGeoJSON4326(feature).geometry,
      radius_meters: tool.key === 'point_nearby' ? 1000 : undefined,
      buffer_meters: ['line_nearby', 'bezier_nearby'].includes(tool.key) ? 800 : undefined
    })

    createMapCommandExecutor({ map }).executeMany(response.map_commands || [])
    onContext?.(response.agent_context)
    onMessage?.(response.agent_context?.text || `已完成${tool.label}。`)
    onComplete?.(response)
  })

  map.addInteraction(draw)
  onMessage?.(`${tool.label}已启动。${getDrawHint(tool)}`)
  return cleanup
}
