import { defineConfig, minimal2023Preset } from '@vite-pwa/assets-generator/config'

export default defineConfig({
  preset: {
    ...minimal2023Preset,
    maskable: { ...minimal2023Preset.maskable, resizeOptions: { background: '#2F7DBF' } },
    apple: { ...minimal2023Preset.apple, resizeOptions: { background: '#2F7DBF' } },
  },
  images: ['public/favicon.svg'],
})
