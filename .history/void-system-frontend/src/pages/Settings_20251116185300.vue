<template>
  <el-card>
    <el-input 
      v-model="topic" 
      placeholder="输入学习主题，例如：高等数学" 
      @keyup.enter="generate"
    />
    
    <!-- 添加波纹效果的按钮 -->
    <button class="ripple-button custom-btn" @click="generate">
      生成任务
    </button>

    <div v-if="result" class="result-box">
      <h3>系统建议：</h3>
      <pre>{{ result }}</pre>
    </div>
  </el-card>
</template>

<script setup>
import { ref } from "vue"

const topic = ref("")
const result = ref("")

// 波纹效果函数
function createRipple(event) {
  const button = event.currentTarget;
  const circle = document.createElement("span");
  const diameter = Math.max(button.clientWidth, button.clientHeight);
  const radius = diameter / 2;
  
  circle.style.width = circle.style.height = `${diameter}px`;
  circle.style.left = `${event.clientX - button.getBoundingClientRect().left - radius}px`;
  circle.style.top = `${event.clientY - button.getBoundingClientRect().top - radius}px`;
  circle.classList.add("ripple-effect");
  
  const ripple = button.getElementsByClassName("ripple-effect")[0];
  if (ripple) {
    ripple.remove();
  }
  
  button.appendChild(circle);
}

// 生成任务函数
async function generate(event) {
  console.log("触发了generate函数，topic值：", topic.value);
  if (!topic.value.trim()) return;
  
  try {
    result.value = topic.value;
  } catch (error) {
    console.error("生成失败:", error);
    result.value = "生成失败，请重试";
  }
}
</script>

<style scoped>
/* 波纹效果样式 */
.ripple-button {
  position: relative;
  overflow: hidden;
  background: #409EFF;
  color: white;
  border: none;
  padding: 12px 24px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: background 0.3s;
  margin-top: 10px;
}
</style>

