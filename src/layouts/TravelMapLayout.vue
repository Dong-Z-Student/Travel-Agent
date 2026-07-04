<script setup>
import OlMapContainer from '@/components/map/OlMapContainer.vue'
import LeftBottomControls from '@/components/map/LeftBottomControls.vue'
import RightBottomControls from '@/components/map/RightBottomControls.vue'
import TopRightToolbar from '@/components/toolbar/TopRightToolbar.vue'
import PoiClusterLayer from '@/components/poi/PoiClusterLayer.vue'
import AgentChatEntry from '@/components/agent/AgentChatEntry.vue'
</script>

<template>
  <div class="travel-map-layout">
    <OlMapContainer />
    <PoiClusterLayer />
    <AgentChatEntry />
    <LeftBottomControls />
    <RightBottomControls />
    <TopRightToolbar />
    <div class="poi-legend" aria-label="POI 图例">
      <span><i class="legend-dot scenic"></i>景点</span>
      <span><i class="legend-dot hotel"></i>酒店</span>
      <span><i class="legend-dot metro"></i>地铁站</span>
    </div>
  </div>
</template>

<style scoped>
.travel-map-layout {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: #eef2f5;
}

.poi-legend {
  position: absolute;
  right: 70px;
  bottom: 16px;
  z-index: 5;
  display: flex;
  gap: 12px;
  align-items: center;
  padding: 8px 10px;
  font-size: 13px;
  color: #1f2933;
  pointer-events: none;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.12);
}

.poi-legend span {
  display: inline-flex;
  gap: 5px;
  align-items: center;
  white-space: nowrap;
}

.legend-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}

.legend-dot.scenic { background: #e85d3f; }
.legend-dot.hotel { background: #2f80ed; }
.legend-dot.metro { background: #16a36a; }
</style>



