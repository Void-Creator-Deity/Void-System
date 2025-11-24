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
                开始任务
              </el-button>
              <el-button v-if="task.status === 'in_progress'" type="success" size="small" @click="completeTask(task.task_id)">
                {{ task.difficulty >= 3 ? '提交证明' : '完成任务' }}
              </el-button>
              <template v-if="task.status === 'pending_evaluation'">
                <el-tag type="warning">待评估</el-tag>
              </template>
              <template v-if="task.status === 'completed'">
                <el-tag type="success">已完成</el-tag>
              </template>
              <template v-if="task.status === 'failed'">
                <el-tag type="danger">未通过</el-tag>
              </template>
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

  <!-- 任务证明提交对话框 -->
  <el-dialog
    v-model="proofDialogVisible"
    title="提交任务证明"
    width="500px"
    :close-on-click-modal="false"
  >
    <div v-if="currentTaskForProof">
      <h3 style="margin-bottom: 20px;">{{ currentTaskForProof.task_name }}</h3>
      <p>请提交完成任务的证明材料（如截图、描述等）：</p>
      <el-input
        v-model="proofContent"
        type="textarea"
        :rows="6"
        placeholder="请输入任务证明内容"
        style="margin-top: 15px;"
      ></el-input>
    </div>
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="proofDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitTaskProof">提交证明</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
/**
 * Home Component - System Dashboard
 * -----------------------------------
 * 系统主页，展示用户属性、任务、商店等核心功能
 */

import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '@/api/index'

// ==================== 响应式状态 ====================

// 系统统计数据
const systemData = reactive({
  coins: 0,  // 系统币余额
  taskCompleted: 0,  // 已完成任务数
  taskInProgress: 0,  // 进行中任务数
  attributePoints: 0,  // 总属性点数
  consecutiveDays: 0  // 连续学习天数
})

// 用户属性列表
const attributes = ref([])

// 任务列表
const tasks = ref([])

// 商店商品列表
const shopItems = ref([])

// 新增属性表单
const newAttribute = reactive({
  name: '',
  value: 0,
  description: ''
})

// 新增任务表单
const newTask = reactive({
  title: '',
  attributeName: '',
  duration: '',
  priority: 'medium',
  attributePoints: 1,
  rewardCoins: 10
})

// 对话框显示状态
const showAddAttributeDialog = ref(false)
const showAddTaskDialog = ref(false)

// 任务证明相关
const proofDialogVisible = ref(false)
const currentTaskForProof = ref(null)
const proofContent = ref('')

// 加载用户数据
const loadUserData = async () => {
  try {
    // 获取用户信息
    // 由于是模拟环境，暂时不使用真实API
    // const profile = await api.get('/user/profile')
    // systemData.coins = profile.data.balance
    
    // 加载任务
    await loadTasks()
    
    // 加载属性
    await loadAttributes()
    
    // 加载商店物品
    await loadShopItems()
  } catch (error) {
    console.error('加载用户数据失败:', error)
    ElMessage.error('加载数据失败')
  }
}

// 加载商店物品
const loadShopItems = async () => {
  try {
    // 调用后端API获取商店商品列表
    const response = await api.get('/shop/items')
    shopItems.value = response.data
  } catch (error) {
    console.error('加载商店商品失败:', error)
    ElMessage.error('加载商店商品失败')
    // 在API调用失败时使用模拟数据作为备用
    shopItems.value = [
      { item_id: 'item1', item_name: '小型能量药水', price: 50, category: '消耗品', description: '恢复10点属性值' },
      { item_id: 'item2', item_name: '中型能量药水', price: 150, category: '消耗品', description: '恢复30点属性值' },
      { item_id: 'item3', item_name: '大型能量药水', price: 300, category: '消耗品', description: '恢复50点属性值' },
      { item_id: 'item4', item_name: '任务加速器', price: 200, category: '工具', description: '减少任务完成时间20%' },
      { item_id: 'item5', item_name: '金币探测器', price: 350, category: '工具', description: '增加任务奖励金币15%' }
    ]
  }
}

