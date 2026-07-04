<script setup>
import { nextTick, onBeforeUnmount, watch, ref } from 'vue'
import Feature from 'ol/Feature.js'
import Point from 'ol/geom/Point.js'
import VectorLayer from 'ol/layer/Vector.js'
import VectorSource from 'ol/source/Vector.js'
import Cluster from 'ol/source/Cluster.js'
import Overlay from 'ol/Overlay.js'
import { Circle, Fill, Stroke, Style, Text } from 'ol/style.js'
import { boundingExtent } from 'ol/extent.js'
import { unByKey } from 'ol/Observable.js'
import { addLayer, removeLayerById } from '@/map-core/layerManager'
import { lonLatToMapCoord } from '@/map-core/projectionUtils'
import { getPoiDetail, getPois } from '@/services/poiService'
import { POI_CATEGORIES } from '@/mocks/mockPois'
import { useMapStore } from '@/stores/mapStore'
import { usePoiStore } from '@/stores/poiStore'
import PoiPopupCard from './PoiPopupCard.vue'

const CATEGORY_STYLE = {
  scenic_spot: { color: '#e85d3f', stroke: '#fff2ec', label: '景' },
  hotel: { color: '#2f80ed', stroke: '#edf5ff', label: '酒' },
  metro_station: { color: '#16a36a', stroke: '#effaf4', label: '铁' }
}

const mapStore = useMapStore()
const poiStore = usePoiStore()
const popupEl = ref(null)
const selectedPoi = ref(null)
const selectedDetail = ref(null)

let overlay = null
let clickKey = null
const layerIds = Object.values(POI_CATEGORIES).map(item => item.layerId)

const createPoiFeature = poi => {
  const feature = new Feature({
    geometry: new Point(lonLatToMapCoord([poi.longitude, poi.latitude], mapStore.activeBaseMap)),
    poi
  })
  feature.setId(poi.id)
  return feature
}

const makeClusterStyle = category => feature => {
  const members = feature.get('features') || []
  const size = members.length
  const style = CATEGORY_STYLE[category]
  const radius = size > 1 ? Math.min(18 + size, 32) : 11
  const text = size > 1 ? String(size) : style.label

  return new Style({
    image: new Circle({
      radius,
      fill: new Fill({ color: style.color }),
      stroke: new Stroke({ color: style.stroke, width: 3 })
    }),
    text: new Text({
      text,
      font: size > 1 ? '700 13px sans-serif' : '700 12px sans-serif',
      fill: new Fill({ color: '#fff' })
    })
  })
}

const createClusterLayer = (category, pois) => {
  const source = new VectorSource({ features: pois.map(createPoiFeature) })
  const clusterSource = new Cluster({ distance: 44, minDistance: 12, source })

  return new VectorLayer({
    source: clusterSource,
    zIndex: 20,
    style: makeClusterStyle(category),
    declutter: true
  })
}

const closePopup = () => {
  overlay?.setPosition(undefined)
  selectedPoi.value = null
  selectedDetail.value = null
  poiStore.setSelectedPoi(null)
}

const openPoiPopup = async (poi, coordinate) => {
  selectedPoi.value = poi
  selectedDetail.value = null
  poiStore.setSelectedPoi(poi)
  overlay?.setPosition(coordinate)

  const cached = poiStore.detailCache[poi.id]
  const detail = cached || await getPoiDetail(poi.id)
  if (detail) {
    poiStore.cachePoiDetail(detail)
    selectedDetail.value = detail
  }
  await nextTick()
  overlay?.setPosition(coordinate)
}

const handleMapClick = event => {
  const map = mapStore.map
  if (!map) return

  const clusterFeature = map.forEachFeatureAtPixel(event.pixel, feature => {
    const members = feature.get('features')
    return members?.length ? feature : null
  }, { hitTolerance: 6 })

  if (!clusterFeature) {
    closePopup()
    return
  }

  const members = clusterFeature.get('features') || []
  if (members.length === 1) {
    const poi = members[0].get('poi')
    openPoiPopup(poi, clusterFeature.getGeometry().getCoordinates())
    return
  }

  closePopup()
  const coords = members.map(feature => feature.getGeometry().getCoordinates())
  map.getView().fit(boundingExtent(coords), { padding: [120, 120, 120, 120], duration: 300, maxZoom: 15 })
}

const mountPoiLayers = async map => {
  layerIds.forEach(layerId => removeLayerById(map, layerId, { silent: true }))

  const { pois } = await getPois({
    city: '武汉市',
    category_codes: Object.keys(POI_CATEGORIES),
    bbox: [113.68, 29.96, 115.08, 31.36],
    zoom: map.getView().getZoom()
  })
  poiStore.setPois(pois)
  renderPoiLayers(map, pois)

  overlay = new Overlay({
    element: popupEl.value,
    positioning: 'bottom-center',
    autoPan: { animation: { duration: 250 }, margin: 24 },
    offset: [0, -18]
  })
  map.addOverlay(overlay)

  clickKey = map.on('singleclick', handleMapClick)
}

const renderPoiLayers = (map, pois) => {
  layerIds.forEach(layerId => removeLayerById(map, layerId, { silent: true }))
  Object.entries(POI_CATEGORIES).forEach(([category, meta]) => {
    const categoryPois = pois.filter(poi => poi.category_code === category)
    const layer = createClusterLayer(category, categoryPois)
    addLayer(map, layer, {
      layer_id: meta.layerId,
      group: meta.group,
      title: meta.label,
      visible: true
    })
  })
}

watch(() => mapStore.ready, ready => {
  if (ready && mapStore.map) mountPoiLayers(mapStore.map)
}, { immediate: true })

watch(() => mapStore.activeBaseMap, () => {
  if (!mapStore.ready || !mapStore.map || !poiStore.pois.length) return
  closePopup()
  renderPoiLayers(mapStore.map, poiStore.pois)
})

onBeforeUnmount(() => {
  const map = mapStore.map
  if (map) {
    layerIds.forEach(layerId => removeLayerById(map, layerId, { silent: true }))
    if (overlay) map.removeOverlay(overlay)
    if (clickKey) unByKey(clickKey)
  }
})
</script>

<template>
  <div ref="popupEl" class="poi-popup-shell">
    <button v-if="selectedPoi" class="poi-popup-close" type="button" @click="closePopup">×</button>
    <PoiPopupCard :poi="selectedPoi" :detail="selectedDetail" />
  </div>
</template>

<style scoped>
.poi-popup-shell {
  position: relative;
}

.poi-popup-close {
  position: absolute;
  z-index: 2;
  top: 6px;
  right: 6px;
  width: 24px;
  height: 24px;
  padding: 0;
  color: #334155;
  line-height: 22px;
  text-align: center;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 50%;
}
</style>



