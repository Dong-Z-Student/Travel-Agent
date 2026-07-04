<script setup>
import { computed } from 'vue'

const props = defineProps({
  poi: { type: Object, default: null },
  detail: { type: Object, default: null }
})

const categoryLabel = computed(() => {
  const code = props.poi?.category_code || props.detail?.category_code
  return code === 'scenic_spot' ? '景点' : code === 'hotel' ? '酒店' : '地铁站'
})

const cover = computed(() => props.detail?.images?.[0]?.image_url || '')
const intro = computed(() => props.detail?.profile?.short_intro_zh || props.poi?.tags?.join(' / ') || '')
</script>

<template>
  <article v-if="poi" class="poi-popup-card">
    <img v-if="cover" class="poi-cover" :src="cover" :alt="poi.name_zh" />
    <div class="poi-body">
      <div class="poi-meta">{{ categoryLabel }}</div>
      <h3>{{ detail?.name_zh || poi.name_zh }}</h3>
      <p v-if="detail?.name_en || poi.name_en" class="poi-en">{{ detail?.name_en || poi.name_en }}</p>
      <p v-if="intro" class="poi-intro">{{ intro }}</p>
      <p class="poi-address">{{ detail?.address || poi.address }}</p>
      <div v-if="detail?.profile?.recommended_duration_minutes" class="poi-extra">
        建议游览 {{ detail.profile.recommended_duration_minutes }} 分钟
      </div>
    </div>
  </article>
</template>

<style scoped>
.poi-popup-card {
  width: 300px;
  overflow: hidden;
  color: #1f2933;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.18);
}

.poi-cover {
  display: block;
  width: 100%;
  height: 132px;
  object-fit: cover;
}

.poi-body {
  padding: 12px 14px 14px;
}

.poi-meta {
  margin-bottom: 4px;
  font-size: 12px;
  color: #1d7f64;
}

h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 700;
  line-height: 1.3;
}

.poi-en {
  margin: 2px 0 8px;
  font-size: 12px;
  color: #6b7280;
}

.poi-intro,
.poi-address,
.poi-extra {
  margin: 7px 0 0;
  font-size: 13px;
  line-height: 1.5;
}

.poi-address {
  color: #475569;
}

.poi-extra {
  color: #0f766e;
}
</style>
