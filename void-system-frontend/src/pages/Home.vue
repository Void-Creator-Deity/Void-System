<template>
  <div class="home-container">
    <!-- 页面标题 -->
    <div class="home-header">
      <div class="header-main">
        <h2><span class="glitch">虚空</span> <span class="system-text">系统</span> 终端</h2>
        <div class="user-level-badge">
          <div class="level-label">等级</div>
          <div class="level-value">{{ systemData.level }}</div>
        </div>
      </div>
      
      <div class="system-meta">
        <div class="exp-bar-container">
          <div class="exp-info">
            <span>EXP</span>
            <span>{{ systemData.expProgress }} / 100</span>
          </div>
          <div class="exp-track">
            <div class="exp-fill" :style="{ width: systemData.expProgress + '%' }"></div>
          </div>
        </div>

        <div class="system-status">
          <div class="status-indicator">
            <div class="status-dot"></div>
            <span>已连接</span>
          </div>
          <div class="system-coins">
            <span class="coin-icon">💰</span>
            <span class="coin-count">{{ systemData.coins }}</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 核心数据概览 -->
    <div class="overview-section grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-lg">
      <div class="stat-card card cyber-border">
        <div class="stat-icon-wrapper">
          <div class="stat-icon">📊</div>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.taskCompleted }}</div>
          <div class="stat-label">完成任务</div>
          <div class="stat-sub">率: {{ systemData.completionRate.toFixed(1) }}%</div>
        </div>
      </div>
      <div class="stat-card card cyber-border">
        <div class="stat-icon-wrapper">
          <div class="stat-icon">🎯</div>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.taskInProgress }}</div>
          <div class="stat-label">进行中</div>
          <div class="stat-sub">待处理记录</div>
        </div>
      </div>
      <div class="stat-card card cyber-border">
        <div class="stat-icon-wrapper">
          <div class="stat-icon">📈</div>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.attributePoints }}</div>
          <div class="stat-label">属性总值</div>
          <div class="stat-sub">当前能力总点数</div>
        </div>
      </div>
      <div class="stat-card card cyber-border">
        <div class="stat-icon-wrapper">
          <div class="stat-icon">⚡</div>
        </div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.totalExperience }}</div>
          <div class="stat-label">总经验值</div>
          <div class="stat-sub">历史累积</div>
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
      
      <div class="attributes-grid grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-lg">
        <div v-for="(attr, index) in attributes" :key="index" class="attribute-card card">
          <div class="attribute-header">
            <h4 class="attribute-name">{{ attr.attr_name }}</h4>
            <div class="attribute-actions">
              <el-button size="small" @click="editAttribute(attr)">编辑</el-button>
              <el-button size="small" type="danger" @click="deleteAttribute(attr.attr_id)">删除</el-button>
            </div>
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
      
      <div class="tasks-list grid grid-cols-1 md:grid-cols-2 gap-lg">
        <div v-for="(task, index) in tasks" :key="index" class="task-card card">
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
              <el-button size="small" @click="viewTaskDetail(task.task_id)">查看详情</el-button>
              <el-button size="small" type="danger" @click="deleteTask(task.task_id)">删除</el-button>
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
      
      <div class="store-items grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-lg">
        <div v-for="(item, index) in shopItems" :key="index" class="store-item card">
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
    
    <!-- 系统币统计 -->
    <div class="coins-section">
      <div class="section-header">
        <h3>💰 系统币统计</h3>
      </div>
      
      <div class="coins-overview">
        <div class="stat-card">
          <div class="stat-icon">📊</div>
          <div class="stat-content">
            <div class="stat-value">{{ coinStats?.total_coins || 0 }}</div>
            <div class="stat-label">总获取</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">💸</div>
          <div class="stat-content">
            <div class="stat-value">{{ coinStats?.total_spent || 0 }}</div>
            <div class="stat-label">总支出</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">📈</div>
          <div class="stat-content">
            <div class="stat-value">{{ coinStats?.daily_average || 0 }}</div>
            <div class="stat-label">日均获取</div>
          </div>
        </div>
        <div class="stat-card">
          <div class="stat-icon">🏆</div>
          <div class="stat-content">
            <div class="stat-value">{{ coinStats?.highest_balance || 0 }}</div>
            <div class="stat-label">历史最高</div>
          </div>
        </div>
      </div>
      
      <!-- 系统币历史记录 -->
      <div class="coins-history">
        <h4>📋 近期收支记录</h4>
        <el-table v-if="coinHistory.length > 0" :data="coinHistory.slice(0, 5)" style="width: 100%">
          <el-table-column prop="transaction_type" label="类型" width="100"></el-table-column>
          <el-table-column prop="amount" label="金额" width="100"></el-table-column>
          <el-table-column prop="description" label="描述"></el-table-column>
          <el-table-column prop="created_at" label="时间" width="180"></el-table-column>
        </el-table>
        <div v-else class="empty-history">
          <div class="empty-icon">📝</div>
          <p>暂无收支记录</p>
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
    
    <!-- 编辑属性对话框 -->
    <el-dialog v-model="showEditAttributeDialog" title="编辑属性" width="500px">
      <el-form :model="editingAttribute" label-width="80px">
        <el-form-item label="属性名称">
          <el-input v-model="editingAttribute.attr_name" placeholder="例如：高数熟练度"></el-input>
        </el-form-item>
        <el-form-item label="当前值">
          <el-slider v-model="editingAttribute.attr_value" :min="0" :max="editingAttribute.max_value" :step="1"></el-slider>
        </el-form-item>
        <el-form-item label="最大值">
          <el-input-number v-model="editingAttribute.max_value" :min="10" :max="1000"></el-input-number>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="editingAttribute.description" type="textarea" placeholder="简要描述此属性"></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditAttributeDialog = false">取消</el-button>
        <el-button type="primary" @click="updateAttribute">保存</el-button>
      </template>
    </el-dialog>
    
    <!-- 任务详情对话框 -->
    <el-dialog v-model="showTaskDetailDialog" title="任务详情" width="600px">
      <div v-if="currentTask" class="task-detail">
        <h4>{{ currentTask.task_name }}</h4>
        <div class="detail-section">
          <div class="detail-item">
            <span class="detail-label">状态：</span>
            <el-tag :type="getTaskStatusType(currentTask.status)">{{ getTaskStatusText(currentTask.status) }}</el-tag>
          </div>
          <div class="detail-item">
            <span class="detail-label">优先级：</span>
            <span :class="'priority-' + currentTask.priority">{{ getPriorityText(currentTask.priority) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">预计时长：</span>
            <span>{{ currentTask.estimated_time || '未设置' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">关联属性：</span>
            <span>{{ currentTask.related_attrs || '未关联' }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">系统币奖励：</span>
            <span>+{{ currentTask.reward_coins || 0 }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">属性点数奖励：</span>
            <span>+{{ currentTask.attribute_points || 0 }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">创建时间：</span>
            <span>{{ formatDate(currentTask.created_at) }}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">更新时间：</span>
            <span>{{ formatDate(currentTask.updated_at) }}</span>
          </div>
          <div class="detail-item description">
            <span class="detail-label">描述：</span>
            <span>{{ currentTask.description || '暂无描述' }}</span>
          </div>
        </div>
        <div v-if="currentTask.proof_data" class="proof-section">
          <h5>任务证明：</h5>
          <div class="proof-content">{{ currentTask.proof_data.content }}</div>
          <div class="proof-time">{{ formatDate(currentTask.proof_data.timestamp) }}</div>
        </div>
      </div>
      <template #footer>
        <el-button @click="showTaskDetailDialog = false">关闭</el-button>
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
import { getUserStats } from '@/api/user'

// ==================== 响应式状态 ====================

// 系统统计数据
const systemData = reactive({
  coins: 0,  // 系统币余额
  totalExperience: 0, // 总经验
  level: 1, // 当前等级
  expProgress: 0, // 当前等级经验进度
  taskCompleted: 0,  // 已完成任务数
  taskInProgress: 0,  // 进行中任务数
  attributePoints: 0,  // 总属性点数
  consecutiveDays: 0,  // 连续学习天数
  completionRate: 0   // 任务完成率
})

// 系统币历史记录
const coinHistory = ref([])

// 系统币统计信息
const coinStats = ref(null)

// 用户属性列表
const attributes = ref([])

// 任务列表
const tasks = ref([])

// 商店商品列表
const shopItems = ref([])

// 新属性表单数据
const newAttribute = reactive({
  name: '',
  value: 0,
  description: ''
})

// 编辑属性表单数据
const editingAttribute = reactive({
  attr_id: '',
  attr_name: '',
  attr_value: 0,
  max_value: 100,
  description: ''
})

// 新任务表单数据
const newTask = reactive({
  title: '',
  attributeName: '',
  duration: '',
  priority: 'medium',
  attributePoints: 1,
  rewardCoins: 10
})

// 对话框状态
const showAddAttributeDialog = ref(false)
const showEditAttributeDialog = ref(false)
const showAddTaskDialog = ref(false)
const showTaskDetailDialog = ref(false)

// 任务详情数据
const currentTask = ref(null)

// 任务证明相关
const proofDialogVisible = ref(false)
const currentTaskForProof = ref(null)
const proofContent = ref('')

// ==================== 业务逻辑 ====================

/**
 * 加载系统币历史记录
 */
const loadCoinHistory = async () => {
  try {
    const response = await api.get('/api/coins/history')
    if (response.data.success && response.data.data) {
      coinHistory.value = response.data.data
    }
  } catch (error) {
    console.error('加载系统币历史记录失败:', error)
    // 不显示错误消息，避免影响用户体验
  }
}

/**
 * 加载系统币统计信息
 */
const loadCoinStats = async () => {
  try {
    const response = await api.get('/api/coins/stats')
    if (response.data.success && response.data.data) {
      coinStats.value = response.data.data
    }
  } catch (error) {
    console.error('加载系统币统计信息失败:', error)
    // 不显示错误消息，避免影响用户体验
  }
}

/**
 * 加载用户数据（包括任务、属性、商店等）
 */
const loadUserData = async () => {
  try {
    // 获取用户信息（包括余额）
    const profile = await api.get('/api/user/profile')
    if (profile.data.data) {
      systemData.coins = profile.data.data.balance || 0
    }
    
    // 获取用户统计信息
    const stats = await getUserStats()
    if (stats) {
      // 使用用户统计数据更新系统数据
      systemData.taskCompleted = stats.completed_tasks || 0
      systemData.taskInProgress = stats.in_progress_tasks || 0
      systemData.totalExperience = stats.total_experience || 0
      systemData.completionRate = stats.completion_rate || 0
      
      // 简单的等级计算逻辑：100经验一级
      systemData.level = Math.floor(systemData.totalExperience / 100) + 1
      systemData.expProgress = systemData.totalExperience % 100
      
      // 连续天数暂时从 profile 获取或后端 stats 返回
      systemData.consecutiveDays = stats.consecutive_days || 0
    }
    
    // 并行加载数据
    await Promise.all([
      loadTasks(),
      loadAttributes(),
      loadShopItems(),
      loadCoinHistory(),
      loadCoinStats()
    ])
  } catch (error) {
    console.error('加载用户数据失败:', error)
    ElMessage.error('加载数据失败')
  }
}

/**
 * 加载商店商品列表
 */
const loadShopItems = async () => {
  try {
    const response = await api.get('/api/shop/items')
    shopItems.value = response.data.data || []
  } catch (error) {
    console.error('加载商店商品失败:', error)
    ElMessage.error('加载商店商品失败')
    // API 调用失败时使用备用数据
    shopItems.value = [
      { item_id: 'item1', item_name: '小型能量药水', price: 50, category: '消耗品', description: '恢复10点属性值' },
      { item_id: 'item2', item_name: '中型能量药水', price: 150, category: '消耗品', description: '恢复30点属性值' },
      { item_id: 'item3', item_name: '大型能量药水', price: 300, category: '消耗品', description: '恢复50点属性值' },
      { item_id: 'item4', item_name: '任务加速器', price: 200, category: '工具', description: '减少任务完成时间20%' },
      { item_id: 'item5', item_name: '金币探测器', price: 350, category: '工具', description: '增加任务奖励金币15%' }
    ]
  }
}

/**
 * 加载用户属性列表
 */
  const loadAttributes = async () => {
    try {
      const response = await api.get('/api/attributes')
      // 确保attributes.value始终是数组
      attributes.value = Array.isArray(response.data?.data) ? response.data.data : []
    
    // 计算总属性点数
    systemData.attributePoints = attributes.value.reduce(
      (sum, attr) => sum + (attr.attr_value || 0), 
      0
    )
    } catch (error) {
      console.error('加载属性失败:', error)
      ElMessage.error('加载属性失败')
      // API 调用失败时设置默认值
      attributes.value = []
      systemData.attributePoints = 0
    }
  }

/**
 * 加载任务列表
 */
const loadTasks = async () => {
  try {
    const response = await api.get('/api/tasks')
    // 确保tasks.value始终是数组，正确访问后端返回的数据结构
    tasks.value = Array.isArray(response.data?.data?.tasks) ? response.data.data.tasks : []
    
    // 更新任务统计
    systemData.taskCompleted = tasks.value.filter(t => t.status === 'completed').length
    systemData.taskInProgress = tasks.value.filter(t => t.status === 'in_progress').length
  } catch (error) {
    console.error('加载任务失败:', error)
    ElMessage.error('加载任务失败')
    // API 调用失败时设置默认值
    tasks.value = []
    systemData.taskCompleted = 0
    systemData.taskInProgress = 0
  }
}

/**
 * 添加新属性
 */
const addAttribute = async () => {
  if (!newAttribute.name.trim()) {
    ElMessage.warning('请输入属性名称')
    return
  }
  
  try {
    const response = await api.post('/api/attributes', {
      attr_name: newAttribute.name,
      max_value: 100,
      description: newAttribute.description
    })
    
    // 重新加载属性列表
    await loadAttributes()
    
    showAddAttributeDialog.value = false
    ElMessage.success('属性添加成功')
    
    // 重置表单
    newAttribute.name = ''
    newAttribute.value = 0
    newAttribute.description = ''
  } catch (error) {
    console.error('添加属性失败:', error)
    ElMessage.error(error.response?.data?.detail || '添加属性失败')
  }
}

/**
 * 编辑属性
 */
const editAttribute = (attr) => {
  // 填充编辑表单数据
  editingAttribute.attr_id = attr.attr_id
  editingAttribute.attr_name = attr.attr_name
  editingAttribute.attr_value = attr.attr_value
  editingAttribute.max_value = attr.max_value || 100
  editingAttribute.description = attr.description || ''
  // 打开编辑对话框
  showEditAttributeDialog.value = true
}

/**
 * 更新属性
 */
const updateAttribute = async () => {
  if (!editingAttribute.attr_name.trim()) {
    ElMessage.warning('请输入属性名称')
    return
  }
  
  try {
    const response = await api.put(`/api/attributes/${editingAttribute.attr_id}`, {
      attr_name: editingAttribute.attr_name,
      attr_value: editingAttribute.attr_value,
      max_value: editingAttribute.max_value,
      description: editingAttribute.description
    })
    
    // 重新加载属性列表
    await loadAttributes()
    
    showEditAttributeDialog.value = false
    ElMessage.success('属性更新成功')
  } catch (error) {
    console.error('更新属性失败:', error)
    ElMessage.error(error.response?.data?.detail || '更新属性失败')
  }
}

/**
 * 删除属性
 */
const deleteAttribute = async (attr_id) => {
  try {
    await api.delete(`/api/attributes/${attr_id}`)
    
    // 重新加载属性列表
    await loadAttributes()
    
    ElMessage.success('属性删除成功')
  } catch (error) {
    console.error('删除属性失败:', error)
    ElMessage.error(error.response?.data?.detail || '删除属性失败')
  }
}

/**
 * 查看任务详情
 */
const viewTaskDetail = async (task_id) => {
  try {
    const response = await api.get(`/api/tasks/${task_id}`)
    if (response.data.success && response.data.data) {
      currentTask.value = response.data.data
      showTaskDetailDialog.value = true
    }
  } catch (error) {
    console.error('获取任务详情失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取任务详情失败')
  }
}

/**
 * 删除任务
 */
const deleteTask = async (task_id) => {
  try {
    const response = await api.delete(`/api/tasks/${task_id}`)
    if (response.data.success) {
      // 重新加载任务列表
      await loadTasks()
      ElMessage.success('任务删除成功')
    }
  } catch (error) {
    console.error('删除任务失败:', error)
    ElMessage.error(error.response?.data?.detail || '删除任务失败')
  }
}

/**
 * 获取任务状态对应的Element Plus标签类型
 */
const getTaskStatusType = (status) => {
  const statusMap = {
    pending: 'info',
    in_progress: 'warning',
    pending_evaluation: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return statusMap[status] || 'info'
}

/**
 * 获取任务状态的中文文本
 */
const getTaskStatusText = (status) => {
  const statusMap = {
    pending: '待开始',
    in_progress: '进行中',
    pending_evaluation: '待评估',
    completed: '已完成',
    failed: '未通过'
  }
  return statusMap[status] || '未知状态'
}

/**
 * 获取任务优先级的中文文本
 */
const getPriorityText = (priority) => {
  const priorityMap = {
    easy: '简单',
    medium: '中等',
    hard: '困难'
  }
  return priorityMap[priority] || '未知优先级'
}

/**
 * 格式化日期
 */
const formatDate = (dateString) => {
  if (!dateString) return '未设置'
  const date = new Date(dateString)
  return date.toLocaleString('zh-CN')
}

/**
 * 创建新任务
 */
const addTask = async () => {
  if (!newTask.title.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  
  try {
    // 构建关联属性字典（如果选择了属性）
    const relatedAttrs = newTask.attributeName ? {
      [attributes.value.find(a => a.attr_name === newTask.attributeName)?.attr_id]: 1
    } : {}
    
    const response = await api.post('/api/tasks', {
      task_name: newTask.title,
      description: '',
      related_attrs: relatedAttrs,
      estimated_time: parseInt(newTask.duration) || 30,
      reward_coins: newTask.rewardCoins
    })
    
    // 重新加载任务列表
    await loadTasks()
    
    showAddTaskDialog.value = false
    ElMessage.success('任务创建成功')
    
    // 重置表单
    newTask.title = ''
    newTask.attributeName = ''
    newTask.duration = ''
    newTask.priority = 'medium'
    newTask.attributePoints = 1
    newTask.rewardCoins = 10
  } catch (error) {
    console.error('创建任务失败:', error)
    ElMessage.error(error.response?.data?.detail || '创建任务失败')
  }
}

/**
 * 购买商店物品
 * @param {number} index - 商品在列表中的索引
 */
const purchaseItem = async (index) => {
  const item = shopItems.value[index]
  if (!item) return
  
  if (systemData.coins < (item.price || 0)) {
    ElMessage.warning('余额不足')
    return
  }
  
  try {
    await api.post(`/api/shop/purchase/${item.item_id || item.id}`)
    
    // 重新加载用户数据以更新余额
    await loadUserData()
    
    ElMessage.success('购买成功！')
  } catch (error) {
    console.error('购买失败:', error)
    ElMessage.error(error.response?.data?.detail || '购买失败')
  }
}

/**
 * 开始任务
 * @param {string} task_id - 任务ID
 */
const startTask = async (task_id) => {
  try {
    await api.put(`/api/tasks/${task_id}/status?status=in_progress`)
    await loadTasks()
    ElMessage.success('任务已开始')
  } catch (error) {
    console.error('更新任务状态失败:', error)
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

/**
 * 打开任务证明提交对话框
 * @param {string} task_id - 任务ID
 */
const openProofDialog = (task_id) => {
  const task = tasks.value.find(t => t.task_id === task_id)
  if (task) {
    currentTaskForProof.value = task
    proofContent.value = ''
    proofDialogVisible.value = true
  }
}

/**
 * 提交任务证明
 */
const submitTaskProof = async () => {
  if (!currentTaskForProof.value || !proofContent.value.trim()) {
    ElMessage.error('请填写任务证明内容')
    return
  }
  
  try {
    await api.post(`/api/tasks/${currentTaskForProof.value.task_id}/proof`, {
      proof_data: {
        content: proofContent.value.trim(),
        timestamp: new Date().toISOString()
      }
    })
    
    ElMessage.success('任务证明提交成功，请等待评估')
    proofDialogVisible.value = false
    
    // 重新加载任务列表
    await loadTasks()
  } catch (error) {
    console.error('提交任务证明失败:', error)
    ElMessage.error(error.response?.data?.detail || '提交任务证明失败')
  }
}

/**
 * 完成任务
 * @param {string} task_id - 任务ID
 */
const completeTask = async (task_id) => {
  try {
    const task = tasks.value.find(t => t.task_id === task_id)
    if (!task) {
      ElMessage.error('任务不存在')
      return
    }
    
    // 检查任务是否需要证明（根据难度或其他条件）
    if (task.estimated_time && task.estimated_time >= 120) {
      // 预计时间超过2小时的任务需要提交证明
      openProofDialog(task_id)
      } else {
        // 简单任务直接完成
      await api.put(`/api/tasks/${task_id}/status?status=completed`)
        await loadTasks()
      await loadUserData()  // 重新加载用户数据以更新余额
        ElMessage.success('任务完成！获得奖励')
    }
  } catch (error) {
    console.error('完成任务失败:', error)
    ElMessage.error(error.response?.data?.detail || '操作失败')
  }
}

// ==================== 生命周期 ====================

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
  flex-direction: column;
  gap: 20px;
  margin-bottom: 40px;
  padding-bottom: 25px;
  border-bottom: 1px solid var(--color-border);
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-main h2 {
  font-size: 2.2em;
  margin: 0;
  font-weight: 800;
  letter-spacing: -0.5px;
}

.home-header h2 .glitch {
  color: var(--color-primary-light);
  text-shadow: var(--shadow-glow);
  position: relative;
  display: inline-block;
}

.home-header h2 .dashboard {
  color: var(--color-text-muted);
  font-weight: 400;
  margin-left: 5px;
}

.user-level-badge {
  display: flex;
  align-items: center;
  gap: 12px;
  background: var(--color-bg-card);
  padding: 8px 16px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-border-cyber);
  box-shadow: var(--shadow-cyber);
}

.level-label {
  font-size: 0.75em;
  font-weight: 800;
  color: var(--color-text-muted);
  letter-spacing: 1px;
}

.level-value {
  font-size: 1.8em;
  font-weight: 900;
  color: var(--color-primary-light);
  font-family: var(--font-family-mono);
  line-height: 1;
}

.system-meta {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 30px;
}

.exp-bar-container {
  flex: 1;
  max-width: 600px;
}

.exp-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.8em;
  font-weight: 600;
  color: var(--color-text-secondary);
  margin-bottom: 6px;
  letter-spacing: 0.5px;
}

.exp-track {
  height: 6px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
  border: 1px solid var(--color-border-light);
}

.exp-fill {
  height: 100%;
  background: var(--grad-cyber);
  box-shadow: 0 0 10px var(--glow-primary);
  transition: width var(--transition-slow);
}

.system-status {
  display: flex;
  align-items: center;
  gap: 20px;
  background: var(--color-bg-glass);
  backdrop-filter: blur(10px);
  padding: 6px 16px;
  border-radius: var(--radius-full);
  border: 1px solid var(--color-border);
}

.status-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.75em;
  font-weight: 700;
  letter-spacing: 1px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: var(--color-success);
  box-shadow: 0 0 8px var(--color-success);
  animation: pulse 2s infinite;
}

.system-coins {
  display: flex;
  align-items: center;
  gap: 6px;
  font-weight: 700;
  font-size: 1.1em;
  color: var(--color-warning);
}

/* 概览统计卡片 */
.overview-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 40px;
}

.stat-card {
  padding: 24px;
  display: flex;
  align-items: flex-start;
  gap: 16px;
  background: var(--grad-surface);
  border: 1px solid var(--color-border);
  transition: all var(--transition-normal);
}

.stat-card:hover {
  transform: translateY(-4px);
  border-color: var(--color-border-cyber);
  box-shadow: var(--shadow-cyber);
}

.stat-icon-wrapper {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  font-size: 1.5em;
  border: 1px solid var(--color-border-light);
}

.stat-content {
  flex: 1;
}

.stat-value {
  font-size: 2.2em;
  font-weight: 800;
  line-height: 1;
  color: var(--color-text-primary);
  margin-bottom: 4px;
  font-family: var(--font-family-mono);
}

.stat-label {
  font-size: 0.85em;
  color: var(--color-text-secondary);
  font-weight: 600;
  margin-bottom: 2px;
}

.stat-sub {
  font-size: 0.7em;
  color: var(--color-text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 通用区块样式 */
.attributes-section,
.tasks-section,
.store-section,
.coins-section {
  margin-bottom: 40px;
  background: var(--color-bg-card);
  backdrop-filter: blur(20px);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-lg);
  padding: 30px;
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
  width: 4px;
  height: 100%;
  background: var(--grad-cyber);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 30px;
}

.section-header h3 {
  font-size: 1.6em;
  font-weight: 800;
  color: var(--color-text-primary);
  letter-spacing: -0.5px;
}

/* 属性卡片 */
.attributes-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}

.attribute-card {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 24px;
  transition: all var(--transition-normal);
}

.attribute-card:hover {
  transform: translateY(-4px);
  border-color: var(--color-border-cyber);
  background: var(--color-bg-secondary);
}

.attribute-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.attribute-name {
  font-size: 1.1em;
  font-weight: 700;
  color: var(--color-text-primary);
}

.attribute-level {
  font-size: 0.8em;
  font-weight: 800;
  color: var(--color-primary-light);
  background: var(--color-bg-primary);
  padding: 4px 10px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border-cyber);
}

.attribute-progress {
  margin-bottom: 16px;
}

.progress-bar {
  height: 8px;
  background: var(--color-bg-primary);
  border-radius: var(--radius-full);
  margin-bottom: 8px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--grad-cyber);
  transition: width 1s cubic-bezier(0.4, 0, 0.2, 1);
}

.attribute-value {
  font-size: 0.8em;
  color: var(--color-text-secondary);
  font-weight: 600;
  font-family: var(--font-family-mono);
}

.attribute-description {
  font-size: 0.85em;
  color: var(--color-text-muted);
  line-height: 1.5;
}

/* 任务卡片 */
.tasks-list {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 24px;
}

.task-card {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 24px;
  transition: all var(--transition-normal);
  border-left: 4px solid var(--color-primary);
}

.task-card:hover {
  transform: translateX(4px);
  border-color: var(--color-border-cyber);
  background: var(--color-bg-secondary);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.task-title {
  font-size: 1.15em;
  font-weight: 700;
  color: var(--color-text-primary);
}

.task-priority {
  font-size: 0.7em;
  font-weight: 800;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  text-transform: uppercase;
}

.task-priority.easy { color: var(--color-success); background: rgba(16, 185, 129, 0.1); }
.task-priority.medium { color: var(--color-warning); background: rgba(245, 158, 11, 0.1); }
.task-priority.hard { color: var(--color-error); background: rgba(239, 68, 68, 0.1); }

.task-info {
  display: flex;
  gap: 16px;
  margin-bottom: 16px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85em;
  color: var(--color-text-secondary);
  font-weight: 600;
}

.task-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.task-status {
  font-size: 0.75em;
  font-weight: 700;
  color: var(--color-text-muted);
}

.task-status.in_progress { color: var(--color-primary-light); }
.task-status.completed { color: var(--color-success); }

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