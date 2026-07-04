import Map from 'ol/Map.js'
import View from 'ol/View.js'
import { defaults as defaultControls } from 'ol/control/defaults.js'
import { MAP_CONFIG } from '@/config/mapConfig'
import { createBaseMapLayers } from './baseMapFactory'
import { lonLatToMapCoord } from './projectionUtils'

export const WUHAN_CENTER = MAP_CONFIG.defaultCenter
export const WUHAN_DEFAULT_ZOOM = MAP_CONFIG.defaultZoom
export const createDefaultBaseLayers = () => createBaseMapLayers('standard')

export const createMap = (target, options = {}) => {
  const view = new View({
    projection: 'EPSG:3857',
    center: lonLatToMapCoord(options.center || WUHAN_CENTER),
    zoom: options.zoom || WUHAN_DEFAULT_ZOOM,
    rotation: 0
  })

  const map = new Map({
    target,
    view,
    layers: options.layers || createDefaultBaseLayers(),
    controls: defaultControls({
      zoom: false,
      rotate: false,
      attribution: false
    })
  })
  map.set('active_base_map', options.baseMap || 'standard')
  return map
}
