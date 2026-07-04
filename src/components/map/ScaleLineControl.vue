<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import ScaleLine from 'ol/control/ScaleLine.js'
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()
const scaleTarget = ref(null)
let scaleControl = null

const mountScaleLine = map => {
  if (!map || scaleControl) return

  scaleControl = new ScaleLine({
    target: scaleTarget.value,
    bar: false,
    units: 'metric',
    className: 'travel-scale-line'
  })

  map.addControl(scaleControl)
}

const cleanupScaleLine = () => {
  const map = mapStore.map
  if (map && scaleControl) map.removeControl(scaleControl)
  scaleControl = null
}

watch(() => mapStore.ready, ready => {
  if (ready && mapStore.map) mountScaleLine(mapStore.map)
}, { immediate: true })

onBeforeUnmount(cleanupScaleLine)
</script>

<template>
  <div class="scale-row">
    <div ref="scaleTarget" class="scale-shell"></div>
  </div>
</template>

<style scoped>
.scale-row {
  min-width: 96px;
  min-height: 26px;
  padding: 4px 8px 5px;
  pointer-events: auto;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 7px;
  box-shadow: 0 5px 14px rgba(15, 23, 42, 0.10);
}

.scale-shell {
  min-width: 84px;
  min-height: 17px;
}

:deep(.travel-scale-line) {
  position: static;
  padding: 0;
  background: transparent;
}

:deep(.travel-scale-line-inner) {
  height: 14px;
  padding: 0 4px;
  color: #111827;
  font-size: 11px;
  line-height: 13px;
  text-align: center;
  border-color: #111827;
  border-style: solid;
  border-width: 0 1px 2px;
}
</style>
