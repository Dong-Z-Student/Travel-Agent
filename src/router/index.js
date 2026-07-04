import { createRouter, createWebHistory } from 'vue-router'
import TravelMapLayout from '@/layouts/TravelMapLayout.vue'

const routes = [
  {
    path: '/',
    name: 'TravelMap',
    component: TravelMapLayout
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

export default router
