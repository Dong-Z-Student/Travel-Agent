<script setup>
import { ref } from 'vue'
import { useMapStore } from '@/stores/mapStore'
import ToolbarButton from './ToolbarButton.vue'

const emit = defineEmits(['click-tool'])
const mapStore = useMapStore()
const night = ref(false)

const applyMode = () => {
  const viewport = mapStore.map?.getViewport?.()
  if (!viewport) return
  viewport.classList.toggle('night-map-mode', night.value)
}

const toggleMode = () => {
  emit('click-tool')
  night.value = !night.value
  applyMode()
}
</script>

<template>
  <ToolbarButton :label="night ? '夜间' : '日间'" :active="night" @click="toggleMode" />
</template>

<style>
.night-map-mode .ol-layer canvas {
  filter: invert(0.88) hue-rotate(175deg) saturate(0.78) brightness(0.82) contrast(1.05);
}
</style>
