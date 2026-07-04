import { defineStore } from 'pinia'

const createWelcomeMessage = () => ({
  id: 'agent_welcome',
  role: 'assistant',
  content: '你好，我可以帮你规划武汉旅行路线，也可以结合景点、酒店和地铁站给出建议。',
  created_at: Date.now()
})

export const useAgentStore = defineStore('agent', {
  state: () => ({
    conversationId: null,
    input: '',
    loading: false,
    messages: [createWelcomeMessage()],
    latestSpatialContext: null,
    tripState: null,
    cards: []
  }),
  actions: {
    setInput(value) {
      this.input = value
    },
    setLoading(value) {
      this.loading = value
    },
    addMessage(message) {
      this.messages.push({
        id: message.id || `msg_${Date.now()}_${Math.random().toString(16).slice(2)}`,
        created_at: message.created_at || Date.now(),
        ...message
      })
    },
    setAgentResponse(response = {}) {
      if (response.conversation_id) this.conversationId = response.conversation_id
      if (response.trip_state) this.tripState = response.trip_state
      this.cards = response.cards || []
      if (response.reply) {
        this.addMessage({ role: 'assistant', content: response.reply })
      }
    },
    setSpatialContext(context) {
      this.latestSpatialContext = context
    },
    resetConversation() {
      this.input = ''
      this.loading = false
      this.messages = [createWelcomeMessage()]
      this.latestSpatialContext = null
      this.tripState = null
      this.cards = []
      this.conversationId = null
    }
  }
})
