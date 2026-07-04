<script setup>
import { WUHAN_CENTER, WUHAN_DEFAULT_ZOOM } from '@/map-core/createMap'
import { lonLatToMapCoord } from '@/map-core/projectionUtils'
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()

const resetView = () => {
  const view = mapStore.view
  if (!view) return
  view.animate({
    center: lonLatToMapCoord(WUHAN_CENTER, mapStore.activeBaseMap),
    zoom: WUHAN_DEFAULT_ZOOM,
    rotation: 0,
    duration: 350
  })
}
</script>

<template>
  <button class="reset-view-control" type="button" title="复位到武汉默认视图" @click="resetView">⌂</button>
</template>

<style scoped>
.reset-view-control {
  width: 42px;
  height: 38px;
  padding: 0;
  color: #111827;
  font-size: 21px;
  line-height: 1;
  pointer-events: auto;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.14);
}

.reset-view-control:hover {
  background: #f8fafc;
}
</style>
