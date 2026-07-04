import httpClient from './httpClient'

export const sendAgentMessageHttp = payload => httpClient.post('/api/agent/chat', payload).then(res => res.data)
