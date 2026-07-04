<script setup>
import { ref } from 'vue'
import { addLayer, removeLayersByGroup } from '@/map-core/layerManager'
import { BASE_MAP_OPTIONS, createBaseMapLayers } from '@/map-core/baseMapFactory'
import { useMapStore } from '@/stores/mapStore'
import ToolbarButton from './ToolbarButton.vue'
import ToolPopover from './ToolPopover.vue'

defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['toggle'])
const mapStore = useMapStore()
const activeBase = ref('standard')

const switchBaseMap = key => {
  const map = mapStore.map
  if (!map) return
  activeBase.value = key
  mapStore.setActiveBaseMap(key)
  removeLayersByGroup(map, 'base_map')
  createBaseMapLayers(key).forEach(layer => addLayer(map, layer))
}
</script>

<template>
  <div class="tool-wrap">
    <ToolbarButton label="图层" :active="open" @click="emit('toggle')" />
    <ToolPopover v-if="open">
      <div class="layer-panel">
        <div class="base-row primary">
          <button
            v-for="item in BASE_MAP_OPTIONS.slice(0, 2)"
            :key="item.key"
            :class="{ active: activeBase === item.key }"
            type="button"
            @click="switchBaseMap(item.key)"
          >{{ item.title }}</button>
        </div>
        <div class="base-row">
          <button
            v-for="item in BASE_MAP_OPTIONS.slice(2)"
            :key="item.key"
            :class="{ active: activeBase === item.key }"
            type="button"
            @click="switchBaseMap(item.key)"
          >{{ item.title }}</button>
        </div>
      </div>
    </ToolPopover>
  </div>
</template>

<style scoped>
.tool-wrap { position: relative; }
.layer-panel { display: grid; gap: 10px; }
.base-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.base-row.primary { grid-template-columns: repeat(2, 1fr); }
button {
  height: 34px;
  color: #334155;
  cursor: pointer;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 7px;
}
button.active {
  color: #0f766e;
  font-weight: 700;
  background: #ecfdf5;
  border-color: rgba(15, 118, 110, 0.35);
}
</style>
