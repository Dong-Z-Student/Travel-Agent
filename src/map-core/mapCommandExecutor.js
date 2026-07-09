import { getLayerById, removeLayerById, removeLayersByGroup, setLayerVisible } from './layerManager'

import Feature from 'ol/Feature.js'
import Point from 'ol/geom/Point.js'
import VectorLayer from 'ol/layer/Vector.js'
import VectorSource from 'ol/source/Vector.js'
import { Circle, Fill, Stroke, Style, Text } from 'ol/style.js'
import { addPlannedRoute, clearAllRouteAnimations, clearPlannedRoutes, showRouteAnimation } from '@/map-tools/routeRenderer'
import { getActiveBaseMapKey, lonLatToMapCoord } from './projectionUtils'
import { addLayer } from './layerManager'

const highlightStyle = feature => [
  new Style({
    image: new Circle({
      radius: 13,
      fill: new Fill({ color: 'rgba(20, 184, 166, 0.16)' }),
      stroke: new Stroke({ color: 'rgba(20, 184, 166, 0.28)', width: 1.5 })
    })
  }),
  new Style({
    image: new Circle({
      radius: 6.5,
      fill: new Fill({ color: '#14b8a6' }),
      stroke: new Stroke({ color: 'rgba(255, 255, 255, 0.96)', width: 2 })
    }),
    text: new Text({
      text: feature.get('name_zh') || '',
      offsetY: -17,
      font: '600 11px sans-serif',
      fill: new Fill({ color: '#0f766e' }),
      stroke: new Stroke({ color: 'rgba(255, 255, 255, 0.96)', width: 3 })
    })
  })
]

export class MapCommandExecutor {
  constructor({ map, layerManager = {} } = {}) {
    this.map = map
    this.layerManager = layerManager
  }

  setMap(map) {
    this.map = map
  }

  execute(command) {
    if (!command || !command.type) return null
    const handler = this[`execute${command.type}`]
    if (typeof handler !== 'function') {
      console.warn(`[MapCommandExecutor] Unsupported command: ${command.type}`)
      return null
    }
    return handler.call(this, command.payload || {})
  }

  executeMany(commands = []) {
    if (this.shouldReplacePlanningResult(commands)) {
      this.clearPlanningResult()
    }
    return commands.map(command => this.execute(command))
  }

  shouldReplacePlanningResult(commands = []) {
    return commands.some(command =>
      ['ADD_ROUTE', 'PLAY_ROUTE_ANIMATION'].includes(command?.type)
      || command?.payload?.replace_existing === true
    )
  }

  clearPlanningResult() {
    if (!this.map) return
    clearAllRouteAnimations(this.map)
    clearPlannedRoutes(this.map)
    removeLayersByGroup(this.map, 'spatial_query_result')
  }

  executeCLEAR_LAYER(payload) {
    if (!this.map || !payload.layer_id) return null
    return removeLayerById(this.map, payload.layer_id)
  }

  executeFIT_BOUNDS(payload) {
    if (!this.map || !payload.extent) return null
    this.map.getView().fit(payload.extent, { padding: payload.padding || [80, 80, 80, 80], duration: 300 })
    return true
  }

  executeSET_LAYER_VISIBLE(payload) {
    if (!this.map || !payload.layer_id) return null
    return setLayerVisible(this.map, payload.layer_id, payload.visible !== false)
  }

  executeADD_POIS(payload) { return this.layerManager.addPois?.(payload) || null }
  executeHIGHLIGHT_POIS(payload) {
    if (this.layerManager.highlightPois) return this.layerManager.highlightPois(payload)
    if (!this.map || !payload.poi_ids?.length) return null

    const ids = new Set(payload.poi_ids)
    const sourcePois = payload.pois || []
    const baseMapKey = getActiveBaseMapKey(this.map)
    const features = sourcePois
      .filter(poi => !ids.size || ids.has(poi.id))
      .map(poi => {
        const feature = new Feature(new Point(lonLatToMapCoord([poi.longitude, poi.latitude], baseMapKey)))
        feature.setProperties(poi)
        return feature
      })

    const layer = new VectorLayer({
      source: new VectorSource({ features }),
      style: highlightStyle,
      zIndex: 55
    })
    addLayer(this.map, layer, {
      layer_id: payload.layer_id || 'spatial-query-result',
      group: 'spatial_query_result',
      title: payload.title || '空间查询结果',
      visible: true
    })

    if (features.length) {
      this.map.getView().fit(layer.getSource().getExtent(), {
        padding: [90, 90, 90, 420],
        duration: 350,
        maxZoom: 14
      })
    }
    return layer
  }
  executeFOCUS_POIS(payload) { return this.layerManager.focusPois?.(payload) || null }
  executeADD_ROUTE(payload) {
    if (this.layerManager.addRoute) return this.layerManager.addRoute(payload)
    if (!this.map) return null
    if (!payload.route) return null
    return addPlannedRoute(this.map, payload.route)
  }

  executePLAY_ROUTE_ANIMATION(payload) {
    if (this.layerManager.playRouteAnimation) return this.layerManager.playRouteAnimation(payload)
    if (!this.map) return null
    if (!payload.route) return null
    return showRouteAnimation(this.map, payload.route)
  }
  executeSHOW_POPUP(payload) { return this.layerManager.showPopup?.(payload) || null }
  executeSHOW_HEATMAP(payload) { return this.layerManager.showHeatmap?.(payload) || null }
}

export const createMapCommandExecutor = options => new MapCommandExecutor(options)

