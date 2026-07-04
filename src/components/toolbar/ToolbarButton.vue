<script setup>
defineProps({ active: Boolean, label: { type: String, required: true }, round: Boolean })
defineEmits(['click'])
</script>

<template>
  <button class="toolbar-button" :class="{ active, round }" type="button" @click="$emit('click')">
    <slot>{{ label }}</slot>
  </button>
</template>

<style scoped>
.toolbar-button {
  min-width: 54px;
  height: 38px;
  padding: 0 12px;
  color: #1f2937;
  font-size: 14px;
  white-space: nowrap;
  cursor: pointer;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.12);
}

.toolbar-button:hover,
.toolbar-button.active {
  color: #0f766e;
  background: #f8fafc;
  border-color: rgba(15, 118, 110, 0.26);
}

.toolbar-button.round {
  width: 38px;
  min-width: 38px;
  padding: 0;
  border-radius: 50%;
}
</style>