// 加载属性
  const loadAttributes = async () => {
    try {
      // 调用后端API获取用户属性
      const response = await api.get('/attributes')
      attributes.value = response.data
    } catch (error) {
      console.error('加载属性失败:', error)
      ElMessage.error('加载属性失败')
      // 在API调用失败时使用模拟数据作为备用
      attributes.value = [
        { attr_id: 'attr1', attr_name: '智力', value: 75, max_value: 100, description: '影响思考和学习能力' },
        { attr_id: 'attr2', attr_name: '体力', value: 60, max_value: 100, description: '影响耐力和健康' },
        { attr_id: 'attr3', attr_name: '魅力', value: 80, max_value: 100, description: '影响社交能力' }
      ]
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
    // 调用后端API进行购买操作
    await api.post(`/shop/purchase/${item.id}`)
    
    // 重新加载用户数据以更新余额
    await loadUserData()
    
    ElMessage.success('购买成功！')
  } catch (error) {
    console.error('购买失败:', error)
    ElMessage.error(error.response?.data?.detail || '购买失败')
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

// 任务证明提交对话框状态
const proofDialogVisible = ref(false);
const currentTaskForProof = ref(null);
const proofContent = ref('');

const openProofDialog = (taskId) => {
  const task = tasks.value.find(t => t.task_id === taskId);
  if (task) {
    currentTaskForProof.value = task;
    proofContent.value = '';
    proofDialogVisible.value = true;
  }
};

const submitTaskProof = async () => {
  if (!currentTaskForProof.value || !proofContent.value.trim()) {
    ElMessage.error('请填写任务证明内容');
    return;
  }
  
  try {
    await api.post('/tasks/proof', {
      task_id: currentTaskForProof.value.task_id,
      proof_content: proofContent.value.trim()
    });
    
    ElMessage.success('任务证明提交成功，请等待评估');
    proofDialogVisible.value = false;
    
    // 更新任务状态
    const task = tasks.value.find(t => t.task_id === currentTaskForProof.value.task_id);
    if (task) {
      task.status = 'pending_evaluation';
    }
  } catch (error) {
    console.error('提交任务证明失败:', error);
    ElMessage.error('提交任务证明失败');
  }
};

// 完成任务
const completeTask = async (taskId) => {
  try {
    // 对于需要证明的任务，打开提交证明对话框
    const task = tasks.value.find(t => t.task_id === taskId);
    if (task) {
      // 检查任务是否需要证明
      if (task.difficulty >= 3) { // 难度3以上的任务需要提交证明
        openProofDialog(taskId);
      } else {
        // 简单任务直接完成
        await api.put(`/tasks/${taskId}/status`, { status: 'completed' });
        await loadTasks()
        await loadUserData() // 重新加载用户数据以更新余额
        ElMessage.success('任务完成！获得奖励')
      }
    }
  } catch (error) {
    console.error('完成任务失败:', error);
    ElMessage.error('操作失败');
  }
}

// 组件挂载时加载数据
onMounted(() => {
  loadUserData()
})
</script>

<style scoped>
.home-container {
  max-width: 100%;
  margin: 0 auto;
  padding: 0;
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
  padding-bottom: 20px;
  border-bottom: 1px solid var(--border-color);
  position: relative;
}

.home-header::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  width: 100%;
  height: 1px;
  background: linear-gradient(90deg, transparent, var(--accent-primary), transparent);
}

.home-header h2 {
  font-size: 2.4em;
  margin: 0;
  position: relative;
  font-weight: 700;
}

.home-header h2 .glitch {
  color: var(--accent-primary);
  text-shadow: 0 0 15px var(--accent-glow);
  position: relative;
  display: inline-block;
  animation: glitchEffect 3s infinite;
}

.home-header h2 .dashboard {
  color: var(--text-muted);
  font-weight: 500;
}

.system-status {
  display: flex;
  align-items: center;
  gap: 25px;
  background: rgba(10, 13, 32, 0.6);
  backdrop-filter: var(--blur-sm);
  padding: 0.75rem 1.5rem;
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  font-family: var(--main-font);
  font-size: 0.9rem;
}

.status-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background-color: var(--success-color);
  animation: pulse 2s infinite;
  box-shadow: 0 0 10px var(--success-color);
}

