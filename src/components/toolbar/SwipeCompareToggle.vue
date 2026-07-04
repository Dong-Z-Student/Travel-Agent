<script setup>
import { onBeforeUnmount, ref } from 'vue'
import TileLayer from 'ol/layer/Tile.js'
import XYZ from 'ol/source/XYZ.js'
import OSM from 'ol/source/OSM.js'
import { getRenderPixel } from 'ol/render.js'
import { unByKey } from 'ol/Observable.js'
import { MAP_CONFIG } from '@/config/mapConfig'
import { addLayer, removeLayerById } from '@/map-core/layerManager'
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()
const active = ref(false)
const value = ref(50)
const layerId = 'swipe_compare_layer'
let layer = null
let preKey = null
let postKey = null

const createSwipeLayer = () => {
  if (!MAP_CONFIG.tiandituKey) return new TileLayer({ source: new OSM(), zIndex: 10 })
  return new TileLayer({
    source: new XYZ({
      projection: 'EPSG:4326',
      url: `http://t{0-7}.tianditu.gov.cn/img_c/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=c&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${MAP_CONFIG.tiandituKey}`
    }),
    zIndex: 10
  })
}

const enableSwipe = () => {
  const map = mapStore.map
  if (!map || active.value) return
  layer = createSwipeLayer()
  preKey = layer.on('prerender', event => {
    const ctx = event.context
    const mapSize = map.getSize()
    const width = mapSize[0] * (Number(value.value) / 100)
    const tl = getRenderPixel(event, [width, 0])
    const tr = getRenderPixel(event, [mapSize[0], 0])
    const bl = getRenderPixel(event, [width, mapSize[1]])
    const br = getRenderPixel(event, mapSize)
    ctx.save()
    ctx.beginPath()
    ctx.moveTo(tl[0], tl[1])
    ctx.lineTo(bl[0], bl[1])
    ctx.lineTo(br[0], br[1])
    ctx.lineTo(tr[0], tr[1])
    ctx.closePath()
    ctx.clip()
  })
  postKey = layer.on('postrender', event => event.context.restore())
  addLayer(map, layer, { layer_id: layerId, group: 'swipe_compare', title: '卷帘对比', visible: true })
  active.value = true
}

const disableSwipe = () => {
  const map = mapStore.map
  if (preKey) unByKey(preKey)
  if (postKey) unByKey(postKey)
  preKey = null
  postKey = null
  if (map) removeLayerById(map, layerId)
  layer = null
  active.value = false
}

const toggle = () => active.value ? disableSwipe() : enableSwipe()
const render = () => mapStore.map?.render?.()

onBeforeUnmount(disableSwipe)
</script>

<template>
  <div class="swipe-tool">
    <button type="button" :class="{ active }" @click="toggle">卷帘</button>
    <input v-if="active" v-model="value" type="range" min="0" max="100" @input="render" />
  </div>
</template>

<style scoped>
.swipe-tool { display: grid; gap: 8px; }
button {
  height: 32px;
  cursor: pointer;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 7px;
}
button.active { color: #0f766e; font-weight: 700; background: #ecfdf5; }
input { width: 100%; }
</style>
