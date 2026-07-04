import httpClient from './httpClient'

export const getPoisHttp = params => httpClient.get('/api/pois', { params }).then(res => res.data)
export const getPoiDetailHttp = poiId => httpClient.get(`/api/pois/${poiId}/detail`).then(res => res.data)
