<template>
  <div class="map-copyright">© 武汉市智能出行旅游规划 Agent · 地图数据来自公开底图服务</div>
</template>

<style scoped>
.map-copyright {
  position: absolute;
  left: 50%;
  bottom: 12px;
  z-index: 5;
  max-width: min(560px, calc(100vw - 360px));
  padding: 5px 10px;
  font-size: 12px;
  line-height: 1.4;
  color: #475569;
  text-align: center;
  white-space: nowrap;
  pointer-events: none;
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 8px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.08);
  transform: translateX(-50%);
}
</style>
