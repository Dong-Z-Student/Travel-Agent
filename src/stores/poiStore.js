import { defineStore } from 'pinia'

export const usePoiStore = defineStore('poi', {
  state: () => ({
    pois: [],
    categories: ['scenic_spot', 'hotel', 'metro_station'],
    selectedPoi: null,
    detailCache: {}
  }),
  getters: {
    poisByCategory: state => category => state.pois.filter(poi => poi.category_code === category)
  },
  actions: {
    setPois(pois) {
      this.pois = pois
    },
    setSelectedPoi(poi) {
      this.selectedPoi = poi
    },
    cachePoiDetail(detail) {
      if (detail?.id) this.detailCache[detail.id] = detail
    }
  }
})
