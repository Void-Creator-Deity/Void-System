<template>
  <el-card>
    <el-input
      v-model="question"
      placeholder="向系统提问（知识库检索）"
      @keyup.enter="ask"
    />
    <el-button :style="{ position: 'relative' }" @click="ask">发送</el-button>

    <div v-if="answer" class="answer-box">
      <h4>回答：</h4>
      <pre>{{ answer }}</pre>
    </div>
  </el-card>
</template>

<script setup>
import { ref } from "vue"
import { askQA } from "@/api/ai"

const question = ref("")
const answer = ref("")

async function ask() {
  answer.value = await askQA(question.value)
}
</script>

<style scoped>
.answer-box {
  margin-top: 20px;
  background: rgba(0,0,0,0.6);
  padding: 10px;
  border-radius: 8px;
  color: #eaeaea;
}
</style>
