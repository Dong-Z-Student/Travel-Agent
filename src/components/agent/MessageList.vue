<script setup>
import { nextTick, ref, watch } from 'vue'

const props = defineProps({
  messages: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})

const listRef = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (!listRef.value) return
  listRef.value.scrollTop = listRef.value.scrollHeight
}

watch(() => [props.messages.length, props.loading], scrollToBottom, { immediate: true })
</script>

<template>
  <div ref="listRef" class="message-list">
    <div
      v-for="message in messages"
      :key="message.id"
      class="message-row"
      :class="message.role"
    >
      <div class="message-bubble">{{ message.content }}</div>
    </div>
    <div v-if="loading" class="message-row assistant">
      <div class="message-bubble typing">正在思考...</div>
    </div>
  </div>
</template>

<style scoped>
.message-list {
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 10px;
  min-height: 0;
  padding: 4px 2px;
  overflow-y: auto;
}

.message-row {
  display: flex;
}

.message-row.user {
  justify-content: flex-end;
}

.message-bubble {
  max-width: 86%;
  padding: 9px 11px;
  color: #1f2937;
  font-size: 13px;
  line-height: 1.5;
  white-space: pre-wrap;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
}

.message-row.user .message-bubble {
  color: #fff;
  background: #0f766e;
  border-color: rgba(15, 118, 110, 0.28);
}

.typing {
  color: #64748b;
}
</style>
