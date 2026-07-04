<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import FullScreen from 'ol/control/FullScreen.js'
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()
const fullscreenTarget = ref(null)
let fullscreenControl = null

const mountFullscreen = map => {
  if (!map || fullscreenControl) return

  fullscreenControl = new FullScreen({
    target: fullscreenTarget.value,
    source: document.querySelector('.travel-map-layout') || map.getTargetElement(),
    label: '⛶',
    labelActive: '⤢',
    tipLabel: '全屏'
  })

  map.addControl(fullscreenControl)
}

const cleanupFullscreen = () => {
  const map = mapStore.map
  if (map && fullscreenControl) map.removeControl(fullscreenControl)
  fullscreenControl = null
}

watch(() => mapStore.ready, ready => {
  if (ready && mapStore.map) mountFullscreen(mapStore.map)
}, { immediate: true })

onBeforeUnmount(cleanupFullscreen)
</script>

<template>
  <div ref="fullscreenTarget" class="fullscreen-control-host"></div>
</template>

<style scoped>
.fullscreen-control-host {
  pointer-events: auto;
}

:deep(.ol-full-screen) {
  position: static;
}

:deep(.ol-full-screen button) {
  width: 42px;
  height: 38px;
  padding: 0;
  color: #111827;
  font-size: 20px;
  line-height: 1;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.14);
}

:deep(.ol-full-screen button:hover) {
  background: #f8fafc;
}
</style>