.system-coins {
  display: flex;
  align-items: center;
  gap: 10px;
  font-weight: 600;
  font-size: 1.3em;
  color: var(--warning-color);
  font-family: var(--main-font);
  letter-spacing: 1px;
  position: relative;
}

.system-coins::before {
  content: '';
  position: absolute;
  left: -15px;
  width: 1px;
  height: 20px;
  background: var(--border-color);
}

.coin-icon {
  font-size: 1.4em;
  animation: float 2s ease-in-out infinite;
}

@keyframes glitchEffect {
  0%, 90%, 100% { transform: translateX(0); }
  91% { transform: translateX(-2px); }
  92% { transform: translateX(2px); }
  93% { transform: translateX(-1px); }
  94% { transform: translateX(1px); }
  95% { transform: translateX(-1px); }
  96% { transform: translateX(1px); }
  97% { transform: translateX(-1px); }
  98% { transform: translateX(1px); }
  99% { transform: translateX(-1px); }
}

/* 概览部分 */
.overview-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 25px;
  margin-bottom: 40px;
}

.stat-card {
  background: rgba(42, 65, 140, 0.4);
  backdrop-filter: var(--blur-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 25px;
  display: flex;
  align-items: center;
  gap: 20px;
  transition: all var(--transition-normal) ease;
  position: relative;
  overflow: hidden;
  transform: perspective(1000px) rotateX(0deg);
  transform-style: preserve-3d;
}

.stat-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, var(--accent-primary), transparent);
}

.stat-card::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 150%;
  height: 150%;
  background: radial-gradient(circle, rgba(0, 255, 204, 0.05), transparent 70%);
  transform: translate(-50%, -50%);
  transition: opacity var(--transition-normal) ease;
  opacity: 0;
}

.stat-card:hover {
  transform: translateY(-8px) perspective(1000px) rotateX(5deg);
  box-shadow: 0 8px 30px rgba(0, 255, 204, 0.25);
  border-color: var(--accent-primary);
  background: rgba(42, 65, 140, 0.6);
}

.stat-card:hover::after {
  opacity: 1;
}

.stat-icon {
  font-size: 3em;
  opacity: 0.9;
  transition: transform var(--transition-normal) ease;
  position: relative;
  z-index: 1;
}

.stat-card:hover .stat-icon {
  transform: scale(1.2) rotate(10deg);
}

.stat-content {
  flex: 1;
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: 2.5em;
  font-weight: 700;
  font-family: var(--main-font);
  color: var(--accent-primary);
  line-height: 1.1;
  text-shadow: 0 0 10px var(--accent-glow);
  margin-bottom: 0.25rem;
}

.stat-label {
  color: var(--text-secondary);
  font-size: 0.95em;
  font-family: var(--main-font);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

/* 通用区块样式 */
.attributes-section,
.tasks-section,
.store-section {
  margin-bottom: 40px;
  background: rgba(20, 33, 82, 0.4);
  backdrop-filter: var(--blur-md);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 25px;
  position: relative;
  overflow: hidden;
  transition: all var(--transition-normal) ease;
}

.attributes-section::before,
.tasks-section::before,
.store-section::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 3px;
  background: linear-gradient(90deg, var(--accent-primary), transparent);
  box-shadow: 0 0 10px var(--accent-glow);
}

.attributes-section:hover,
.tasks-section:hover,
.store-section:hover {
  box-shadow: 0 0 30px rgba(0, 255, 204, 0.1);
  border-color: var(--accent-primary);
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

.attributes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 25px;
  margin-top: 25px;
}

