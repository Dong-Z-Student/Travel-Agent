import { sendAgentMessageHttp } from '@/api/agentApi'

export const sendAgentMessage = payload => sendAgentMessageHttp(payload)
