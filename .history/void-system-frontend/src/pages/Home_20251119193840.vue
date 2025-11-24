<template>
  <div class="home-container">
    <!-- 页面标题 -->
    <div class="home-header">
      <h2><span class="glitch">虚空</span> <span class="system-text">系统</span> <span class="dashboard">控制台</span></h2>
      <div class="system-status">
        <div class="status-indicator">
          <div class="status-dot"></div>
          <span>系统运行正常</span>
        </div>
        <div class="system-coins">
          <span class="coin-icon">💰</span>
          <span class="coin-count">{{ systemData.coins }}</span>
        </div>
      </div>
    </div>
    
    <!-- 核心数据概览 -->
    <div class="overview-section">
      <div class="stat-card">
        <div class="stat-icon">📊</div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.taskCompleted }}</div>
          <div class="stat-label">总任务完成</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🎯</div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.taskInProgress }}</div>
          <div class="stat-label">进行中任务</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">📈</div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.attributePoints }}</div>
          <div class="stat-label">总属性点数</div>
        </div>
      </div>
      <div class="stat-card">
        <div class="stat-icon">🔥</div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.consecutiveDays }}</div>
          <div class="stat-label">连续学习天数</div>
        </div>
      </div>
    </div>
    
    <!-- 属性面板 -->
    <div class="attributes-section">
      <div class="section-header">
        <h3>🧠 个人属性</h3>
        <el-button type="primary" size="small" @click="showAddAttributeDialog = true">
          + 添加属性
        </el-button>
      </div>
      
      <div class="attributes-grid">
        <div v-for="(attr, index) in attributes" :key="index" class="attribute-card">
          <div class="attribute-header">
            <h4 class="attribute-name">{{ attr.attr_name }}</h4>
            <div class="attribute-level">Lv.{{ Math.floor(attr.attr_value / 10) }}</div>
          </div>
          
          <div class="attribute-progress">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: attr.attr_value + '%' }"></div>
            </div>
            <div class="attribute-value">{{ attr.attr_value }}/{{ attr.max_value || 100 }}</div>
          </div>
          
          <div class="attribute-description">{{ attr.description || '暂无描述' }}</div>
        </div>
        
        <!-- 空状态 -->
        <div v-if="attributes.length === 0" class="empty-attributes">
          <div class="empty-icon">🔍</div>
          <p>尚未添加任何属性</p>
          <el-button type="info" size="small" @click="showAddAttributeDialog = true">
            开始添加属性
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 任务面板 -->
    <div class="tasks-section">
      <div class="section-header">
        <h3>📋 学习任务</h3>
        <el-button type="primary" size="small" @click="showAddTaskDialog = true">
          + 创建任务
        </el-button>
      </div>
      
      <div class="tasks-list">
        <div v-for="(task, index) in tasks" :key="index" class="task-card">
          <div class="task-header">
            <h4 class="task-title">{{ task.task_name || task.title }}</h4>
            <div class="task-priority" :class="task.priority || 'medium'">
              {{ (task.priority || 'medium') === 'easy' ? '简单' : (task.priority || 'medium') === 'medium' ? '中等' : '困难' }}
            </div>
          </div>
          
          <div class="task-body">
            <div class="task-info">
              <span class="info-item">
                <span class="info-icon">⏱️</span>
                {{ task.estimated_time || task.duration || '未设置' }}
              </span>
              <span class="info-item">
                <span class="info-icon">🎯</span>
                {{ task.related_attrs || task.attributeName || '未关联' }}
              </span>
              <span class="info-item">
                <span class="info-icon">💰</span>
                +{{ task.reward_coins || task.rewardCoins || 0 }}
              </span>
              <span class="info-item">
                <span class="info-icon">📊</span>
                +{{ task.attribute_points || task.attributePoints || 0 }}点
              </span>
            </div>
            
            <div class="task-progress">
              <div class="progress-bar">
                <div class="progress-fill" :style="{ width: (task.progress || 0) + '%' }"></div>
              </div>
              <div class="progress-text">{{ task.progress || 0 }}%</div>
            </div>
          </div>
          
          <div class="task-footer">
            <div class="task-status" :class="task.status || 'pending'">
              {{ (task.status || 'pending') === 'pending' ? '待开始' : (task.status || 'pending') === 'in_progress' ? '进行中' : '已完成' }}
            </div>
            <div class="task-actions">
              <el-button v-if="task.status === 'pending'" size="small" @click="startTask(task.task_id)">
                开始
              </el-button>
              <el-button v-if="task.status === 'in_progress'" type="success" size="small" @click="completeTask(task.task_id)">
                完成
              </el-button>
              <el-button v-if="task.status === 'completed'" type="info" size="small" disabled>
                已完成
              </el-button>
            </div>
          </div>
        </div>
        
        <!-- 空状态 -->
        <div v-if="tasks.length === 0" class="empty-tasks">
          <div class="empty-icon">📝</div>
          <p>暂无学习任务</p>
          <el-button type="info" size="small" @click="showAddTaskDialog = true">
            创建第一个任务
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 资源商店 -->
    <div class="store-section">
      <div class="section-header">
        <h3>🛒 资源商店</h3>
        <div class="store-balance">
          余额: {{ systemData.coins }} 币
        </div>
      </div>
      
      <div class="store-items">
        <div v-for="(item, index) in shopItems" :key="index" class="store-item">
          <div class="item-icon">{{ item.icon || '📦' }}</div>
          <div class="item-info">
            <h4 class="item-name">{{ item.name || '未命名物品' }}</h4>
            <div class="item-description">{{ item.description || '暂无描述' }}</div>
            <div class="item-price">
              <span class="coin-icon">💰</span>
              {{ item.price || 0 }}
            </div>
          </div>
          <el-button 
            :disabled="systemData.coins < (item.price || 0) || (item.quantity || 0) <= 0"
            size="small" 
            @click="purchaseItem(index)"
          >
            {{ systemData.coins < (item.price || 0) ? '余额不足' : (item.quantity || 0) <= 0 ? '已售罄' : '兑换' }}
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 添加属性对话框 -->
    <el-dialog v-model="showAddAttributeDialog" title="添加新属性" width="500px">
      <el-form :model="newAttribute" label-width="80px">
        <el-form-item label="属性名称">
          <el-input v-model="newAttribute.name" placeholder="例如：高数熟练度"></el-input>
        </el-form-item>
        <el-form-item label="初始值">
          <el-slider v-model="newAttribute.value" :min="0" :max="100" :step="1"></el-slider>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newAttribute.description" type="textarea" placeholder="简要描述此属性"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddAttributeDialog = false">取消</el-button>
        <el-button type="primary" @click="addAttribute">添加</el-button>
      </template>
    </el-dialog>
    
    <!-- 创建任务对话框 -->
    <el-dialog v-model="showAddTaskDialog" title="创建新任务" width="600px">
      <el-form :model="newTask" label-width="80px">
        <el-form-item label="任务名称">
          <el-input v-model="newTask.title" placeholder="例如：完成3小时高数学习"></el-input>
        </el-form-item>
        <el-form-item label="关联属性">
          <el-select v-model="newTask.attributeName" placeholder="选择属性">
            <el-option v-for="attr in attributes" :key="attr.attr_name" :label="attr.attr_name" :value="attr.attr_name"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="预计时长">
          <el-input v-model="newTask.duration" placeholder="例如：2小时"></el-input>
        </el-form-item>
        <el-form-item label="难度等级">
          <el-select v-model="newTask.priority" placeholder="选择难度">
            <el-option label="简单" value="easy"></el-option>
            <el-option label="中等" value="medium"></el-option>
            <el-option label="困难" value="hard"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="属性奖励">
          <el-input-number v-model="newTask.attributePoints" :min="1" :max="20"></el-input-number>
        </el-form-item>
        <el-form-item label="系统币奖励">
          <el-input-number v-model="newTask.rewardCoins" :min="1" :max="100"></el-input-number>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddTaskDialog = false">取消</el-button>
        <el-button type="primary" @click="addTask">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/index'

