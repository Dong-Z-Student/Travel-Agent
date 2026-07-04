import { getPoiDetailHttp, getPoisHttp } from '@/api/poiApi'
import { mockPois } from '@/mocks/mockPois'
import { mockPoiDetails } from '@/mocks/mockPoiDetails'
import { USE_MOCK } from './serviceConfig'

export const getPois = params => {
  if (!USE_MOCK) return getPoisHttp(params)

  const categories = params?.category_codes || []
  const pois = categories.length
    ? mockPois.filter(poi => categories.includes(poi.category_code))
    : mockPois

  return Promise.resolve({ pois })
}

export const getPoiDetail = poiId => {
  if (!USE_MOCK) return getPoiDetailHttp(poiId)

  const detail = mockPoiDetails[poiId]
  if (detail) return Promise.resolve(detail)

  const poi = mockPois.find(item => item.id === poiId)
  return Promise.resolve(poi ? {
    ...poi,
    profile: { short_intro_zh: poi.tags?.join(' / ') || poi.category_code },
    images: []
  } : null)
}
