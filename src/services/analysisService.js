import { getPopulationHeatmapHttp } from '@/api/analysisApi'
import { mockPopulationHeatmap } from '@/mocks/mockPopulationHeatmap'
import { USE_MOCK } from './serviceConfig'

export const getPopulationHeatmap = params => USE_MOCK ? Promise.resolve(mockPopulationHeatmap) : getPopulationHeatmapHttp(params)
