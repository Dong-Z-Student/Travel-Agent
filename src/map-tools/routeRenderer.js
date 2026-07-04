import Feature from 'ol/Feature.js'
import LineString from 'ol/geom/LineString.js'
import Point from 'ol/geom/Point.js'
import VectorLayer from 'ol/layer/Vector.js'
import VectorSource from 'ol/source/Vector.js'
import { Circle, Fill, Stroke, Style, Text } from 'ol/style.js'
import { addLayer, removeLayerById, removeLayersByGroup } from '@/map-core/layerManager'
import { getActiveBaseMapKey, lonLatToMapCoord, lonLatsToMapCoords } from '@/map-core/projectionUtils'

const routeAnimations = new Map()

const routeLineStyle = [
  new Style({
    stroke: new Stroke({
      color: 'rgba(255, 255, 255, 0.96)',
      width: 7,
      lineCap: 'round',
      lineJoin: 'round'
    })
  }),
  new Style({
    stroke: new Stroke({
      color: '#0f766e',
      width: 4,
      lineCap: 'round',
      lineJoin: 'round'
    })
  })
]

const stopStyle = feature => new Style({
  image: new Circle({
    radius: 4.5,
    fill: new Fill({ color: '#fff' }),
    stroke: new Stroke({ color: '#0f766e', width: 2 })
  }),
  text: new Text({
    text: feature.get('name') || '',
    offsetY: -14,
    font: '600 11px sans-serif',
    fill: new Fill({ color: '#0f766e' }),
    stroke: new Stroke({ color: '#fff', width: 3 })
  })
})

const movingStyle = [
  new Style({
    image: new Circle({
      radius: 10,
      fill: new Fill({ color: 'rgba(249, 115, 22, 0.22)' })
    })
  }),
  new Style({
    image: new Circle({
      radius: 6,
      fill: new Fill({ color: '#f97316' }),
      stroke: new Stroke({ color: '#fff', width: 2 })
    })
  })
]

const trailStyle = feature => new Style({
  stroke: new Stroke({
    color: `rgba(249, 115, 22, ${feature.get('opacity') || 0.18})`,
    width: feature.get('width') || 8,
    lineCap: 'round',
    lineJoin: 'round'
  })
})

const toMapCoords = (map, coordinates) => lonLatsToMapCoords(coordinates, getActiveBaseMapKey(map))

const getCoordinateAtProgress = (coords, progress) => {
  if (!coords.length) return null
  if (coords.length === 1) return coords[0]

  const segments = []
  let total = 0
  for (let index = 1; index < coords.length; index += 1) {
    const start = coords[index - 1]
    const end = coords[index]
    const length = Math.hypot(end[0] - start[0], end[1] - start[1])
    segments.push({ start, end, length })
    total += length
  }

  let target = total * progress
  for (const segment of segments) {
    if (target <= segment.length) {
      const ratio = segment.length === 0 ? 0 : target / segment.length
      return [
        segment.start[0] + (segment.end[0] - segment.start[0]) * ratio,
        segment.start[1] + (segment.end[1] - segment.start[1]) * ratio
      ]
    }
    target -= segment.length
  }

  return coords[coords.length - 1]
}

const getTrailCoordinates = (coords, progress, lengthRatio = 0.09, steps = 14) => {
  const trail = []
  for (let index = 0; index < steps; index += 1) {
    const ratio = index / (steps - 1)
    const sampleProgress = progress - lengthRatio * ratio
    if (sampleProgress < 0) break
    const coord = getCoordinateAtProgress(coords, sampleProgress)
    if (coord) trail.push(coord)
  }
  return trail
}

export const addPlannedRoute = (map, route) => {
  if (!map || !route?.geometry?.coordinates?.length) return null

  const baseMapKey = getActiveBaseMapKey(map)
  const coords = toMapCoords(map, route.geometry.coordinates)
  const routeFeature = new Feature(new LineString(coords))
  routeFeature.setProperties({ route_id: route.route_id, route_name: route.route_name })

  const stopFeatures = (route.stops || []).map(stop => {
    const feature = new Feature(new Point(lonLatToMapCoord([stop.longitude, stop.latitude], baseMapKey)))
    feature.setProperties(stop)
    return feature
  })

  const layer = new VectorLayer({
    source: new VectorSource({ features: [routeFeature, ...stopFeatures] }),
    style: feature => feature.getGeometry().getType() === 'LineString' ? routeLineStyle : stopStyle(feature),
    zIndex: 50
  })

  addLayer(map, layer, {
    layer_id: `route-plan-${route.route_id}`,
    group: 'route_plan',
    title: route.route_name || '规划路线',
    visible: true
  })

  map.getView().fit(routeFeature.getGeometry().getExtent(), {
    padding: [110, 110, 110, 430],
    duration: 400,
    maxZoom: 13
  })

  return layer
}

export const clearRouteAnimation = (map, routeId) => {
  const animation = routeAnimations.get(routeId)
  if (animation?.frameId) cancelAnimationFrame(animation.frameId)
  routeAnimations.delete(routeId)
  removeLayerById(map, `route-animation-${routeId}`)
}

export const clearAllRouteAnimations = map => {
  routeAnimations.forEach(animation => {
    if (animation?.frameId) cancelAnimationFrame(animation.frameId)
  })
  routeAnimations.clear()
  if (map) removeLayersByGroup(map, 'route_animation')
}

export const clearPlannedRoutes = map => {
  if (!map) return []
  return removeLayersByGroup(map, 'route_plan')
}

export const showRouteAnimation = (map, route) => {
  if (!map || !route?.geometry?.coordinates?.length) return null
  clearRouteAnimation(map, route.route_id)

  const coords = toMapCoords(map, route.geometry.coordinates)
  const trailFeatures = Array.from({ length: 13 }, (_, index) => {
    const feature = new Feature(new LineString([]))
    feature.setProperties({
      type: 'trail',
      opacity: Math.max(0.035, 0.24 - index * 0.015),
      width: Math.max(1.4, 13 - index * 0.85)
    })
    return feature
  })
  const movingFeature = new Feature(new Point(coords[0]))
  movingFeature.set('type', 'moving')
  const layer = new VectorLayer({
    source: new VectorSource({ features: [...trailFeatures, movingFeature] }),
    style: feature => feature.get('type') === 'trail' ? trailStyle(feature) : movingStyle,
    zIndex: 65
  })

  addLayer(map, layer, {
    layer_id: `route-animation-${route.route_id}`,
    group: 'route_animation',
    title: `${route.route_name || '路线'}动画`,
    visible: true
  })

  let progress = 0
  const speed = route.animation?.speed || 0.00001
  const loop = route.animation?.loop !== false

  const render = () => {
    progress += speed
    if (progress > 1) {
      if (!loop) return
      progress = 0
    }
    const currentCoord = getCoordinateAtProgress(coords, progress)
    movingFeature.getGeometry().setCoordinates(currentCoord)

    const trailCoords = getTrailCoordinates(coords, progress)
    trailFeatures.forEach((feature, index) => {
      const head = trailCoords[index]
      const tail = trailCoords[index + 1]
      feature.getGeometry().setCoordinates(head && tail ? [tail, head] : [])
    })

    layer.changed()
    const frameId = requestAnimationFrame(render)
    routeAnimations.set(route.route_id, { frameId, layer })
  }

  const frameId = requestAnimationFrame(render)
  routeAnimations.set(route.route_id, { frameId, layer })
  return layer
}