.attribute-card {
  background: rgba(10, 13, 32, 0.6);
  backdrop-filter: var(--blur-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 25px;
  transition: all var(--transition-normal) ease;
  position: relative;
  overflow: hidden;
}

.attribute-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 5px;
  height: 100%;
  background: linear-gradient(to bottom, var(--accent-primary), var(--accent-secondary));
  box-shadow: 0 0 15px var(--accent-glow);
}

.attribute-card:hover {
  border-color: var(--accent-primary);
  transform: translateY(-8px);
  box-shadow: 0 8px 25px rgba(0, 255, 204, 0.15);
  background: rgba(10, 13, 32, 0.8);
}

.attribute-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  position: relative;
  z-index: 1;
}

.attribute-name {
  font-size: 1.3em;
  margin: 0;
  color: var(--text-primary);
  font-family: var(--main-font);
  letter-spacing: 0.5px;
}

.attribute-level {
  font-size: 0.95em;
  color: var(--bg-primary);
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  padding: 0.3rem 0.8rem;
  border-radius: var(--radius-full);
  font-weight: 600;
  font-family: var(--main-font);
  box-shadow: 0 0 10px var(--accent-glow);
}

.attribute-progress {
  margin-bottom: 15px;
  position: relative;
  z-index: 1;
}

.progress-bar {
  height: 10px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: var(--radius-full);
  overflow: hidden;
  margin-bottom: 10px;
  border: 1px solid var(--border-color);
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
  transition: width 0.5s ease;
  border-radius: var(--radius-full);
  position: relative;
  overflow: hidden;
}

.progress-fill::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  animation: shimmer 2s infinite;
}

@keyframes shimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}

.attribute-value {
  font-size: 0.9em;
  color: var(--text-secondary);
  text-align: right;
  font-family: var(--main-font);
}

.attribute-description {
  color: var(--text-muted);
  font-size: 0.95em;
  line-height: 1.6;
  position: relative;
  z-index: 1;
}

/* 任务面板 */
.tasks-list {
  display: grid;
  gap: 25px;
  margin-top: 25px;
}

.task-card {
  background: rgba(42, 65, 140, 0.6);
  backdrop-filter: var(--blur-sm);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 25px;
  transition: all var(--transition-normal) ease;
  position: relative;
  overflow: hidden;
  transform: perspective(1000px) rotateX(0deg);
}

.task-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 4px;
  height: 100%;
  transition: all var(--transition-normal) ease;
}

