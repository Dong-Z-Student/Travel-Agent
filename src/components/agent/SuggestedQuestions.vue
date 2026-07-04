<script setup>
const emit = defineEmits(['ask'])

const questions = [
  '帮我规划两天武汉轻松游',
  '东湖附近怎么玩',
  '推荐靠近地铁的酒店'
]
</script>

<template>
  <div class="suggested-questions">
    <button
      v-for="question in questions"
      :key="question"
      type="button"
      @click="emit('ask', question)"
    >{{ question }}</button>
  </div>
</template>

<style scoped>
.suggested-questions {
  display: grid;
  gap: 6px;
}

button {
  height: 30px;
  padding: 0 10px;
  color: #334155;
  text-align: left;
  cursor: pointer;
  background: #fff;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 7px;
}

button:hover {
  color: #0f766e;
  background: #f8fafc;
}
</style>
