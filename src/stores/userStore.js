import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({ session: null, user: null }),
  getters: {
    isLoggedIn: state => Boolean(state.user)
  },
  actions: {
    setSession(payload) {
      this.session = payload?.session || null
      this.user = payload?.user || null
    },
    clearSession() {
      this.session = null
      this.user = null
    }
  }
})
