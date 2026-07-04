import { queryPoisHttp } from '@/api/spatialQueryApi'
import { createMockSpatialQueryResult } from '@/mocks/mockSpatialQuery'
import { USE_MOCK } from './serviceConfig'

export const queryPois = payload => USE_MOCK
  ? Promise.resolve(createMockSpatialQueryResult(payload))
  : queryPoisHttp(payload)
