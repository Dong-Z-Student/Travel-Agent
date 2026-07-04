<script setup>
import { onBeforeUnmount, ref } from 'vue'
import { storeToRefs } from 'pinia'
import { sendAgentMessage } from '@/services/agentService'
import { createMapCommandExecutor } from '@/map-core/mapCommandExecutor'
import { startAgentSpatialQueryTool } from '@/map-tools/agentSpatialQueryTool'
import { useAgentStore } from '@/stores/agentStore'
import { useMapStore } from '@/stores/mapStore'
import AgentChatPanel from './AgentChatPanel.vue'

const agentStore = useAgentStore()
const mapStore = useMapStore()
const { input, loading, messages } = storeToRefs(agentStore)
const expanded = ref(false)
const locked = ref(false)
const inputFocused = ref(false)
const preferences = ref(['轻松', '地铁优先'])
let stopSpatialTool = null

const expand = () => {
  expanded.value = true
}

const collapse = () => {
  if (locked.value || loading.value || inputFocused.value) return
  expanded.value = false
}

const closePanel = () => {
  expanded.value = false
}

const toggleLock = () => {
  locked.value = !locked.value
}

const togglePreference = chip => {
  preferences.value = preferences.value.includes(chip)
    ? preferences.value.filter(item => item !== chip)
    : [...preferences.value, chip]
}

const executeMapCommands = commands => {
  if (!commands?.length || !mapStore.map) return
  createMapCommandExecutor({ map: mapStore.map }).executeMany(commands)
}

const submitMessage = async value => {
  const content = typeof value === 'string' ? value : input.value
  const message = content.trim()
  if (!message || loading.value) return

  expand()
  agentStore.addMessage({ role: 'user', content: message })
  agentStore.setInput('')
  agentStore.setLoading(true)

  try {
    const response = await sendAgentMessage({
      conversation_id: agentStore.conversationId,
      message,
      preferences: preferences.value,
      context: {
        ...(agentStore.latestSpatialContext || {}),
        trip_state: agentStore.tripState
      }
    })
    executeMapCommands(response.map_commands)
    agentStore.setAgentResponse(response)
  } catch (error) {
    agentStore.addMessage({ role: 'assistant', content: '当前 Agent 服务暂不可用，请稍后再试。' })
    console.error('[AgentChatEntry] send message failed', error)
  } finally {
    agentStore.setLoading(false)
  }
}

const handleToolSelect = tool => {
  if (!mapStore.map) return
  expand()
  if (stopSpatialTool) stopSpatialTool()
  stopSpatialTool = startAgentSpatialQueryTool({
    map: mapStore.map,
    tool,
    onMessage: content => agentStore.addMessage({ role: 'assistant', content }),
    onContext: context => agentStore.setSpatialContext(context),
    onComplete: () => {
      stopSpatialTool = null
    }
  })
}

onBeforeUnmount(() => {
  if (stopSpatialTool) stopSpatialTool()
})
</script>

<template>
  <div class="agent-chat-entry" @mouseleave="collapse">
    <form v-if="!expanded" class="agent-mini-bar" @submit.prevent="submitMessage">
      <button type="button" class="agent-dot" @click="expand">AI</button>
      <input
        v-model="input"
        type="text"
        placeholder="问问武汉怎么玩"
        @focus="expand"
      />
      <button type="submit" :disabled="loading || !input.trim()">发送</button>
    </form>

    <AgentChatPanel
      v-else
      v-model:input="input"
      :locked="locked"
      :loading="loading"
      :messages="messages"
      :preferences="preferences"
      @submit="submitMessage"
      @close="closePanel"
      @toggle-lock="toggleLock"
      @focus-input="inputFocused = true"
      @blur-input="inputFocused = false"
      @toggle-preference="togglePreference"
      @tool-select="handleToolSelect"
    />
  </div>
</template>

<style scoped>
.agent-chat-entry {
  position: absolute;
  left: 16px;
  top: 16px;
  z-index: 9;
  pointer-events: auto;
}

.agent-mini-bar {
  display: grid;
  grid-template-columns: 38px minmax(0, 260px) 58px;
  gap: 8px;
  align-items: center;
  padding: 8px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.16);
}

.agent-dot,
.agent-mini-bar button {
  height: 34px;
  cursor: pointer;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
}

.agent-dot {
  color: #fff;
  font-weight: 800;
  background: #0f766e;
  border-color: #0f766e;
}

.agent-mini-bar input {
  height: 34px;
  min-width: 0;
  padding: 0 10px;
  color: #1f2937;
  background: #f8fafc;
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  outline: none;
}

.agent-mini-bar input:focus {
  border-color: rgba(15, 118, 110, 0.45);
}

.agent-mini-bar button[type="submit"] {
  color: #0f766e;
  font-weight: 700;
  background: #ecfdf5;
}

.agent-mini-bar button[type="submit"]:disabled {
  color: #94a3b8;
  cursor: not-allowed;
  background: #f1f5f9;
}
</style>
