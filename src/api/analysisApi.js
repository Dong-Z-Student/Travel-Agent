import httpClient from './httpClient'

export const getPopulationHeatmapHttp = params => httpClient.get('/api/analysis/population-heatmap', { params }).then(res => res.data)
