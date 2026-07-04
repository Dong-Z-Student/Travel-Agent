<script setup>
import { nextTick, onBeforeUnmount, ref } from 'vue'
import Map from 'ol/Map.js'
import { createBaseMapLayers } from '@/map-core/baseMapFactory'
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()
const active = ref(false)
const mapTargets = ref([])
let splitMaps = []

const setTargetRef = (el, index) => {
  if (el) mapTargets.value[index] = el
}

const openSplit = async () => {
  const mainMap = mapStore.map
  if (!mainMap) return
  active.value = true
  await nextTick()
  const view = mainMap.getView()
  const keys = ['standard', 'satellite', 'gaode', 'osm']
  splitMaps = keys.map((key, index) => new Map({
    target: mapTargets.value[index],
    view,
    layers: createBaseMapLayers(key),
    controls: []
  }))
}

const closeSplit = () => {
  splitMaps.forEach(map => map.setTarget(undefined))
  splitMaps = []
  active.value = false
  mapStore.map?.updateSize?.()
}

onBeforeUnmount(closeSplit)
</script>

<template>
  <button type="button" :class="{ active }" @click="openSplit">分屏</button>
  <Teleport to="body">
    <div v-if="active" class="split-overlay">
      <button class="exit-split" type="button" @click="closeSplit">退出分屏</button>
      <div class="split-grid">
        <div v-for="index in 4" :key="index" :ref="el => setTargetRef(el, index - 1)" class="split-map"></div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
button {
  height: 32px;
  cursor: pointer;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 7px;
}
button.active { color: #0f766e; font-weight: 700; background: #ecfdf5; }
.split-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: #eef2f5;
}
.split-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
  width: 100%;
  height: 100%;
  gap: 2px;
}
.split-map { min-width: 0; min-height: 0; background: #fff; }
.exit-split {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 2;
  width: auto;
  padding: 0 12px;
  background: #fff;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.16);
}
</style>
