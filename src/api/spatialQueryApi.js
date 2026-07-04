import httpClient from './httpClient'

export const queryPoisHttp = payload => httpClient.post('/api/spatial-query/pois', payload).then(res => res.data)