// 系统数据（替换模拟数据）
const systemData = reactive({
  coins: 100, // 设置默认值
  taskCompleted: 0,
  taskInProgress: 0,
  attributePoints: 0,
  consecutiveDays: 0
})

const attributes = ref([
  { attr_name: '数学', attr_value: 50, description: '数学技能水平' },
  { attr_name: '编程', attr_value: 75, description: '编程能力水平' }
]) // 添加示例数据
const tasks = ref([
  { task_id: 1, task_name: '完成每日编程练习', status: 'in_progress', progress: 50 },
  { task_id: 2, task_name: '阅读技术文档', status: 'pending', progress: 0 }
]) // 添加示例数据
const shopItems = ref([
  { id: 1, name: '学习加速卡', description: '提高学习效率20%', price: 50, quantity: 10, icon: '🚀' },
  { id: 2, name: '属性提升券', description: '提升任意属性5点', price: 80, quantity: 5, icon: '🎯' }
]) // 添加示例数据
const newAttribute = reactive({
  name: '',
  value: 0,
  description: ''
})
const newTask = reactive({
  title: '',
  attributeName: '',
  duration: '',
  priority: 'medium',
  attributePoints: 1,
  rewardCoins: 10
})
const showAddAttributeDialog = ref(false)
const showAddTaskDialog = ref(false)

