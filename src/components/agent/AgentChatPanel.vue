<script setup>
import { ref } from 'vue'
import AgentToolMenu from './AgentToolMenu.vue'
import MessageList from './MessageList.vue'
import PreferenceChips from './PreferenceChips.vue'
import SuggestedQuestions from './SuggestedQuestions.vue'

defineProps({
  locked: { type: Boolean, default: false },
  input: { type: String, default: '' },
  loading: { type: Boolean, default: false },
  messages: { type: Array, default: () => [] },
  preferences: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:input', 'submit', 'close', 'toggle-lock', 'focus-input', 'blur-input', 'toggle-preference', 'tool-select'])
const toolMenuOpen = ref(false)

const handleToolSelect = tool => {
  toolMenuOpen.value = false
  emit('tool-select', tool)
}
</script>

<template>
  <section class="agent-chat-panel">
    <header class="agent-panel-header">
      <div>
        <strong>智游图策 Agent</strong>
        <span>武汉出行旅游规划</span>
      </div>
      <div class="header-actions">
        <button type="button" :class="{ active: locked }" @click="emit('toggle-lock')">{{ locked ? '已锁定' : '锁定' }}</button>
        <button type="button" @click="emit('close')">收起</button>
      </div>
    </header>

    <MessageList :messages="messages" :loading="loading" />

    <PreferenceChips :selected="preferences" @toggle="emit('toggle-preference', $event)" />
    <SuggestedQuestions @ask="emit('submit', $event)" />

    <form class="agent-input-row" @submit.prevent="emit('submit')">
      <div class="tool-anchor">
        <button class="plus-btn" type="button" @click="toolMenuOpen = !toolMenuOpen">+</button>
        <AgentToolMenu v-if="toolMenuOpen" @select="handleToolSelect" />
      </div>
      <input
        :value="input"
        type="text"
        placeholder="告诉我你想怎么玩武汉"
        @input="emit('update:input', $event.target.value)"
        @focus="emit('focus-input')"
        @blur="emit('blur-input')"
      />
      <button class="send-btn" type="submit" :disabled="loading || !input.trim()">发送</button>
    </form>
  </section>
</template>

<style scoped>
.agent-chat-panel {
  display: flex;
  flex-direction: column;
  width: 360px;
  height: min(560px, calc(100vh - 32px));
  gap: 10px;
  padding: 12px;
  color: #1f2937;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 10px;
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.18);
}

.agent-panel-header {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  align-items: flex-start;
}

.agent-panel-header strong,
.agent-panel-header span {
  display: block;
}

.agent-panel-header strong {
  font-size: 15px;
}

.agent-panel-header span {
  margin-top: 2px;
  color: #64748b;
  font-size: 12px;
}

.header-actions {
  display: flex;
  gap: 6px;
}

.header-actions button,
.send-btn,
.plus-btn {
  cursor: pointer;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 7px;
}

.header-actions button {
  height: 28px;
  padding: 0 9px;
  color: #475569;
}

.header-actions button.active {
  color: #0f766e;
  background: #ecfdf5;
}

.agent-input-row {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) 58px;
  gap: 8px;
  align-items: center;
}

.tool-anchor {
  position: relative;
}

.plus-btn,
.send-btn {
  height: 34px;
}

.plus-btn {
  width: 34px;
  color: #0f766e;
  font-size: 20px;
}

input {
  height: 34px;
  min-width: 0;
  padding: 0 10px;
  color: #1f2937;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  outline: none;
}

input:focus {
  border-color: rgba(15, 118, 110, 0.45);
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.10);
}

.send-btn {
  color: #fff;
  background: #0f766e;
  border-color: #0f766e;
}

.send-btn:disabled {
  color: #94a3b8;
  cursor: not-allowed;
  background: #f1f5f9;
  border-color: rgba(15, 23, 42, 0.08);
}
</style>
