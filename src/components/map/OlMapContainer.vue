<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { createMap } from '@/map-core/createMap'
import { registerExistingLayers } from '@/map-core/layerManager'
import { useMapStore } from '@/stores/mapStore'

const mapTarget = ref(null)
const mapStore = useMapStore()
let map = null

onMounted(() => {
  map = createMap(mapTarget.value)
  registerExistingLayers(map)
  mapStore.setMap(map)
})

onBeforeUnmount(() => {
  if (map) {
    map.setTarget(undefined)
    map = null
  }
  mapStore.clearMap()
})
</script>

<template>
  <div ref="mapTarget" class="ol-map-container"></div>
</template>

<style scoped>
.ol-map-container {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
</style>
