<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import OverviewMap from 'ol/control/OverviewMap.js'
import { createBaseMapLayers } from '@/map-core/baseMapFactory'
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()
const overviewTarget = ref(null)
const collapsed = ref(false)
const activeBaseMap = ref('standard')
let overviewControl = null

const mountOverview = map => {
  if (!map || overviewControl) return

  overviewControl = new OverviewMap({
    target: overviewTarget.value,
    collapsed: false,
    collapsible: false,
    layers: createBaseMapLayers(activeBaseMap.value)
  })

  map.addControl(overviewControl)
}

const toggleCollapsed = () => {
  collapsed.value = !collapsed.value
}

const cleanupOverview = () => {
  const map = mapStore.map
  if (map && overviewControl) map.removeControl(overviewControl)
  overviewControl = null
}

const syncOverviewLayers = key => {
  activeBaseMap.value = key
  const overviewMap = overviewControl?.getOverviewMap?.()
  if (!overviewMap) return
  const layers = overviewMap.getLayers()
  layers.clear()
  createBaseMapLayers(key).forEach(layer => layers.push(layer))
  overviewMap.updateSize()
}

watch(() => mapStore.ready, ready => {
  if (ready && mapStore.map) mountOverview(mapStore.map)
}, { immediate: true })

watch(() => mapStore.activeBaseMap, key => {
  syncOverviewLayers(key || 'standard')
})

onBeforeUnmount(() => {
  cleanupOverview()
})
</script>

<template>
  <div class="overview-wrap" :class="{ collapsed }">
    <button
      class="overview-toggle"
      type="button"
      :title="collapsed ? '展开鹰眼' : '收起鹰眼'"
      @click="toggleCollapsed"
    >
      {{ collapsed ? '▣' : '−' }}
    </button>
    <div v-show="!collapsed" ref="overviewTarget" class="overview-shell"></div>
  </div>
</template>

<style scoped>
.overview-wrap {
  position: relative;
  pointer-events: auto;
}

.overview-shell {
  width: 172px;
  height: 118px;
  overflow: hidden;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.14);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.14);
}

.overview-toggle {
  position: absolute;
  right: 6px;
  top: 6px;
  z-index: 2;
  display: grid;
  width: 24px;
  height: 24px;
  padding: 0;
  place-items: center;
  color: #1f2937;
  font-size: 17px;
  line-height: 1;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.12);
  border-radius: 6px;
  box-shadow: 0 3px 10px rgba(15, 23, 42, 0.12);
}

.overview-toggle:hover {
  background: #fff;
}

.overview-wrap.collapsed {
  width: 32px;
  height: 32px;
}

.overview-wrap.collapsed .overview-toggle {
  right: 0;
  top: 0;
}

:deep(.ol-overviewmap) {
  position: static;
  width: 100%;
  height: 100%;
  padding: 0;
  background: transparent;
  border: 0;
}

:deep(.ol-overviewmap-map) {
  width: 100%;
  height: 100%;
  margin: 0;
  border: 0;
}

:deep(.ol-overviewmap-box) {
  border: 2px solid #e85d3f;
}

:deep(.ol-overviewmap button) {
  display: none;
}
</style>
