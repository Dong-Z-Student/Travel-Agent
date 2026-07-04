import { getRouteHttp, planRouteHttp } from '@/api/routeApi'
import { getMockRoute } from '@/mocks/mockRoutePlans'
import { USE_MOCK } from './serviceConfig'

export const getRoute = routeId => USE_MOCK ? Promise.resolve(getMockRoute(routeId)) : getRouteHttp(routeId)
export const planRoute = payload => USE_MOCK ? Promise.resolve(getMockRoute(payload?.route_id)) : planRouteHttp(payload)
