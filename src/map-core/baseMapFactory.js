import TileLayer from 'ol/layer/Tile.js'
import XYZ from 'ol/source/XYZ.js'
import OSM from 'ol/source/OSM.js'
import TileImage from 'ol/source/TileImage.js'
import TileGrid from 'ol/tilegrid/TileGrid.js'
import { MAP_CONFIG } from '@/config/mapConfig'
import { getBaseMapDatum } from './projectionUtils'

const setMeta = (layer, meta) => {
  layer.set('layer_id', meta.layer_id)
  layer.set('group', 'base_map')
  layer.set('title', meta.title)
  layer.set('visible', meta.visible !== false)
  if (meta.base_map_key) layer.set('base_map_key', meta.base_map_key)
  if (meta.datum) layer.set('datum', meta.datum)
  layer.setVisible(meta.visible !== false)
  layer.setZIndex(-100 + (meta.order || 0))
  return layer
}

const tiandituUrl = layer => {
  const key = MAP_CONFIG.tiandituKey
  return `http://t{0-7}.tianditu.gov.cn/${layer}_c/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=${layer}&STYLE=default&TILEMATRIXSET=c&FORMAT=tiles&TILEMATRIX={z}&TILEROW={y}&TILECOL={x}&tk=${key}`
}

const createTianditu = (layer, title, layerId, order = 0) => setMeta(new TileLayer({
  source: new XYZ({ projection: 'EPSG:4326', url: tiandituUrl(layer), crossOrigin: 'anonymous' })
}), { layer_id: layerId, title, order, base_map_key: layerId.includes('img') || layerId.includes('cia') ? 'satellite' : 'standard', datum: getBaseMapDatum(layerId.includes('img') || layerId.includes('cia') ? 'satellite' : 'standard') })

const createGaode = () => setMeta(new TileLayer({
  source: new XYZ({ url: 'http://webrd0{1-4}.is.autonavi.com/appmaptile?lang=zh_cn&size=1&scl=1&style=8&lstyle=7&x={x}&y={y}&z={z}', crossOrigin: 'anonymous' })
}), { layer_id: 'base_gaode', title: '高德地图', base_map_key: 'gaode', datum: getBaseMapDatum('gaode') })

const createBaidu = () => {
  const resolutions = []
  for (let i = 0; i < 19; i++) resolutions.push(Math.pow(2, 18 - i))
  const tileGrid = new TileGrid({ origin: [0, 0], resolutions })
  const url = 'http://online{0-3}.map.bdimg.com/onlinelabel/?qt=tile&x={x}&y={y}&z={z}&styles=pl&udt=20191119&scaler=1&p=1'

  return setMeta(new TileLayer({
    source: new TileImage({
      projection: 'EPSG:3857',
      tileGrid,
      crossOrigin: 'anonymous',
      tileUrlFunction(tileCoord) {
        if (!tileCoord) return ''
        let tempUrl = url
        tempUrl = tempUrl.replace('{x}', tileCoord[1] < 0 ? `M${-tileCoord[1]}` : tileCoord[1])
        tempUrl = tempUrl.replace('{y}', tileCoord[2] < 0 ? `M${tileCoord[2] + 1}` : -(tileCoord[2] + 1))
        tempUrl = tempUrl.replace('{z}', tileCoord[0])
        const match = /\{(\d+)-(\d+)\}/.exec(tempUrl)
        if (match) {
          const delta = Number(match[2]) - Number(match[1])
          const num = Math.round(Math.random() * delta + Number(match[1]))
          tempUrl = tempUrl.replace(match[0], String(num))
        }
        return tempUrl
      }
    })
  }), { layer_id: 'base_baidu', title: '百度地图', base_map_key: 'baidu', datum: getBaseMapDatum('baidu') })
}

const createOsm = () => setMeta(new TileLayer({ source: new OSM({ crossOrigin: 'anonymous' }) }), { layer_id: 'base_osm', title: 'OSM', base_map_key: 'osm', datum: getBaseMapDatum('osm') })

export const BASE_MAP_OPTIONS = [
  { key: 'standard', title: '标准地图' },
  { key: 'satellite', title: '卫星地图' },
  { key: 'gaode', title: '高德' },
  { key: 'baidu', title: '百度' },
  { key: 'osm', title: 'OSM' }
]

export const createBaseMapLayers = key => {
  if (key === 'standard') return MAP_CONFIG.tiandituKey ? [createTianditu('vec', '标准地图', 'base_tianditu_vec', 0), createTianditu('cva', '标准地图注记', 'base_tianditu_cva', 1)] : [createOsm()]
  if (key === 'satellite') return MAP_CONFIG.tiandituKey ? [createTianditu('img', '卫星地图', 'base_tianditu_img', 0), createTianditu('cia', '卫星地图注记', 'base_tianditu_cia', 1)] : [createOsm()]
  if (key === 'gaode') return [createGaode()]
  if (key === 'baidu') return [createBaidu()]
  return [createOsm()]
}
