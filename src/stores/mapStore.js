import { defineStore } from 'pinia'

export const useMapStore = defineStore('map', {
  state: () => ({
    map: null,
    view: null,
    ready: false,
    activeBaseMap: 'standard'
  }),
  actions: {
    setMap(map) {
      this.map = map
      this.view = map?.getView?.() || null
      this.ready = Boolean(map)
      map?.set?.('active_base_map', this.activeBaseMap)
    },
    clearMap() {
      this.map = null
      this.view = null
      this.ready = false
    },
    getMap() {
      return this.map
    },
    setActiveBaseMap(key) {
      this.activeBaseMap = key
      this.map?.set?.('active_base_map', key)
    }
  }
})
