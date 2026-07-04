import { sendAgentMessageHttp } from '@/api/agentApi'
import { createMockAgentReply } from '@/mocks/mockAgentReplies'
import { USE_MOCK } from './serviceConfig'

const mockDelay = result => new Promise(resolve => {
  window.setTimeout(() => resolve(result), 450)
})

export const sendAgentMessage = payload => USE_MOCK
  ? mockDelay(createMockAgentReply(payload))
  : sendAgentMessageHttp(payload)
