<template>
  <div class="tool-popover"><slot /></div>
</template>

<style scoped>
.tool-popover {
  position: absolute;
  top: 46px;
  left: 50%;
  min-width: 220px;
  max-width: min(360px, calc(100vw - 32px));
  padding: 12px;
  color: #1f2937;
  background: rgba(255, 255, 255, 0.97);
  border: 1px solid rgba(15, 23, 42, 0.10);
  border-radius: 8px;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.16);
  transform: translateX(-50%);
}
</style>
