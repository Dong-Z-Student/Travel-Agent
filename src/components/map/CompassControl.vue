<script setup>
import { onBeforeUnmount, ref, watch } from 'vue'
import { unByKey } from 'ol/Observable.js'
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()
const angle = ref(0)
let dragging = false

const radiansToDegrees = radians => radians * 180 / Math.PI
const degreesToRadians = degrees => degrees * Math.PI / 180

const normalizeDegrees = degrees => {
  let value = degrees % 360
  if (value > 180) value -= 360
  if (value < -180) value += 360
  return value
}

const syncFromMap = () => {
  const rotation = mapStore.view?.getRotation?.() || 0
  angle.value = normalizeDegrees(radiansToDegrees(rotation))
}

const setRotation = degrees => {
  if (!mapStore.view) return
  const normalized = normalizeDegrees(degrees)
  angle.value = normalized
  mapStore.view.setRotation(degreesToRadians(normalized))
}

const resetRotation = () => setRotation(0)

const updateFromPointer = event => {
  const target = event.currentTarget
  const rect = target.getBoundingClientRect()
  const centerX = rect.left + rect.width / 2
  const centerY = rect.top + rect.height / 2
  const dx = event.clientX - centerX
  const dy = event.clientY - centerY
  const degrees = Math.atan2(dx, -dy) * 180 / Math.PI
  setRotation(degrees)
}

const onPointerDown = event => {
  dragging = true
  event.currentTarget.setPointerCapture?.(event.pointerId)
  updateFromPointer(event)
}

const onPointerMove = event => {
  if (!dragging) return
  updateFromPointer(event)
}

const onPointerUp = event => {
  dragging = false
  event.currentTarget.releasePointerCapture?.(event.pointerId)
}

let rotationKey = null
watch(() => mapStore.ready, ready => {
  if (!ready || !mapStore.view) return
  syncFromMap()
  rotationKey = mapStore.view.on('change:rotation', syncFromMap)
}, { immediate: true })

onBeforeUnmount(() => {
  if (rotationKey) mapStore.view?.un?.('change:rotation', syncFromMap)
  rotationKey = null
})
</script>

<template>
  <button
    class="compass-control"
    type="button"
    title="拖动旋转地图，双击复位方向"
    @dblclick="resetRotation"
    @pointerdown="onPointerDown"
    @pointermove="onPointerMove"
    @pointerup="onPointerUp"
    @pointercancel="onPointerUp"
  >
    <span class="compass-dial" :style="{ transform: `rotate(${angle}deg)` }">
      <span class="needle north"></span>
      <span class="needle south"></span>
      <span class="north-label">N</span>
    </span>
  </button>
</template>

<style scoped>
.compass-control {
  width: 52px;
  height: 52px;
  padding: 0;
  pointer-events: auto;
  touch-action: none;
  cursor: grab;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 50%;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.14);
}

.compass-control:active {
  cursor: grabbing;
}

.compass-dial {
  position: relative;
  display: block;
  width: 100%;
  height: 100%;
  border-radius: 50%;
}

.needle {
  position: absolute;
  left: 50%;
  width: 0;
  height: 0;
  transform: translateX(-50%);
}

.needle.north {
  top: 8px;
  border-right: 7px solid transparent;
  border-bottom: 18px solid #e85d3f;
  border-left: 7px solid transparent;
}

.needle.south {
  bottom: 8px;
  border-top: 18px solid #64748b;
  border-right: 7px solid transparent;
  border-left: 7px solid transparent;
}

.north-label {
  position: absolute;
  top: 4px;
  left: 50%;
  color: #7f1d1d;
  font-size: 10px;
  font-weight: 700;
  line-height: 1;
  transform: translateX(-50%);
}
</style>

