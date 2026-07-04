import { fileURLToPath, URL } from 'node:url'

import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const tiandituKey = env.VITE_TIANDITU_KEY || ''

  return {
    base: './',
    plugins: [
      vue(),
    ],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url))
      }
    },
    server: {
      proxy: {
        '/tianditu': {
          target: 'https://t0.tianditu.gov.cn',
          changeOrigin: true,
          secure: true,
          rewrite: (path) => {
            const targetPath = path.replace(/^\/tianditu/, '')
            if (!tiandituKey) return targetPath
            const separator = targetPath.includes('?') ? '&' : '?'
            return `${targetPath}${separator}tk=${tiandituKey}`
          },
        }
      }
    }
  }
})
