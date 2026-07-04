<script setup>
import LayerToolButton from './LayerToolButton.vue'
import { ref } from 'vue'
import MeasurementToolButton from './MeasurementToolButton.vue'
import AnalysisToolButton from './AnalysisToolButton.vue'
import DayNightToolButton from './DayNightToolButton.vue'
import MoreToolButton from './MoreToolButton.vue'
import UserEntry from '@/components/auth/UserEntry.vue'

const activePanel = ref('')

const togglePanel = panel => {
  activePanel.value = activePanel.value === panel ? '' : panel
}

const closePanels = () => {
  activePanel.value = ''
}
</script>

<template>
  <section class="top-right-toolbar" aria-label="地图业务工具">
    <LayerToolButton :open="activePanel === 'layer'" @toggle="togglePanel('layer')" />
    <MeasurementToolButton mode="distance" label="测距" @click-tool="closePanels" />
    <MeasurementToolButton mode="area" label="测面积" @click-tool="closePanels" />
    <AnalysisToolButton :open="activePanel === 'analysis'" @toggle="togglePanel('analysis')" />
    <DayNightToolButton @click-tool="closePanels" />
    <MoreToolButton :open="activePanel === 'more'" @toggle="togglePanel('more')" />
    <UserEntry @click-tool="closePanels" />
  </section>
</template>

<style scoped>
.top-right-toolbar {
  position: absolute;
  top: 16px;
  right: 64px;
  z-index: 8;
  display: flex;
  gap: 8px;
  align-items: flex-start;
}
</style>
