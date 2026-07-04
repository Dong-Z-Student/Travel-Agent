import { createApp } from 'vue'
import { createPinia } from 'pinia'

// 引入element资源
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn'

// 引入ol样式，类文件按需引入
import 'ol/ol.css'

import App from './App.vue'
import router from './router'

import './assets/main.css'

const app = createApp(App)
window.app1 = app
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: zhCn })

app.mount('#app')
