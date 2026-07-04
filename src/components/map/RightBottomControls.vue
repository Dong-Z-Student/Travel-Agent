<script setup>
import CompassControl from './CompassControl.vue'
import FullscreenControl from './FullscreenControl.vue'
import ResetViewControl from './ResetViewControl.vue'
import ZoomControlGroup from './ZoomControlGroup.vue'
</script>

<template>
  <section class="right-bottom-controls" aria-label="地图基础控制">
    <CompassControl />
    <ZoomControlGroup />
    <ResetViewControl />
    <FullscreenControl />
  </section>
</template>

<style scoped>
.right-bottom-controls {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 6;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  pointer-events: none;
}
</style>
