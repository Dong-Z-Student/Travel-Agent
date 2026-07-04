import GeoJSON from 'ol/format/GeoJSON.js'
import { fromLonLat, toLonLat, transform } from 'ol/proj.js'
import Feature from 'ol/Feature.js'
import LineString from 'ol/geom/LineString.js'

const geoJSONFormat = new GeoJSON()
const PI = Math.PI
const X_PI = PI * 3000.0 / 180.0
const EARTH_RADIUS = 6378245.0
const GCJ_EE = 0.00669342162296594323
const BAIDU_LL_BAND = [75, 60, 45, 30, 15, 0]
const BAIDU_LL2MC = [
  [-0.0015702102444, 111320.7020616939, 1704480524535203, -10338987376042340, 26112667856603880, -35149669176653700, 26595700718403920, -10725012454188240, 1800819912950474, 82.5],
  [0.0008277824516172526, 111320.7020463578, 647795574.6671607, -4082003173.641316, 10774905663.51142, -15171875531.51559, 12053065338.62167, -5124939663.577472, 913311935.9512032, 67.5],
  [0.00337398766765, 111320.7020202162, 4481351.045890365, -23393751.19931662, 79682215.47186455, -115964993.2797253, 97236711.15602145, -43661946.33752821, 8477230.501135234, 52.5],
  [0.00220636496208, 111320.7020209128, 51751.86112841131, 3796837.749470245, 992013.7397791013, -1221952.21711287, 1340652.697009075, -620943.6990984312, 144416.9293806241, 37.5],
  [-0.0003441963504368392, 111320.7020576856, 278.2353980772752, 2485758.690035394, 6070.750963243378, 54821.18345352118, 9540.606633304236, -2710.55326746645, 1405.483844121726, 22.5],
  [-0.0003218135878613132, 111320.7020701615, 0.00369383431289, 823725.6402795718, 0.46104986909093, 2351.343141331292, 1.58060784298199, 8.77738589078284, 0.37238884252424, 7.45]
]

export const BASE_MAP_DATUM = {
  standard: 'wgs84',
  satellite: 'wgs84',
  osm: 'wgs84',
  gaode: 'gcj02',
  baidu: 'bd09'
}

const outOfChina = ([lon, lat]) => lon < 72.004 || lon > 137.8347 || lat < 0.8293 || lat > 55.8271

