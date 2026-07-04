<script setup>
import OverviewMiniMap from './OverviewMiniMap.vue'
import ScaleLineControl from './ScaleLineControl.vue'
import MapCopyright from './MapCopyright.vue'
</script>

<template>
  <section class="left-bottom-controls" aria-label="地图辅助信息">
    <OverviewMiniMap />
    <ScaleLineControl />
  </section>
  <MapCopyright />
</template>

<style scoped>
.left-bottom-controls {
  position: absolute;
  left: 16px;
  bottom: 16px;
  z-index: 5;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: flex-start;
  pointer-events: none;
}
</style>
