<script setup>
import ToolbarButton from './ToolbarButton.vue'
import ToolPopover from './ToolPopover.vue'
import MouseCoordinateToggle from './MouseCoordinateToggle.vue'
import SplitScreenToggle from './SplitScreenToggle.vue'
import SwipeCompareToggle from './SwipeCompareToggle.vue'

defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['toggle'])
</script>

<template>
  <div class="tool-wrap">
    <ToolbarButton label="更多" :active="open" @click="emit('toggle')" />
    <ToolPopover v-if="open">
      <div class="more-panel">
        <MouseCoordinateToggle />
        <SplitScreenToggle />
        <SwipeCompareToggle />
      </div>
    </ToolPopover>
  </div>
</template>

<style scoped>
.tool-wrap { position: relative; }
.more-panel { display: grid; gap: 8px; }
</style>