// 加载用户数据
  const loadUserData = async () => {
    try {
      // 获取用户信息
      const profile = await api.get('/user/profile')
      // 由于是模拟环境，暂时不使用真实API返回的数据
    } catch (error) {
      console.error('加载用户数据失败:', error)
      ElMessage.error('加载数据失败')
    }
    systemData.coins = profile.data.balance
    
    // 加载任务
    await loadTasks()
    
    // 加载属性
    await loadAttributes()
    
    // 加载商店物品
  await loadShopItems()
}

// 加载商店物品
const loadShopItems = async () => {
  try {
    // 模拟API调用，实际项目中替换为真实API
    // const response = await api.get('/shop/items')
    // shopItems.value = response.data
    console.log('商店物品已加载')
  } catch (error) {
    console.error('加载商店物品失败:', error)
  }
  } catch (error) {
    console.error('加载用户数据失败:', error)
    ElMessage.error('加载数据失败')
  }
}

// 加载任务
const loadTasks = async () => {
  try {
    const response = await api.get('/tasks')
    tasks.value = response.data
    
    // 更新任务统计
    systemData.taskCompleted = tasks.value.filter(t => t.status === 'completed').length
    systemData.taskInProgress = tasks.value.filter(t => t.status === 'in_progress').length
  } catch (error) {
    console.error('加载任务失败:', error)
  }
}

// 添加属性
const addAttribute = async () => {
  try {
    const newAttr = {
      attr_name: newAttribute.name,
      attr_value: newAttribute.value,
      description: newAttribute.description
    }
    
    // 模拟API调用
    // await api.post('/attributes', newAttr)
    
    attributes.value.push(newAttr)
    showAddAttributeDialog.value = false
    ElMessage.success('属性添加成功')
    
    // 重置表单
    newAttribute.name = ''
    newAttribute.value = 0
    newAttribute.description = ''
  } catch (error) {
    console.error('添加属性失败:', error)
    ElMessage.error('添加属性失败')
  }
}

// 添加任务
const addTask = async () => {
  try {
    const taskToAdd = {
      task_id: tasks.value.length + 1,
      task_name: newTask.title,
      status: 'pending',
      progress: 0,
      related_attrs: newTask.attributeName,
      estimated_time: newTask.duration,
      reward_coins: newTask.rewardCoins,
      attribute_points: newTask.attributePoints,
      priority: newTask.priority
    }
    
    // 模拟API调用
    // await api.post('/tasks', taskToAdd)
    
    tasks.value.push(taskToAdd)
    showAddTaskDialog.value = false
    ElMessage.success('任务创建成功')
    
    // 重置表单
    newTask.title = ''
    newTask.attributeName = ''
    newTask.duration = ''
    newTask.priority = 'medium'
    newTask.attributePoints = 1
    newTask.rewardCoins = 10
    
    // 更新任务统计
    systemData.taskInProgress = tasks.value.filter(t => t.status === 'in_progress' || t.status === 'in_progress').length
  } catch (error) {
    console.error('创建任务失败:', error)
    ElMessage.error('创建任务失败')
  }
}

// 购买物品
const purchaseItem = async (index) => {
  const item = shopItems.value[index]
  if (!item) return
  
  if (systemData.coins < (item.price || 0)) {
    ElMessage.warning('余额不足')
    return
  }
  
  try {
    // 模拟购买
    systemData.coins -= (item.price || 0)
    item.quantity = (item.quantity || 0) - 1
    ElMessage.success('购买成功！')
  } catch (error) {
    console.error('购买失败:', error)
    ElMessage.error('购买失败')
  }
}

// 开始任务
const startTask = async (taskId) => {
  try {
    await api.put(`/tasks/${taskId}/status`, { status: 'in_progress' })
    await loadTasks()
    ElMessage.success('任务已开始')
  } catch (error) {
    console.error('更新任务状态失败:', error)
    ElMessage.error('操作失败')
  }
}

// 完成任务
const completeTask = async (taskId) => {
  try {
    await api.put(`/tasks/${taskId}/status`, { status: 'completed' })
    await loadTasks()
    await loadUserData() // 重新加载用户数据以更新余额
    ElMessage.success('任务完成！获得奖励')
  } catch (error) {
    console.error('完成任务失败:', error)
    ElMessage.error('操作失败')
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadUserData()
})
</script>

<style scoped>
.home-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 20px;
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
}

.home-header h2 {
  font-size: 2.2em;
  margin: 0;
}

.system-status {
  display: flex;
  align-items: center;
  gap: 20px;
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background-color: var(--accent-primary);
  animation: pulse 2s infinite;
}

.system-coins {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  font-size: 1.2em;
  color: var(--accent-primary);
}

/* 概览部分 */
.overview-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.stat-card {
  background: rgba(42, 65, 140, 0.5);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: all var(--transition-fast) ease;
  position: relative;
  overflow: hidden;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-primary), transparent);
}

.stat-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 5px 20px rgba(0, 255, 204, 0.2);
}

