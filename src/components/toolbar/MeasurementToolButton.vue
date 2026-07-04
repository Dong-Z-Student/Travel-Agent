<script setup>
import { onBeforeUnmount, ref } from 'vue'
import Draw from 'ol/interaction/Draw.js'
import LineString from 'ol/geom/LineString.js'
import Overlay from 'ol/Overlay.js'
import Point from 'ol/geom/Point.js'
import VectorLayer from 'ol/layer/Vector.js'
import VectorSource from 'ol/source/Vector.js'
import { getArea, getLength } from 'ol/sphere.js'
import { getCenter } from 'ol/extent.js'
import { Circle, Fill, Stroke, Style } from 'ol/style.js'
import { addLayer, getLayerById, removeLayerById } from '@/map-core/layerManager'
import { useMapStore } from '@/stores/mapStore'
import ToolbarButton from './ToolbarButton.vue'

const MEASURE_DRAW_KEY = 'travel_agent_measure_draw'
const STOP_MEASURE_EVENT = 'travel-agent-stop-measure'

const props = defineProps({ mode: { type: String, required: true }, label: { type: String, required: true } })
const emit = defineEmits(['click-tool'])
const mapStore = useMapStore()
const active = ref(false)
let draw = null
let source = null
let layer = null
const overlayGroups = new Map()
const geometryListeners = new Map()

const layerId = props.mode === 'distance' ? 'measure_distance_layer' : 'measure_area_layer'
const group = props.mode === 'distance' ? 'measure_distance' : 'measure_area'

const formatLength = meters => meters >= 1000 ? `${(meters / 1000).toFixed(2)} km` : `${meters.toFixed(1)} m`
const formatArea = meters => meters >= 10000 ? `${(meters / 10000).toFixed(2)} ha` : `${meters.toFixed(1)} m²`

const getLabelCoord = geometry => {
  if (geometry.getType() === 'Polygon') return getCenter(geometry.getExtent())
  const coords = geometry.getCoordinates()
  return coords[coords.length - 1]
}

const getDistanceSegmentText = (start, end) => formatLength(getLength(new LineString([start, end])))

const styleFeature = feature => {
  const geometry = feature.getGeometry()
  if (!geometry) return []
  const isDistance = props.mode === 'distance'
  const styles = [
    new Style({
      fill: new Fill({ color: isDistance ? 'rgba(232, 93, 63, 0.10)' : 'rgba(47, 128, 237, 0.12)' }),
      stroke: new Stroke({ color: isDistance ? '#e85d3f' : '#2f80ed', width: 3 })
    })
  ]

  const coords = isDistance ? geometry.getCoordinates() : (geometry.getCoordinates()?.[0] || []).slice(0, -1)
  coords.forEach(coord => {
    styles.push(new Style({
      geometry: new Point(coord),
      image: new Circle({
        radius: 5,
        fill: new Fill({ color: '#fff' }),
        stroke: new Stroke({ color: isDistance ? '#ef3340' : '#2f80ed', width: 3 })
      })
    }))
  })

  return styles
}

const ensureLayer = map => {
  const existing = getLayerById(map, layerId)
  if (existing) {
    layer = existing
    source = existing.getSource()
    return
  }
  source = new VectorSource()
  layer = new VectorLayer({ source, style: styleFeature, zIndex: 60 })
  addLayer(map, layer, { layer_id: layerId, group, title: props.label, visible: true })
}

const removeFeature = (map, feature) => {
  source?.removeFeature(feature)
  const listenerKey = geometryListeners.get(feature)
  if (listenerKey) {
    feature.getGeometry()?.un('change', listenerKey)
    geometryListeners.delete(feature)
  }
  clearFeatureOverlays(map, feature)
}

const addOverlay = (map, feature, position, element, options = {}) => {
  const overlay = new Overlay({
    element,
    positioning: options.positioning || 'bottom-left',
    offset: options.offset || [8, -8],
    stopEvent: true
  })
  overlay.setPosition(position)
  map.addOverlay(overlay)
  const group = overlayGroups.get(feature) || []
  group.push(overlay)
  overlayGroups.set(feature, group)
  return overlay
}

const clearFeatureOverlays = (map, feature) => {
  const group = overlayGroups.get(feature) || []
  group.forEach(overlay => {
    map.removeOverlay(overlay)
    overlay.getElement()?.remove()
  })
  overlayGroups.delete(feature)
}

const createTag = (text, onRemoveVertex, onRemoveFeature) => {
  const tag = document.createElement('span')
  tag.className = 'measure-tag'
  const label = document.createElement('span')
  label.textContent = text
  tag.appendChild(label)

  if (onRemoveVertex) {
    const pointDelete = document.createElement('button')
    pointDelete.className = 'measure-tag-x'
    pointDelete.type = 'button'
    pointDelete.title = '删除该端点'
    pointDelete.textContent = '×'
    pointDelete.addEventListener('click', event => {
      event.stopPropagation()
      onRemoveVertex()
    })
    tag.appendChild(pointDelete)
  }

  if (onRemoveFeature) {
    const featureDelete = document.createElement('button')
    featureDelete.className = 'measure-tag-trash'
    featureDelete.type = 'button'
    featureDelete.title = '删除本次测量'
    featureDelete.textContent = '▣'
    featureDelete.addEventListener('click', event => {
      event.stopPropagation()
      onRemoveFeature()
    })
    tag.appendChild(featureDelete)
  }

  return tag
}

