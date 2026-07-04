<script setup>
defineProps({
  selected: { type: Array, default: () => [] }
})

const emit = defineEmits(['toggle'])

const chips = ['轻松', '亲子', '夜景', '人少', '地铁优先']
</script>

<template>
  <div class="preference-chips" aria-label="偏好选项">
    <button
      v-for="chip in chips"
      :key="chip"
      type="button"
      :class="{ active: selected.includes(chip) }"
      @click="emit('toggle', chip)"
    >{{ chip }}</button>
  </div>
</template>

<style scoped>
.preference-chips {
  display: flex;
  gap: 6px;
  overflow-x: auto;
}

button {
  height: 28px;
  padding: 0 10px;
  color: #475569;
  white-space: nowrap;
  cursor: pointer;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 999px;
}

button.active {
  color: #0f766e;
  font-weight: 700;
  background: #ecfdf5;
  border-color: rgba(15, 118, 110, 0.32);
}
</style>