const transformLat = (x, y) => {
  let ret = -100.0 + 2.0 * x + 3.0 * y + 0.2 * y * y + 0.1 * x * y + 0.2 * Math.sqrt(Math.abs(x))
  ret += (20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0 / 3.0
  ret += (20.0 * Math.sin(y * PI) + 40.0 * Math.sin(y / 3.0 * PI)) * 2.0 / 3.0
  ret += (160.0 * Math.sin(y / 12.0 * PI) + 320 * Math.sin(y * PI / 30.0)) * 2.0 / 3.0
  return ret
}

const transformLon = (x, y) => {
  let ret = 300.0 + x + 2.0 * y + 0.1 * x * x + 0.1 * x * y + 0.1 * Math.sqrt(Math.abs(x))
  ret += (20.0 * Math.sin(6.0 * x * PI) + 20.0 * Math.sin(2.0 * x * PI)) * 2.0 / 3.0
  ret += (20.0 * Math.sin(x * PI) + 40.0 * Math.sin(x / 3.0 * PI)) * 2.0 / 3.0
  ret += (150.0 * Math.sin(x / 12.0 * PI) + 300.0 * Math.sin(x / 30.0 * PI)) * 2.0 / 3.0
  return ret
}

export const wgs84ToGcj02 = lonLat => {
  if (!Array.isArray(lonLat) || lonLat.length < 2 || outOfChina(lonLat)) return lonLat
  const [lon, lat] = lonLat
  let dLat = transformLat(lon - 105.0, lat - 35.0)
  let dLon = transformLon(lon - 105.0, lat - 35.0)
  const radLat = lat / 180.0 * PI
  let magic = Math.sin(radLat)
  magic = 1 - GCJ_EE * magic * magic
  const sqrtMagic = Math.sqrt(magic)
  dLat = (dLat * 180.0) / ((EARTH_RADIUS * (1 - GCJ_EE)) / (magic * sqrtMagic) * PI)
  dLon = (dLon * 180.0) / (EARTH_RADIUS / sqrtMagic * Math.cos(radLat) * PI)
  return [lon + dLon, lat + dLat]
}

export const gcj02ToBd09 = lonLat => {
  const [lon, lat] = lonLat
  const z = Math.sqrt(lon * lon + lat * lat) + 0.00002 * Math.sin(lat * X_PI)
  const theta = Math.atan2(lat, lon) + 0.000003 * Math.cos(lon * X_PI)
  return [z * Math.cos(theta) + 0.0065, z * Math.sin(theta) + 0.006]
}

export const wgs84ToBd09 = lonLat => gcj02ToBd09(wgs84ToGcj02(lonLat))

const getLoop = (value, min, max) => {
  let next = value
  while (next > max) next -= max - min
  while (next < min) next += max - min
  return next
}

const getRange = (value, min, max) => Math.max(min, Math.min(max, value))

const convertor = ([lon, lat], coefficients) => {
  const x = coefficients[0] + coefficients[1] * Math.abs(lon)
  const c = Math.abs(lat) / coefficients[9]
  let y = coefficients[2]
  y += coefficients[3] * c
  y += coefficients[4] * c * c
  y += coefficients[5] * c * c * c
  y += coefficients[6] * c * c * c * c
  y += coefficients[7] * c * c * c * c * c
  y += coefficients[8] * c * c * c * c * c * c
  return [x * (lon < 0 ? -1 : 1), y * (lat < 0 ? -1 : 1)]
}

export const bd09ToBdMercator = lonLat => {
  const lon = getLoop(lonLat[0], -180, 180)
  const lat = getRange(lonLat[1], -74, 74)
  const absLat = Math.abs(lat)
  const coefficients = BAIDU_LL2MC[BAIDU_LL_BAND.findIndex(band => absLat >= band)] || BAIDU_LL2MC[BAIDU_LL2MC.length - 1]
  return convertor([lon, lat], coefficients)
}

export const getBaseMapDatum = baseMapKey => BASE_MAP_DATUM[baseMapKey] || BASE_MAP_DATUM.standard

export const lonLatToBaseMapLonLat = (lonLat, baseMapKey = 'standard') => {
  const datum = getBaseMapDatum(baseMapKey)
  if (datum === 'gcj02') return wgs84ToGcj02(lonLat)
  if (datum === 'bd09') return wgs84ToBd09(lonLat)
  return lonLat
}

export const getActiveBaseMapKey = (map, fallback = 'standard') => map?.get?.('active_base_map') || fallback

export const lonLatToMapCoord = (lonLat, baseMapKey = 'standard') => {
  if (getBaseMapDatum(baseMapKey) === 'bd09') return bd09ToBdMercator(wgs84ToBd09(lonLat))
  return fromLonLat(lonLatToBaseMapLonLat(lonLat, baseMapKey), 'EPSG:3857')
}

export const lonLatsToMapCoords = (lonLats, baseMapKey = 'standard') => lonLats.map(lonLat => lonLatToMapCoord(lonLat, baseMapKey))

export const mapCoordToLonLat = coord => toLonLat(coord, 'EPSG:3857')

export const featureToGeoJSON4326 = feature => geoJSONFormat.writeFeatureObject(feature, {
  dataProjection: 'EPSG:4326',
  featureProjection: 'EPSG:3857'
})

export const geoJSON4326ToFeature = geojson => geoJSONFormat.readFeature(geojson, {
  dataProjection: 'EPSG:4326',
  featureProjection: 'EPSG:3857'
})

export const geoJSON4326ToFeatures = geojson => geoJSONFormat.readFeatures(geojson, {
  dataProjection: 'EPSG:4326',
  featureProjection: 'EPSG:3857'
})

export const lineStringFromBezierSamples = samples => {
  const coords = samples.map(coord => {
    if (Math.abs(coord[0]) <= 180 && Math.abs(coord[1]) <= 90) return lonLatToMapCoord(coord)
    return coord
  })
  return new Feature(new LineString(coords))
}

export const transformCoord = (coord, source = 'EPSG:4326', target = 'EPSG:3857') => transform(coord, source, target)