.task-card.hard::before {
  background: var(--error-color, #ff6666);
  box-shadow: 0 0 15px var(--error-color, #ff6666);
}

.task-card.medium::before {
  background: var(--warning-color, #ffff00);
  box-shadow: 0 0 15px var(--warning-color, #ffff00);
}

.task-card.easy::before {
  background: var(--success-color, #00ff66);
  box-shadow: 0 0 15px var(--success-color, #00ff66);
}

.task-card:hover {
  border-color: var(--accent-primary);
  transform: translateY(-5px) perspective(1000px) rotateX(2deg);
  box-shadow: 0 8px 25px rgba(0, 255, 204, 0.15);
  background: rgba(42, 65, 140, 0.8);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 15px;
  position: relative;
  z-index: 1;
}

.task-title {
  font-size: 1.3em;
  margin: 0;
  color: var(--text-primary);
  font-family: var(--main-font);
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.task-title::first-letter {
  color: var(--accent-primary);
  font-size: 1.2em;
}

.task-priority {
  font-size: 0.85em;
  padding: 0.3rem 0.8rem;
  border-radius: var(--radius-full, 20px);
  border: 1px solid;
  font-weight: 600;
  font-family: var(--main-font);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.task-priority.easy {
  background: rgba(0, 255, 102, 0.2);
  color: #00ff66;
  border-color: #00ff66;
  box-shadow: 0 0 8px rgba(0, 255, 102, 0.2);
}

.task-priority.medium {
  background: rgba(255, 255, 0, 0.2);
  color: #ffff00;
  border-color: #ffff00;
  box-shadow: 0 0 8px rgba(255, 255, 0, 0.2);
}

.task-priority.hard {
  background: rgba(255, 102, 102, 0.2);
  color: #ff6666;
  border-color: #ff6666;
  box-shadow: 0 0 8px rgba(255, 102, 102, 0.2);
}

.task-body {
  margin-bottom: 15px;
  position: relative;
  z-index: 1;
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
  font-family: var(--main-font);
}

.task-progress {
  position: relative;
  z-index: 1;
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
  position: relative;
  z-index: 1;
  flex-wrap: wrap;
  gap: 15px;
}

.task-status {
  padding: 3px 8px;
  border-radius: 4px;
  font-size: 0.9em;
  font-weight: 600;
  border: 1px solid;
  font-family: var(--main-font);
}

.task-status.pending {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  border-color: var(--text-secondary);
}

.task-status.in-progress {
  background: rgba(0, 255, 204, 0.2);
  color: var(--accent-primary);
  border-color: var(--accent-primary);
  box-shadow: 0 0 8px rgba(0, 255, 204, 0.2);
}

.task-status.completed {
  background: rgba(0, 255, 102, 0.2);
  color: #00ff66;
  border-color: #00ff66;
  box-shadow: 0 0 8px rgba(0, 255, 102, 0.2);
}

.task-status.pending_evaluation {
  background: rgba(255, 204, 0, 0.2);
  color: #ffff00;
  border-color: #ffff00;
  box-shadow: 0 0 8px rgba(255, 204, 0, 0.2);
}

.task-status.failed {
  background: rgba(255, 102, 102, 0.2);
  color: #ff6666;
  border-color: #ff6666;
  box-shadow: 0 0 8px rgba(255, 102, 102, 0.2);
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

/* 任务操作按钮样式 */
.task-actions {
  display: flex;
  gap: 10px;
  margin-top: 20px;
  position: relative;
  z-index: 1;
}

.task-btn {
  padding: 0.6rem 1.2rem;
  border: none;
  border-radius: var(--radius-md);
  font-size: 0.95em;
  cursor: pointer;
  transition: all var(--transition-normal) ease;
  font-family: var(--main-font);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  position: relative;
  overflow: hidden;
}

.task-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
  transition: left var(--transition-normal) ease;
}

.task-btn:hover::before {
  left: 100%;
}

.task-btn-primary {
  background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
  color: var(--bg-primary);
  box-shadow: 0 0 15px var(--accent-glow);
}

.task-btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 0 20px var(--accent-primary);
}

.task-btn-secondary {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
}

.task-btn-secondary:hover {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
  background: rgba(0, 255, 204, 0.05);
  transform: translateY(-1px);
}

.task-btn-danger {
  background: rgba(255, 51, 102, 0.1);
  border: 1px solid var(--error-color);
  color: var(--error-color);
}

.task-btn-danger:hover {
  background: rgba(255, 51, 102, 0.2);
  transform: translateY(-1px);
  box-shadow: 0 0 15px rgba(255, 51, 102, 0.3);
}

/* 空状态 */
.empty-attributes,
.empty-tasks {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 40px;
  text-align: center;
  color: var(--text-secondary);
  background: rgba(10, 13, 32, 0.3);
  backdrop-filter: var(--blur-sm);
  border: 2px dashed var(--border-color);
  border-radius: var(--radius-lg);
  transition: all var(--transition-normal) ease;
}

.empty-attributes:hover,
.empty-tasks:hover {
  border-color: var(--accent-primary);
  box-shadow: 0 0 30px rgba(0, 255, 204, 0.1);
  background: rgba(10, 13, 32, 0.5);
}

.empty-icon {
  font-size: 4em;
  margin-bottom: 20px;
  opacity: 0.7;
  animation: float 3s ease-in-out infinite;
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