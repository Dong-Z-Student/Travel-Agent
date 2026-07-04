<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { toLonLat } from 'ol/proj.js'
import { unByKey } from 'ol/Observable.js'
import { useMapStore } from '@/stores/mapStore'

const mapStore = useMapStore()
const enabled = ref(false)
const text = ref('')
let moveKey = null

const format = coordinate => {
  const [lon, lat] = toLonLat(coordinate)
  return `${lon.toFixed(3)}, ${lat.toFixed(3)}`
}

const toggle = () => {
  const map = mapStore.map
  if (!map) return
  enabled.value = !enabled.value
  if (enabled.value) {
    moveKey = map.on('pointermove', event => { text.value = format(event.coordinate) })
  } else {
    if (moveKey) unByKey(moveKey)
    moveKey = null
    text.value = ''
  }
}

onBeforeUnmount(() => {
  if (moveKey) unByKey(moveKey)
})
</script>

<template>
  <div class="mouse-coordinate-tool">
    <button type="button" :class="{ active: enabled }" @click="toggle">鼠标坐标</button>
    <div v-if="enabled && text" class="coordinate-box">{{ text }}</div>
  </div>
</template>

<style scoped>
.mouse-coordinate-tool { display: grid; gap: 8px; }
button {
  height: 32px;
  cursor: pointer;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 7px;
}
button.active { color: #0f766e; font-weight: 700; background: #ecfdf5; }
.coordinate-box { padding: 6px 8px; font-size: 13px; color: #334155; background: #fff; border-radius: 6px; }
</style>
