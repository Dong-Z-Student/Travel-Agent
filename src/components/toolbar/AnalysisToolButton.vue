<script setup>
import { ref, watch } from 'vue'
import Feature from 'ol/Feature.js'
import Point from 'ol/geom/Point.js'
import Heatmap from 'ol/layer/Heatmap.js'
import VectorSource from 'ol/source/Vector.js'
import { getPopulationHeatmap } from '@/services/analysisService'
import { addLayer, getLayerById, removeLayerById, setLayerVisible } from '@/map-core/layerManager'
import { lonLatToMapCoord } from '@/map-core/projectionUtils'
import { useMapStore } from '@/stores/mapStore'
import ToolbarButton from './ToolbarButton.vue'
import ToolPopover from './ToolPopover.vue'

defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['toggle'])
const mapStore = useMapStore()
const visible = ref(false)
const layerId = 'population_heatmap'
let heatmapData = null

const createHeatmapLayer = data => {
  const features = (data.points || []).map(point => {
    const feature = new Feature(new Point(lonLatToMapCoord([point.longitude, point.latitude], mapStore.activeBaseMap)))
    feature.set('weight', point.weight)
    return feature
  })
  return new Heatmap({
    source: new VectorSource({ features }),
    blur: 16,
    radius: 13,
    weight: feature => feature.get('weight') || 0.5,
    zIndex: 30
  })
}

const toggleHeatmap = async () => {
  const map = mapStore.map
  if (!map) return
  const existing = getLayerById(map, layerId)
  if (existing) {
    visible.value = !existing.getVisible()
    setLayerVisible(map, layerId, visible.value)
    return
  }

  heatmapData = await getPopulationHeatmap({ city: '武汉市', bbox: [113.68, 29.96, 115.08, 31.36] })
  const layer = createHeatmapLayer(heatmapData)
  addLayer(map, layer, { layer_id: layerId, group: 'population_heatmap', title: '人口热力图', visible: true })
  visible.value = true
}

const clearHeatmap = () => {
  const map = mapStore.map
  if (!map) return
  removeLayerById(map, layerId)
  visible.value = false
}

watch(() => mapStore.activeBaseMap, () => {
  const map = mapStore.map
  if (!map || !visible.value || !heatmapData) return
  removeLayerById(map, layerId)
  const layer = createHeatmapLayer(heatmapData)
  addLayer(map, layer, { layer_id: layerId, group: 'population_heatmap', title: '人口热力图', visible: true })
})
</script>

<template>
  <div class="tool-wrap">
    <ToolbarButton label="分析" :active="open || visible" @click="emit('toggle')" />
    <ToolPopover v-if="open">
      <div class="analysis-panel">
        <button type="button" :class="{ active: visible }" @click="toggleHeatmap">人口热力图</button>
        <button type="button" class="plain" @click="clearHeatmap">清除</button>
      </div>
    </ToolPopover>
  </div>
</template>

<style scoped>
.tool-wrap { position: relative; }
.analysis-panel { display: grid; gap: 8px; }
button {
  height: 34px;
  color: #334155;
  cursor: pointer;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 7px;
}
button.active {
  color: #0f766e;
  font-weight: 700;
  background: #ecfdf5;
  border-color: rgba(15, 118, 110, 0.35);
}
button.plain { color: #64748b; }
</style>
