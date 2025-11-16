<template>
  <el-card>
    <el-input 
    v-model="topic" 
    placeholder="输入学习主题，例如：高等数学" 
    @keyup.enter="generate"
    />
    <el-button :style="{ position: 'relative' }" type="primary" @click="generate">生成任务</el-button>

    <div v-if="result" class="result-box">
      <h3>系统建议：</h3>
      <pre>{{ result }}</pre>
    </div>
  </el-card>
</template>

<script setup>
import { ref } from "vue"
import { getAdvisor } from "@/api/ai"

const topic = ref("")
const result = ref("")

async function generate() {
  console.log("触发了generate函数，topic值：", topic.value)
  
  // 添加输入验证
  if (!topic.value.trim()) {
    console.log("输入内容为空")
    return
  }
  
  try {
    console.log("开始调用API...")
    result.value = await getAdvisor(topic.value)
    console.log("API调用完成，结果：", result.value)
  } catch (error) {
    console.error("API调用失败：", error)
    result.value = "生成失败，请重试"
  }
}

</script>

<style scoped>
.result-box {
  margin-top: 20px;
  white-space: pre-wrap;
  background: rgba(20, 20, 25, 0.85);
  color: #ccc;
  padding: 15px;
  border-radius: 10px;
}
</style>