const removeDistanceVertex = (map, feature, index) => {
  const geometry = feature.getGeometry()
  const coords = geometry?.getCoordinates() || []
  if (coords.length <= 2) {
    removeFeature(map, feature)
    return
  }
  geometry.setCoordinates(coords.filter((_, itemIndex) => itemIndex !== index))
}

const removeAreaVertex = (map, feature, index) => {
  const geometry = feature.getGeometry()
  const ring = geometry?.getCoordinates()?.[0] || []
  const coords = ring.slice(0, -1)
  if (coords.length <= 3) {
    removeFeature(map, feature)
    return
  }
  const nextCoords = coords.filter((_, itemIndex) => itemIndex !== index)
  geometry.setCoordinates([[...nextCoords, nextCoords[0]]])
}

const addDistanceOverlays = (map, feature) => {
  const geometry = feature.getGeometry()
  const coords = geometry?.getCoordinates() || []
  if (!coords.length) return

  coords.forEach((coord, index) => {
    const isStart = index === 0
    const isEnd = index === coords.length - 1
    const text = isStart
      ? '起点'
      : isEnd
        ? `共${formatLength(getLength(geometry))}`
        : getDistanceSegmentText(coords[index - 1], coord)

    addOverlay(
      map,
      feature,
      coord,
      createTag(
        text,
        () => removeDistanceVertex(map, feature, index),
        isEnd ? () => removeFeature(map, feature) : null
      )
    )
  })
}

const addAreaOverlays = (map, feature) => {
  const geometry = feature.getGeometry()
  const ring = geometry?.getCoordinates()?.[0] || []
  const coords = ring.slice(0, -1)
  if (!coords.length) return

  coords.forEach((coord, index) => {
    addOverlay(map, feature, coord, createTag(`顶点${index + 1}`, () => removeAreaVertex(map, feature, index)))
  })

  addOverlay(
    map,
    feature,
    getLabelCoord(geometry),
    createTag(`面积${formatArea(getArea(geometry))}`, null, () => removeFeature(map, feature)),
    { positioning: 'center-left', offset: [10, 0] }
  )
}

const refreshFeatureOverlays = (map, feature) => {
  clearFeatureOverlays(map, feature)
  if (props.mode === 'distance') addDistanceOverlays(map, feature)
  else addAreaOverlays(map, feature)
}

const addDeleteOverlay = (map, feature) => {
  refreshFeatureOverlays(map, feature)
  const geometry = feature.getGeometry()
  const listener = () => refreshFeatureOverlays(map, feature)
  geometry?.on('change', listener)
  geometryListeners.set(feature, listener)
}

const removeAllMeasureDraws = map => {
  const interactions = [...map.getInteractions().getArray()]
  interactions.forEach(interaction => {
    if (interaction.get?.(MEASURE_DRAW_KEY)) {
      interaction.setActive(false)
      map.removeInteraction(interaction)
    }
  })
}

const finishDraw = (notifyOthers = false) => {
  const map = mapStore.map
  if (map) {
    removeAllMeasureDraws(map)
  }
  draw = null
  active.value = false
  if (notifyOthers) {
    window.dispatchEvent(new CustomEvent(STOP_MEASURE_EVENT, { detail: { sourceMode: props.mode } }))
  }
}

const stopDraw = () => {
  finishDraw()
}

const cancelBrowserDoubleClick = event => {
  event.preventDefault()
  event.stopPropagation()
}

const addDrawEndGuard = map => {
  const viewport = map.getViewport()
  viewport.addEventListener('dblclick', cancelBrowserDoubleClick, { once: true, capture: true })
}

const startDraw = () => {
  emit('click-tool')
  const map = mapStore.map
  if (!map) return
  finishDraw(true)
  ensureLayer(map)

  draw = new Draw({
    source,
    type: props.mode === 'distance' ? 'LineString' : 'Polygon',
    stopClick: true
  })
  draw.set(MEASURE_DRAW_KEY, true)
  draw.on('drawend', event => {
    const feature = event.feature
    finishDraw(true)
    addDrawEndGuard(map)
    addDeleteOverlay(map, feature)
  })
  map.addInteraction(draw)
  active.value = true
}

const handleExternalStop = event => {
  if (event.detail?.sourceMode === props.mode) return
  finishDraw()
}

window.addEventListener(STOP_MEASURE_EVENT, handleExternalStop)

onBeforeUnmount(() => {
  const map = mapStore.map
  stopDraw()
  overlayGroups.forEach(group => {
    group.forEach(overlay => {
      map?.removeOverlay(overlay)
      overlay.getElement()?.remove()
    })
  })
  overlayGroups.clear()
  geometryListeners.clear()
  window.removeEventListener(STOP_MEASURE_EVENT, handleExternalStop)
  if (map) removeLayerById(map, layerId)
})
</script>

<template>
  <ToolbarButton :label="label" :active="active" @click="startDraw" />
</template>

<style>
.measure-tag {
  display: inline-flex;
  gap: 3px;
  align-items: center;
  padding: 2px 5px;
  font-size: 12px;
  line-height: 1.25;
  color: #334155;
  white-space: nowrap;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-radius: 2px;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.18);
  transform: translateY(-8px);
}

.measure-tag-x,
.measure-tag-trash {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 14px;
  height: 14px;
  padding: 0;
  color: #475569;
  cursor: pointer;
  background: transparent;
  border: 0;
}

.measure-tag-x {
  font-size: 14px;
  font-weight: 700;
  line-height: 1;
}

.measure-tag-trash {
  font-size: 11px;
  border-left: 1px solid rgba(148, 163, 184, 0.45);
}

.measure-tag-x:hover,
.measure-tag-trash:hover {
  color: #ef3340;
}
</style>
