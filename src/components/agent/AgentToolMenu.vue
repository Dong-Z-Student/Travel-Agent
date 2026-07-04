<script setup>
const emit = defineEmits(['select'])

const tools = [
  { key: 'point_nearby', label: '点查询附近 POI' },
  { key: 'line_nearby', label: '线查询附近 POI' },
  { key: 'bezier_nearby', label: '贝塞尔查询附近 POI' },
  { key: 'polygon_inside', label: '面内 POI 查询' }
]
</script>

<template>
  <div class="agent-tool-menu">
    <button
      v-for="tool in tools"
      :key="tool.key"
      type="button"
      @click="emit('select', tool)"
    >{{ tool.label }}</button>
  </div>
</template>

<style scoped>
.agent-tool-menu {
  position: absolute;
  left: 0;
  bottom: 42px;
  z-index: 2;
  display: grid;
  width: 210px;
  gap: 6px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.98);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.16);
}

button {
  height: 32px;
  padding: 0 10px;
  color: #334155;
  text-align: left;
  cursor: pointer;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 7px;
}

button:hover {
  color: #0f766e;
  background: #ecfdf5;
}
</style>
