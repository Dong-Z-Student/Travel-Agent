import httpClient from './httpClient'

export const getRouteHttp = routeId => httpClient.get(`/api/routes/${routeId}`).then(res => res.data)
export const planRouteHttp = payload => httpClient.post('/api/routes/plan', payload).then(res => res.data)