.stat-icon {
  font-size: 2.5em;
  opacity: 0.9;
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 2em;
  font-weight: 700;
  font-family: var(--main-font);
  color: var(--accent-primary);
  line-height: 1.2;
}

.stat-label {
  color: var(--text-secondary);
  font-size: 0.9em;
}

/* 通用区块样式 */
.attributes-section,
.tasks-section,
.store-section {
  margin-bottom: 40px;
  background: rgba(20, 33, 82, 0.3);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 25px;
  position: relative;
  overflow: hidden;
}

.attributes-section::before,
.tasks-section::before,
.store-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--accent-primary), transparent);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 25px;
}

.section-header h3 {
  font-size: 1.5em;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 10px;
}

/* 属性面板 */
.attributes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.attribute-card {
  background: rgba(42, 65, 140, 0.5);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  transition: all var(--transition-fast) ease;
}

.attribute-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0, 255, 204, 0.15);
}

.attribute-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.attribute-name {
  font-size: 1.2em;
  margin: 0;
}

.attribute-level {
  background: rgba(0, 255, 204, 0.2);
  color: var(--accent-primary);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: 600;
}

.attribute-progress {
  margin-bottom: 10px;
}

.progress-bar {
  width: 100%;
  height: 8px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 4px;
  overflow: hidden;
  margin-bottom: 5px;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  border-radius: 4px;
  transition: width var(--transition-normal) ease;
}

.attribute-value {
  text-align: right;
  font-size: 0.9em;
  color: var(--text-secondary);
}

.attribute-description {
  color: var(--text-secondary);
  font-size: 0.9em;
  margin-top: 10px;
}

/* 任务面板 */
.tasks-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.task-card {
  background: rgba(42, 65, 140, 0.5);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  transition: all var(--transition-fast) ease;
}

.task-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0, 255, 204, 0.15);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.task-title {
  font-size: 1.2em;
  margin: 0;
}

.task-priority {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: 600;
}

.task-priority.easy {
  background: rgba(0, 255, 102, 0.2);
  color: #00ff66;
}

.task-priority.medium {
  background: rgba(255, 255, 0, 0.2);
  color: #ffff00;
}

.task-priority.hard {
  background: rgba(255, 102, 102, 0.2);
  color: #ff6666;
}

.task-body {
  margin-bottom: 15px;
}

.task-info {
  display: flex;
  flex-wrap: wrap;
  gap: 15px;
  margin-bottom: 15px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 5px;
  font-size: 0.9em;
  color: var(--text-secondary);
}

.task-progress .progress-text {
  text-align: right;
  font-size: 0.9em;
  color: var(--text-secondary);
  margin-top: 5px;
}

.task-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-status {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: 600;
}

.task-status.pending {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
}

.task-status.in-progress {
  background: rgba(0, 255, 204, 0.2);
  color: var(--accent-primary);
}

.task-status.completed {
  background: rgba(0, 255, 102, 0.2);
  color: #00ff66;
}

/* 商店部分 */
.store-balance {
  color: var(--accent-primary);
  font-weight: 600;
}

.store-items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px;
}

.store-item {
  background: rgba(42, 65, 140, 0.5);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 15px;
  transition: all var(--transition-fast) ease;
}

.store-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 5px 15px rgba(0, 255, 204, 0.15);
}

.item-icon {
  font-size: 2.5em;
}

.item-info {
  flex: 1;
}

.item-name {
  font-size: 1.1em;
  margin: 0 0 5px 0;
}

.item-description {
  color: var(--text-secondary);
  font-size: 0.9em;
  margin-bottom: 8px;
}

.item-price {
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 600;
  color: var(--accent-primary);
}

/* 空状态 */
.empty-attributes,
.empty-tasks {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 40px 20px;
  text-align: center;
  color: var(--text-secondary);
}

.empty-icon {
  font-size: 3em;
  margin-bottom: 15px;
  opacity: 0.5;
}

/* 动画 */
@keyframes pulse {
  0% {
    opacity: 0.6;
  }
  50% {
    opacity: 1;
    box-shadow: 0 0 10px var(--accent-primary);
  }
  100% {
    opacity: 0.6;
  }
}

/* 响应式 */
@media (max-width: 768px) {
  .home-header {
    flex-direction: column;
    gap: 15px;
    text-align: center;
  }
  
  .overview-section {
    grid-template-columns: 1fr;
  }
  
  .section-header {
    flex-direction: column;
    gap: 15px;
    align-items: stretch;
  }
  
  .attributes-grid,
  .store-items {
    grid-template-columns: 1fr;
  }
  
  .task-info {
    gap: 10px;
  }
  
  .task-footer {
    flex-direction: column;
    gap: 10px;
    align-items: stretch;
  }
  
  .store-item {
    flex-direction: column;
    text-align: center;
  }
}
</style>