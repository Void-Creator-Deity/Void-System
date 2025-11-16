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



// 生成任务函数
async function generate() {
  // 添加波纹效果
  
  // 原有的生成逻辑
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
