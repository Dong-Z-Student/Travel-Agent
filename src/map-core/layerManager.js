import { useLayerStore } from '@/stores/layerStore'

const getLayerMeta = layer => ({
  layer_id: layer.get('layer_id'),
  group: layer.get('group'),
  title: layer.get('title'),
  visible: layer.getVisible()
})

const applyLayerMeta = (layer, options = {}) => {
  const layerId = options.layer_id || layer.get('layer_id')
  const group = options.group || layer.get('group')
  const title = options.title || layer.get('title') || layerId
  const visible = options.visible ?? layer.getVisible() ?? true

  if (!layerId) throw new Error('Layer must have layer_id')
  if (!group) throw new Error(`Layer ${layerId} must have group`)

  layer.set('layer_id', layerId)
  layer.set('group', group)
  layer.set('title', title)
  layer.set('visible', visible)
  layer.setVisible(visible)
}

const syncStore = map => {
  const layerStore = useLayerStore()
  const layers = map.getLayers().getArray().map(getLayerMeta).filter(item => item.layer_id)
  layerStore.setLayers(layers)
}

export const registerExistingLayers = map => {
  map.getLayers().getArray().forEach(layer => {
    if (layer.get('layer_id')) applyLayerMeta(layer)
  })
  syncStore(map)
}

export const addLayer = (map, layer, options = {}) => {
  applyLayerMeta(layer, options)
  removeLayerById(map, layer.get('layer_id'), { silent: true })
  map.addLayer(layer)
  syncStore(map)
  return layer
}

export const removeLayerById = (map, layerId, options = {}) => {
  const layer = getLayerById(map, layerId)
  if (layer) map.removeLayer(layer)
  if (!options.silent) syncStore(map)
  return layer
}

export const removeLayersByGroup = (map, group) => {
  const layers = map.getLayers().getArray().filter(layer => layer.get('group') === group)
  layers.forEach(layer => map.removeLayer(layer))
  syncStore(map)
  return layers
}

export const setLayerVisible = (map, layerId, visible) => {
  const layer = getLayerById(map, layerId)
  if (!layer) return null
  layer.setVisible(visible)
  layer.set('visible', visible)
  syncStore(map)
  return layer
}

export const replaceLayerById = (map, layerId, newLayer, options = {}) => {
  removeLayerById(map, layerId, { silent: true })
  return addLayer(map, newLayer, { ...options, layer_id: options.layer_id || layerId })
}

export const getLayerById = (map, layerId) => {
  return map.getLayers().getArray().find(layer => layer.get('layer_id') === layerId) || null
}

export const getLayersByGroup = (map, group) => {
  return map.getLayers().getArray().filter(layer => layer.get('group') === group)
}
