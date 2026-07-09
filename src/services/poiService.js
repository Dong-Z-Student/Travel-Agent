import { getPoiDetailHttp, getPoisHttp } from '@/api/poiApi'

export const getPois = params => getPoisHttp(params)

export const getPoiDetail = poiId => getPoiDetailHttp(poiId)
