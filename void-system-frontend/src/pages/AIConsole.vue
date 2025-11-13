<template>
  <div class="console">
    <el-card class="chat-panel">
      <div class="messages">
        <div v-for="(msg, idx) in messages" :key="idx" class="msg">
          <b v-if="msg.role==='user'">你：</b>
          <b v-else>系统精灵：</b>
          <span>{{ msg.text }}</span>
        </div>
      </div>
      <el-input
        v-model="input"
        placeholder="输入你的问题..."
        @keyup.enter="send"
      />
    </el-card>
  </div>
</template>

<script setup>
import { ref } from "vue"
import { askPersona } from "@/api/ai"

const input = ref("")
const messages = ref([])

async function send() {
  if (!input.value.trim()) return
  messages.value.push({ role: "user", text: input.value })
  const reply = await askPersona(input.value)
  messages.value.push({ role: "system", text: reply })
  input.value = ""
}
</script>

<style scoped>
.console {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 40px;
}
.chat-panel {
  width: 700px;
  background: rgba(20, 20, 25, 0.9);
  color: #eee;
}
.messages {
  height: 400px;
  overflow-y: auto;
  margin-bottom: 10px;
}
.msg { margin: 8px 0; }
</style>
