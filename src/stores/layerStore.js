import { defineStore } from 'pinia'

export const useLayerStore = defineStore('layer', {
  state: () => ({
    layers: []
  }),
  getters: {
    visibleLayers: state => state.layers.filter(layer => layer.visible),
    layersByGroup: state => group => state.layers.filter(layer => layer.group === group),
    layerById: state => layerId => state.layers.find(layer => layer.layer_id === layerId) || null
  },
  actions: {
    setLayers(layers) {
      this.layers = layers.map(layer => ({ ...layer }))
    },
    setLayerVisible(layerId, visible) {
      const layer = this.layers.find(item => item.layer_id === layerId)
      if (layer) layer.visible = visible
    },
    removeLayer(layerId) {
      this.layers = this.layers.filter(layer => layer.layer_id !== layerId)
    }
  }
})
