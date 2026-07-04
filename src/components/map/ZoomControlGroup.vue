<script setup>
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()

const zoomBy = delta => {
  const view = mapStore.view
  if (!view) return
  const zoom = view.getZoom() || 0
  view.animate({ zoom: zoom + delta, duration: 180 })
}
</script>

<template>
  <div class="zoom-control-group" aria-label="地图缩放">
    <button type="button" title="放大" @click="zoomBy(1)">+</button>
    <button type="button" title="缩小" @click="zoomBy(-1)">−</button>
  </div>
</template>

<style scoped>
.zoom-control-group {
  display: grid;
  overflow: hidden;
  pointer-events: auto;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.14);
}

button {
  width: 42px;
  height: 38px;
  padding: 0;
  color: #111827;
  font-size: 24px;
  line-height: 1;
  cursor: pointer;
  background: transparent;
  border: 0;
}

button + button {
  border-top: 1px solid rgba(15, 23, 42, 0.10);
}

button:hover {
  background: #f8fafc;
}
</style>
