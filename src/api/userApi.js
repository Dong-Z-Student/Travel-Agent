import httpClient from './httpClient'

export const getMeHttp = () => httpClient.get('/api/users/me').then(res => res.data)
export const listPreferencesHttp = () => httpClient.get('/api/users/me/preferences').then(res => res.data)
export const createPreferenceHttp = payload => httpClient.post('/api/users/me/preferences', payload).then(res => res.data)
export const deletePreferenceHttp = preferenceId => httpClient.delete(`/api/users/me/preferences/${preferenceId}`).then(res => res.data)
