<template>
  <div class="home-container">
    <!-- 页面标题 -->
    <div class="settings-header">
      <div class="header-main flex justify-between items-center">
        <h1 class="glitch">虚空系统终端</h1>
        <div class="user-level-badge">
          <span class="level-label">等级</span>
          <span class="level-value">{{ systemData.level }}</span>
        </div>
      </div>
      
      <div class="system-meta mt-md">
        <div class="exp-bar-container">
          <div class="exp-info">
            <span>系统经验值</span>
            <span>{{ systemData.expProgress }} / 100</span>
          </div>
          <div class="exp-track">
            <div class="exp-fill" :style="{ width: systemData.expProgress + '%' }"></div>
          </div>
        </div>

        <div class="system-status">
          <div class="status-indicator">
            <div class="status-dot"></div>
            <span>实时连接中</span>
          </div>
          <div class="system-coins">
            <span class="coin-icon">💰</span>
            <span class="coin-count">{{ systemData.coins }} 虚空币 (VC)</span>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 核心数据概览 -->
    <div class="overview-grid mt-xl">
      <div class="void-card stat-card">
        <div class="stat-icon-wrapper">📊</div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.taskCompleted }}</div>
          <div class="stat-label">完成项目</div>
          <div class="stat-sub">率: {{ systemData.completionRate.toFixed(1) }}%</div>
        </div>
      </div>
      <div class="void-card stat-card">
        <div class="stat-icon-wrapper">🎯</div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.taskInProgress }}</div>
          <div class="stat-label">正在执行</div>
          <div class="stat-sub">待处理进程</div>
        </div>
      </div>
      <div class="void-card stat-card">
        <div class="stat-icon-wrapper">📈</div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.attributePoints }}</div>
          <div class="stat-label">属性极值</div>
          <div class="stat-sub">全维度能力指数</div>
        </div>
      </div>
      <div class="void-card stat-card">
        <div class="stat-icon-wrapper">⚡</div>
        <div class="stat-content">
          <div class="stat-value">{{ systemData.totalExperience }}</div>
          <div class="stat-label">累积熵值</div>
          <div class="stat-sub">历史总成就</div>
        </div>
      </div>
    </div>
    
    <!-- 属性面板 -->
    <div class="void-card attributes-section mt-xl">
      <div class="section-header">
        <h3>🧠 虚空属性矩阵</h3>
        <el-button type="primary" class="void-btn primary" @click="showAddAttributeDialog = true">
          <el-icon><Plus /></el-icon> 注入新属性
        </el-button>
      </div>
      
      <div class="attributes-grid mt-lg">
        <div v-for="(attr, index) in attributes" :key="index" class="attribute-item">
          <div class="attribute-header">
            <div class="attr-info">
              <h4 class="attribute-name">{{ attr.attr_name }}</h4>
              <div class="attribute-level">阶位 {{ Math.floor(attr.attr_value / 10) }}</div>
            </div>
            <div class="attribute-actions">
              <el-button link @click="editAttribute(attr)">编辑</el-button>
              <el-button link type="danger" @click="deleteAttribute(attr.attr_id)">卸载</el-button>
            </div>
          </div>
          
          <div class="attribute-progress">
            <div class="progress-track">
              <div class="progress-fill" :style="{ width: attr.attr_value + '%' }"></div>
            </div>
            <div class="attribute-value">{{ attr.attr_value }} / {{ attr.max_value || 100 }}</div>
          </div>
          
          <div class="attribute-description">{{ attr.description || '暂无数据描述' }}</div>
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
    <div class="void-card tasks-section mt-xl">
      <div class="section-header">
        <h3>⚔️ 任务序列控制台</h3>
        <el-button class="void-btn primary" @click="openAddTaskWithTab">
          <el-icon><EditPen /></el-icon> 发布新指令
        </el-button>
      </div>

      <!-- 任务分类标签 -->
      <div class="task-tabs-container mb-lg">
        <el-tabs v-model="activeTab" class="void-tabs">
          <el-tab-pane label="🌌 核心主线" name="main"></el-tab-pane>
          <el-tab-pane label="📅 轮回日常" name="daily"></el-tab-pane>
          <el-tab-pane label="🌿 边境支线" name="side"></el-tab-pane>
        </el-tabs>
      </div>

      <!-- 改进后的长条形任务列表：混合显示独立任务与任务组 -->
      <div class="tasks-list">
        <template v-for="item in displayItems" :key="item.type + '_' + (item.type === 'group' ? item.data.chain_id : item.data.task_id)">
          
          <!-- 任务组显示 -->
          <div v-if="item.type === 'group'" class="task-group-box mb-md">
            <div class="group-bar" :class="{ 'completed': item.data.completed_tasks > 0 && item.data.completed_tasks === item.data.total_tasks }" @click="toggleGroup(item.data.chain_id)">
              <div class="group-bg-fill" :style="{ width: `${item.data.total_tasks === 0 ? 0 : Math.round((item.data.completed_tasks / item.data.total_tasks) * 100)}%` }"></div>
              
              <div class="group-inner">
                <div class="group-main">
                  <div class="group-icon">🗂️</div>
                  <div class="group-text">
                    <span class="group-title">{{ item.data.chain_name }}</span>
                    <span class="group-meta">
                      同步进程: {{ item.data.completed_tasks }} / {{ item.data.total_tasks }}  
                      <span class="divider">|</span> 
                      完成度: {{ item.data.total_tasks === 0 ? 0 : Math.round((item.data.completed_tasks / item.data.total_tasks) * 100) }}%
                    </span>
                  </div>
                </div>
                <div class="group-actions">
                  <el-button link @click.stop="viewGroupDetail(item.data)">拓扑</el-button>
                  <el-button link type="danger" @click.stop="deleteTaskGroup(item.data.chain_id)">移除</el-button>
                  <el-icon class="toggle-arrow" :class="{ 'expanded': expandedGroups.has(item.data.chain_id) }"><ArrowDown /></el-icon>
                </div>
              </div>
            </div>
            
            <!-- 子任务列表 -->
            <el-collapse-transition>
              <div v-show="expandedGroups.has(item.data.chain_id)" class="group-children">
                <div v-for="task in item.subtasks" :key="task.task_id" class="child-task-row" :class="task.status" @click="viewTaskDetail(task.task_id)">
                  <div class="child-left">
                    <span class="child-indicator"></span>
                    <span class="child-name" :class="{'done': task.status === 'completed'}">{{ task.task_name || task.title }}</span>
                    <el-tag v-if="task.status === 'in_progress'" size="small" type="warning" class="void-tag primary">执行中</el-tag>
                  </div>
                  
                  <div class="child-right">
                    <el-tooltip v-if="isTaskLocked(task)" content="锁定" placement="top">
                      <el-button size="small" disabled plain>🔒</el-button>
                    </el-tooltip>
                    <template v-else>
                      <el-button v-if="task.status === 'pending'" size="small" class="void-btn secondary" @click.stop="startTask(task.task_id)">激活</el-button>
                      <el-button v-if="task.status === 'in_progress'" type="success" size="small" class="void-btn success" @click.stop="completeTask(task.task_id)">同步</el-button>
                    </template>
                  </div>
                </div>
              </div>
            </el-collapse-transition>
          </div>

          <!-- 独立任务显示 -->
          <div v-if="item.type === 'task'" class="task-row void-card mb-md" :class="item.data.status">
            <div class="task-info-main" @click="viewTaskDetail(item.data.task_id)">
              <div class="task-title-line">
                <h4 class="task-name">{{ item.data.task_name || item.data.title }}</h4>
                <div class="task-tags">
                  <el-tag v-if="item.data.is_optional" size="small" class="void-tag">支线</el-tag>
                  <el-tag v-if="item.data.is_daily" size="small" class="void-tag primary">每日</el-tag>
                </div>
              </div>
              <div class="task-meta-line">
                <span class="meta-item"><el-icon><Timer /></el-icon> {{ item.data.estimated_time }}m</span>
                <span class="meta-item"><el-icon><Coin /></el-icon> +{{ item.data.reward_coins }}</span>
                <span class="meta-item"><el-icon><DataAnalysis /></el-icon> +{{ item.data.attribute_points }}</span>
              </div>
            </div>
            
            <div class="task-ctrl">
              <el-tag :type="getTaskStatusType(item.data.status)" size="small" class="void-tag">
                {{ getTaskStatusText(item.data.status) }}
              </el-tag>
              
              <div class="task-btns">
                <el-tooltip v-if="isTaskLocked(item.data)" content="锁定">
                  <el-button size="small" disabled circle><el-icon><Lock /></el-icon></el-button>
                </el-tooltip>
                <template v-else>
                  <el-button v-if="item.data.status === 'pending'" size="small" class="void-btn primary" @click="startTask(item.data.task_id)">开始</el-button>
                  <el-button v-if="item.data.status === 'in_progress'" size="small" type="success" class="void-btn primary" @click="completeTask(item.data.task_id)">
                    {{ item.data.completion_type === 'ai_eval' ? '提交' : '完成' }}
                  </el-button>
                </template>
                <el-button size="small" link type="danger" @click="deleteTask(item.data.task_id)"><el-icon><Delete /></el-icon></el-button>
              </div>
            </div>
          </div>
        </template>
        
        <!-- 空状态 -->
        <div v-if="displayItems.length === 0" class="empty-tasks">
          <div class="empty-icon">📝</div>
          <p>暂无学习任务</p>
          <el-button type="info" size="small" @click="showAddTaskDialog = true">
            创建第一个任务
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 资源商店 -->
    <div class="void-card store-section mt-xl">
      <div class="section-header">
        <h3>🛒 虚空贸易站</h3>
        <div class="store-balance void-tag primary">
          能量储备: {{ systemData.coins }} VC
        </div>
      </div>
      
      <div class="store-grid">
        <div v-for="(item, index) in shopItems" :key="index" class="void-card item-card">
          <div class="item-icon">{{ item.icon || '📦' }}</div>
          <div class="item-info">
            <h4 class="item-name">{{ item.name }}</h4>
            <div class="item-desc">{{ item.description }}</div>
            <div class="item-price">
              <span class="price-val">💰 {{ item.price || 0 }}</span>
            </div>
          </div>
          <el-button 
            class="void-btn primary"
            :disabled="systemData.coins < (item.price || 0) || (item.quantity || 0) <= 0"
            size="small" 
            @click="purchaseItem(index)"
          >
            {{ systemData.coins < (item.price || 0) ? '余额不足' : (item.quantity || 0) <= 0 ? '售罄' : '兑换' }}
          </el-button>
        </div>
      </div>
    </div>
    
    <!-- 系统币统计 -->
    <div class="void-card coins-section mt-xl">
      <div class="section-header">
        <h3>💰 资源收支报表</h3>
      </div>
      
      <div class="coins-summary">
        <div class="summary-item">
          <span class="label">累计获取</span>
          <span class="value">{{ coinStats?.total_coins || 0 }}</span>
        </div>
        <div class="summary-item">
          <span class="label">项目分红</span>
          <span class="value">{{ coinStats?.daily_average || 0 }}</span>
        </div>
      </div>
      
      <div class="coins-history mt-lg">
        <h4 class="history-title">数据同步历史</h4>
        <el-table :data="coinHistory.slice(0, 5)" class="void-table">
          <el-table-column prop="transaction_type" label="类别" width="100"></el-table-column>
          <el-table-column prop="amount" label="分值" width="100"></el-table-column>
          <el-table-column prop="description" label="描述项"></el-table-column>
        </el-table>
      </div>
    </div>
    
    <!-- 属性与任务指令对话框 -->
    <el-dialog v-model="showAddAttributeDialog" title="注入新属性" width="500px" class="void-dialog-themed">
      <el-form :model="newAttribute" label-width="100px" class="mt-md">
        <el-form-item label="核心名称">
          <el-input v-model="newAttribute.name" class="void-input" placeholder="例如：高数逻辑能力"></el-input>
        </el-form-item>
        <el-form-item label="初始量级">
          <el-slider v-model="newAttribute.value"></el-slider>
        </el-form-item>
        <el-form-item label="维度描述">
          <el-input v-model="newAttribute.description" type="textarea" class="void-input" placeholder="输入属性定义..."></el-input>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-sm">
          <el-button class="void-btn secondary" @click="showAddAttributeDialog = false">取消</el-button>
          <el-button class="void-btn primary" @click="addAttribute">注入</el-button>
        </div>
      </template>
    </el-dialog>
    
    <el-drawer v-model="showTaskDetailDialog" :title="currentTask ? currentTask.task_name : '任务详情'" size="500px" direction="rtl" class="void-drawer-themed" append-to-body>
      <div v-if="currentTask" class="task-detail-content">
        <div class="detail-header flex justify-between items-center mb-lg">
          <el-tag :type="getTaskStatusType(currentTask.status)" class="void-tag primary" size="large">{{ getTaskStatusText(currentTask.status) }}</el-tag>
          <div class="priority-label" :class="currentTask.priority">{{ getPriorityText(currentTask.priority) }}</div>
        </div>

        <div class="detail-void-card void-card mb-lg">
          <div class="detail-grid">
            <div class="det-item">
              <span class="det-label">周期/预计:</span>
              <span class="det-value">{{ currentTask.estimated_time || 0 }}m</span>
            </div>
            <div class="det-item">
              <span class="det-label">同步点数:</span>
              <span class="det-value">+{{ currentTask.reward_coins }} VC | +{{ currentTask.attribute_points }} AP</span>
            </div>
          </div>
          <div class="det-full mt-md">
            <span class="det-label">关联矩阵:</span>
            <span class="det-value">{{ getRelatedAttrsText(currentTask.related_attrs) }}</span>
          </div>
        </div>

        <div class="detail-desc mb-xl">
          <div class="section-tag mb-sm">指令详情</div>
          <p class="desc-text">{{ currentTask.description || 'VOID_DATA_MISSING' }}</p>
        </div>

        <div v-if="currentTask.ai_suggestion" class="void-think-box mt-lg">
          <div class="think-header mb-sm">🤖 虚空评定反馈</div>
          <div class="think-content">{{ currentTask.ai_suggestion.feedback }}</div>
        </div>
      </div>
    </el-drawer>
    
    <!-- 创建任务对话框 -->
    <el-dialog v-model="showAddTaskDialog" :title="isChainMode ? '新阶段：虚空任务组' : '手动指令：创建记录'" width="650px" class="void-dialog" append-to-body>
      <div class="mode-toggle">
        <el-radio-group v-model="isChainMode" size="large" @change="handleModeChange">
          <el-radio-button :label="false">单一任务</el-radio-button>
          <el-radio-button :label="true">虚空任务组</el-radio-button>
        </el-radio-group>
      </div>

      <el-form :model="newTask" label-width="100px" style="margin-top: 20px;">
        <el-form-item :label="isChainMode ? '组名称' : '任务名称'">
          <el-input v-model="newTask.title" :placeholder="isChainMode ? '例如：深入掌握高等数学' : '例如：完成高数第三章练习'"></el-input>
        </el-form-item>

        <template v-if="!isChainMode">
          <el-form-item label="关联属性">
            <el-select v-model="newTask.attrId" placeholder="选择关联属性（可选）" clearable style="width:100%">
              <el-option v-for="attr in attributes" :key="attr.attr_id" :label="attr.attr_name" :value="attr.attr_id"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item label="任务描述">
            <el-input v-model="newTask.description" type="textarea" :rows="2" placeholder="简要描述任务内容"></el-input>
          </el-form-item>
          <el-form-item label="前置任务">
            <el-select v-model="newTask.prerequisites" multiple collapse-tags placeholder="选择必须先完成的任务(可选)" style="width:100%">
              <el-option 
                v-for="task in tasks.filter(t => t.status !== 'completed')" 
                :key="task.task_id" 
                :label="task.task_name" 
                :value="task.task_id"
              ></el-option>
            </el-select>
          </el-form-item>
          <div class="form-row grid grid-cols-2 gap-md">
            <el-form-item label="预计时长(分)">
              <el-input-number v-model="newTask.duration" :min="1" :max="480" style="width:100%"></el-input-number>
            </el-form-item>
            <el-form-item label="难度等级">
              <el-select v-model="newTask.priority" style="width:100%">
                <el-option label="🟢 简单" value="easy"></el-option>
                <el-option label="🟡 中等" value="medium"></el-option>
                <el-option label="🔴 困难" value="hard"></el-option>
              </el-select>
            </el-form-item>
          </div>
          <el-form-item label="任务属性">
            <el-radio-group v-model="newTask.taskType">
              <el-radio label="main">🌌 主线</el-radio>
              <el-radio label="daily">📅 每日</el-radio>
              <el-radio label="side">🌿 支线</el-radio>
            </el-radio-group>
            <div class="mt-sm">
              <el-checkbox v-model="newTask.isDaily" label="映射到每日页面 (跨模块同步)"></el-checkbox>
              <el-checkbox v-model="newTask.isOptional" label="标记为支线选做"></el-checkbox>
            </div>
          </el-form-item>
          <el-form-item label="奖励配置">
            <div class="flex gap-md">
              <el-input-number v-model="newTask.attributePoints" :min="0" :max="50" controls-position="right">
                <template #prefix>📊</template>
              </el-input-number>
              <el-input-number v-model="newTask.rewardCoins" :min="0" :max="1000" controls-position="right">
                <template #prefix>💰</template>
              </el-input-number>
            </div>
          </el-form-item>
          
          <el-divider content-position="left">完成挑战</el-divider>
          <el-form-item label="确认方式">
            <el-select v-model="newTask.completionType" style="width:100%">
              <el-option label="直接点击完成" value="simple"></el-option>
              <el-option label="🤖 AI 自动化评判" value="ai_eval"></el-option>
            </el-select>
          </el-form-item>
          <el-form-item v-if="newTask.completionType === 'ai_eval'" label="评判标准">
            <el-input v-model="newTask.completionCriteria" type="textarea" :rows="3" placeholder="描述AI应根据什么标准来评判你的成果（如：正确率80%以上）"></el-input>
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="任务组模式">
            <el-checkbox v-model="newTask.isAIEnabled">使用 AI 进行阶段自动拆解</el-checkbox>
          </el-form-item>
          <el-form-item label="任务组说明">
            <el-input v-model="newTask.description" type="textarea" :rows="2" placeholder="对整个任务组的简要描述"></el-input>
          </el-form-item>
          <el-form-item v-if="newTask.isAIEnabled" label="AI 引导目标">
            <el-input v-model="newTask.targetGoal" type="textarea" :rows="5" placeholder="详细描述你想达成的目标，AI 将据此为您拆解任务组步骤..."></el-input>
          </el-form-item>
          <el-form-item v-else label="手动目标">
            <el-input v-model="newTask.targetGoal" type="textarea" :rows="3" placeholder="手动描述此任务组的最终目的（仅作记录）"></el-input>
          </el-form-item>
          <div class="ai-tip">
            <p>💡 提示：AI 将自动生成 5-10 个有关联的子任务，并为你配置奖励。</p>
          </div>
        </template>
      </el-form>
      <template #footer>
        <el-button @click="showAddTaskDialog = false">取消</el-button>
        <el-button type="primary" @click="addTask" :loading="isEvaluating">
          {{ isChainMode ? '创建任务组' : '发布任务' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- AI 评判确认对话框 -->
    <el-dialog v-model="aiReviewVisible" title="🤖 提交 AI 虚空评判" width="550px">
      <div v-if="currentTaskForAI">
        <div class="eval-header">
          <h4>{{ currentTaskForAI.task_name }}</h4>
          <p class="criteria-label">评判标准：{{ currentTaskForAI.completion_criteria?.criteria || '无明确标准' }}</p>
        </div>
        <el-input
          v-model="aiReviewContent"
          type="textarea"
          :rows="6"
          placeholder="请详尽描述你完成任务的情况 (支持 Markdown 格式)..."
        ></el-input>
        <div class="media-urls mt-md">
          <p class="section-label">媒体链接 (图片/链接，每行一个)：</p>
          <el-input
            v-model="aiReviewMedia"
            type="textarea"
            :rows="3"
            placeholder="例如：https://image.com/proof.png"
          ></el-input>
        </div>
      </div>
      <template #footer>
        <el-button @click="aiReviewVisible = false">暂不提交</el-button>
        <el-button type="primary" @click="submitAIReview" :loading="isEvaluating">提交 AI 评核</el-button>
      </template>
    </el-dialog>
  </div>


  <!-- 任务组详情与拓扑图抽屉 -->
  <el-drawer v-model="showGroupDetailDialog" :title="'🗂️ 阶段任务集：' + (currentGroup ? currentGroup.chain_name : '')" size="600px" direction="rtl" class="void-drawer" append-to-body>
    <div v-if="currentGroup" class="task-detail">
      <div class="task-header-detail flex justify-between items-center mb-lg">
        <div>
          <el-tag type="primary" size="large" effect="dark">进度 {{ currentGroup.completed_tasks }}/{{ currentGroup.total_tasks }}</el-tag>
        </div>
      </div>
      <div class="detail-section mb-xl p-md" style="background: rgba(0, 255, 204, 0.05); border: 1px solid rgba(0, 255, 204, 0.2); border-radius: 8px;">
        <div class="detail-item full-width description">
          <span class="detail-label text-primary" style="font-weight: bold;">【阶段序列总目标与策略】</span>
          <p class="mt-sm" style="line-height: 1.8; font-size: 1.05em; color: var(--color-text-primary);">{{ currentGroup.description || '由系统记录的具体说明内容...' }}</p>
        </div>
      </div>
      
      <div class="topology-section mt-md">
        <h5 class="mb-md text-primary" style="font-size: 1.2em; border-bottom: 1px solid var(--color-border); padding-bottom: 10px;">🌲 溯源核心阶段拓扑网络</h5>
        <div class="tree-display">
          <div v-for="(t, index) in currentChainTasks" :key="t.task_id" class="tree-node-visual" :class="'status-' + t.status">
            <div class="node-timeline-connector" v-if="index < currentChainTasks.length - 1"></div>
            <div class="node-visual-content card" @click="viewTaskDetail(t.task_id)">
              <div class="node-visual-header flex justify-between items-center">
                <span class="node-name" style="font-size: 1.1em; font-weight: 600;">
                  <span class="node-icon mr-sm">
                    {{ t.status === 'completed' ? '🏆' : (t.status === 'in_progress' ? '🔥' : '⏳') }}
                  </span>
                  {{ t.task_name }}
                </span>
                <el-tag size="small" :type="getTaskStatusType(t.status)" :effect="t.status === 'in_progress' ? 'dark' : 'plain'">
                  {{ getTaskStatusText(t.status) }}
                </el-tag>
              </div>
              <div class="node-visual-desc mt-sm text-sm" style="color: var(--color-text-secondary); display: -webkit-box; -webkit-line-clamp: 2; line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;">
                {{ t.description || '点击查看详情任务描述...' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
/**
 * Home Component - System Dashboard
 * -----------------------------------
 * 系统主页，展示用户属性、任务、商店等核心功能
 */

import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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

const activeTab = ref('main')

// 过滤后的长条形显示列表：混合任务组和独立任务
const expandedGroups = ref(new Set())
const showGroupDetailDialog = ref(false)
const currentGroup = ref(null)

const toggleGroup = (groupId) => {
  if (expandedGroups.value.has(groupId)) {
    expandedGroups.value.delete(groupId)
  } else {
    expandedGroups.value.add(groupId)
  }
}

const viewGroupDetail = (group) => {
  currentGroup.value = group
  currentChainTasks.value = tasks.value
    .filter(t => t.chain_id === group.chain_id)
    .sort((a, b) => (a.chain_order || 0) - (b.chain_order || 0))
  showGroupDetailDialog.value = true
}

const displayItems = computed(() => {
  if (!tasks.value) return [];
  
  const items = [];
  const processedChains = new Set();
  
  // 先把任务按分类标签过滤
  const typeFilteredTasks = tasks.value.filter(t => {
    if (activeTab.value === 'daily') {
      return t.task_type === 'daily' || t.is_daily || t.data_tags?.includes('daily');
    }
    if (activeTab.value === 'side') return t.task_type === 'side';
    return t.task_type === 'main' || !t.task_type;
  });

  // 遍历这些任务
  typeFilteredTasks.forEach(task => {
    if (!task.chain_id) {
      items.push({ type: 'task', data: task });
    } else {
      if (!processedChains.has(task.chain_id)) {
        processedChains.add(task.chain_id);
        const chainInfo = taskChains.value.find(c => c.chain_id === task.chain_id);
        if (chainInfo) {
          // 获取该组所有任务进行排序，并计算动态进度
          const subtasks = tasks.value
            .filter(t => t.chain_id === task.chain_id)
            .sort((a, b) => (a.chain_order || 0) - (b.chain_order || 0));
          
          const dynamicTotalTasks = subtasks.length;
          const dynamicCompletedTasks = subtasks.filter(t => t.status === 'completed').length;
          
          let currentSubtasks = [];
          const activeInChain = subtasks.find(t => t.status !== 'completed');
          if (activeInChain) {
            currentSubtasks = [activeInChain];
          } else {
            const lastInChain = subtasks[subtasks.length - 1];
            if (lastInChain) {
               currentSubtasks = [lastInChain];
            }
          }

          items.push({ 
            type: 'group', 
            data: { ...chainInfo, total_tasks: dynamicTotalTasks, completed_tasks: dynamicCompletedTasks }, 
            subtasks: currentSubtasks 
          });
        } else {
            // 如果找不到对应的 chain_info，可能出了点问题，作为独立任务显示
            items.push({ type: 'task', data: task });
        }
      }
    }
  });

  // 再按状态排序 (将已完成的放置最后，进行中的放前面)
  return items.sort((a, b) => {
    const statusOrder = { 'in_progress': 0, 'pending': 1, 'pending_evaluation': 2, 'completed': 3, 'failed': 4 };
    const getStatus = (item) => {
       if (item.type === 'task') return item.data.status;
       // group status
       if (item.subtasks.some(s => s.status === 'in_progress')) return 'in_progress';
       if (item.subtasks.every(s => s.status === 'completed')) return 'completed';
       return 'pending';
    };
    return (statusOrder[getStatus(a)] || 0) - (statusOrder[getStatus(b)] || 0);
  });
});

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

// 对话框状态
const showAddAttributeDialog = ref(false)
const showEditAttributeDialog = ref(false)
const showAddTaskDialog = ref(false)
const showTaskDetailDialog = ref(false)
const aiReviewVisible = ref(false)
const currentTaskForAI = ref(null)
// 新建任务表单状态
const newTask = reactive({
  title: '',
  description: '',
  attrId: '',
  duration: 30,
  priority: 'medium',
  attributePoints: 5,
  rewardCoins: 10,
  categoryId: null,
  completionType: 'simple',
  completionCriteria: '',
  targetGoal: '',
  prerequisites: [],
  isOptional: false,
  isDaily: false,
  isAIEnabled: true,
  taskType: 'main'
})

/**
 * 确保弹窗在不同 Tab 下都能正常激活
 */
const openAddTaskWithTab = () => {
  // 根据当前 activeTab 预设任务类型
  newTask.taskType = activeTab.value === 'daily' || activeTab.value === 'side' ? activeTab.value : 'main'
  showAddTaskDialog.value = true
}

const handleModeChange = (val) => {
  isChainMode.value = val
}

const aiReviewContent = ref('')
const aiReviewMedia = ref('')
const isChainMode = ref(false) // 任务创建模式：单任务/任务链
const taskChains = ref([])    // 任务链列表

// 任务详情数据
const currentTask = ref(null)

// 任务证明相关
const isEvaluating = ref(false)
const currentChainTasks = ref([]) // 当前查看的任务链所有任务

// ==================== 前置卡点逻辑 ====================
/**
 * 检查任务是否由于前置条件未完成而被锁定
 */
const isTaskLocked = (task) => {
  if (!task || !task.prerequisites || task.prerequisites.length === 0) return false;
  // 如果任何一个前置任务没有完成，则返回 true (锁定)
  return task.prerequisites.some(prereqId => {
    const prereqTask = tasks.value.find(t => t.task_id === prereqId);
    return !prereqTask || prereqTask.status !== 'completed';
  });
}

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
      loadTaskChains(),
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
 * 加载任务链列表
 */
const loadTaskChains = async () => {
  try {
    const response = await api.get('/api/task-chains')
    taskChains.value = response.data.data?.chains || []
  } catch (error) {
    console.error('加载任务链失败:', error)
  }
}

/**
 * 加载任务列表
 */
const loadTasks = async () => {
  try {
    const response = await api.get('/api/tasks')
    tasks.value = Array.isArray(response.data?.data?.tasks) ? response.data.data.tasks : []
    
    // 更新统计
    systemData.taskCompleted = tasks.value.filter(t => t.status === 'completed').length
    systemData.taskInProgress = tasks.value.filter(t => t.status === 'in_progress').length
  } catch (error) {
    console.error('加载任务失败:', error)
    ElMessage.error('加载任务失败')
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
      const taskObj = response.data.data.task || response.data.data
      currentTask.value = taskObj
      
      // 如果属于任务链，获取该链所有任务
      if (taskObj.chain_id) {
        currentChainTasks.value = tasks.value
          .filter(t => t.chain_id === taskObj.chain_id)
          .sort((a, b) => (a.chain_order || 0) - (b.chain_order || 0))
      } else {
        currentChainTasks.value = []
      }
      
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
      // 重新加载任务列表和任务链进度
      await loadTasks()
      await loadTaskChains()
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
    'pending': 'info',
    'in_progress': '',
    'pending_evaluation': 'warning',
    'completed': 'success',
    'failed': 'danger'
  }
  return statusMap[status] || 'info'
}

/**
 * 获取任务状态的中文文本
 */
const getTaskStatusText = (status) => {
  const statusMap = {
    'pending': '等待开始',
    'in_progress': '进行中',
    'pending_evaluation': '待 AI 评估',
    'completed': '已完成',
    'failed': '失败'
  }
  return statusMap[status] || status
}

/**
 * 获取任务优先级的中文文本
 */
const getPriorityText = (priority) => {
  const priorityMap = {
    'easy': '简单',
    'medium': '中等',
    'hard': '困难'
  }
  return priorityMap[priority] || priority
}

/**
 * 将关联属性字典 {attr_id: weight} 转为可读属性名列表
 */
const getRelatedAttrsText = (relatedAttrs) => {
  if (!relatedAttrs || typeof relatedAttrs !== 'object' || Object.keys(relatedAttrs).length === 0) {
    return '未关联'
  }
  const names = Object.keys(relatedAttrs).map(attrId => {
    const found = attributes.value.find(a => a.attr_id === attrId)
    return found ? found.attr_name : null
  }).filter(Boolean)
  return names.length > 0 ? names.join('、') : '未关联'
}

/**
 * 获取前置任务名称列表
 */
const getPrerequisitesNames = (prereqIds) => {
  if (!prereqIds || !Array.isArray(prereqIds) || prereqIds.length === 0) return ''
  return prereqIds.map(id => {
    const t = tasks.value.find(task => task.task_id === id)
    return t ? t.task_name : '未知任务'
  }).join(', ')
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
 * 获取任务链名称
 */
const getChainName = (chainId) => {
  if (!chainId) return ''
  const chain = taskChains.value.find(c => c.chain_id === chainId)
  return chain ? chain.chain_name : '未知任务组'
}

const deleteTaskGroup = async (chainId) => {
  try {
    await ElMessageBox.confirm('确定要删除整个任务组吗？系统会连同该组下的所有子任务一起删除！', '严重警告', {
      type: 'warning',
      confirmButtonText: '确定删除',
      cancelButtonText: '取消'
    })
    const response = await api.delete(`/api/task-chains/${chainId}`)
    if (response.data.success) {
      // 从已展开的组中移除
      expandedGroups.value.delete(chainId)
      await loadTaskChains()
      await loadTasks()
      ElMessage.success('任务组及子任务删除成功')
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除任务组失败:', error)
      ElMessage.error('删除任务组失败')
    }
  }
}

/**
 * 创建新任务或任务组
 */
const addTask = async () => {
  // 模式 1：创建任务组（AI生成）
  if (isChainMode.value) {
    if (!newTask.title.trim()) {
      ElMessage.warning('请输入名称')
      return
    }
    try {
      await api.post('/api/task-chains', {
        chain_name: newTask.title,
        description: newTask.description,
        target_goal: newTask.isAIEnabled ? newTask.targetGoal : null
      })
      if (newTask.isAIEnabled) {
        ElMessage.success('任务组创建中，请稍等 AI 生成子任务...')
      } else {
        ElMessage.success('任务组创建成功')
      }
      showAddTaskDialog.value = false
      await loadTaskChains()
      await loadTasks()
    } catch (error) {
      ElMessage.error('任务组创建失败')
    }
    return
  }

  // 模式 2：创建单任务
  if (!newTask.title.trim()) {
    ElMessage.warning('请输入任务名称')
    return
  }
  
  try {
    const relatedAttrs = newTask.attrId ? { [newTask.attrId]: 1 } : {}
    
    await api.post('/api/tasks', {
      task_name: newTask.title,
      description: newTask.description,
      related_attrs: relatedAttrs,
      estimated_time: newTask.duration,
      reward_coins: newTask.rewardCoins,
      priority: newTask.priority,
      attribute_points: newTask.attributePoints,
      category_id: newTask.categoryId,
      completion_type: newTask.completionType,
      completion_criteria: { criteria: newTask.completionCriteria },
      prerequisites: newTask.prerequisites,
      task_type: newTask.taskType,
      is_optional: newTask.isOptional ? 1 : 0,
      is_daily: newTask.isDaily ? 1 : 0
    })
    
    await loadTasks()
    showAddTaskDialog.value = false
    ElMessage.success('任务创建成功！')
    
    // 重置
    Object.assign(newTask, {
      title: '', attrId: '', description: '', duration: 30,
      priority: 'medium', attributePoints: 5, rewardCoins: 10,
      categoryId: null,
      completionType: 'simple', completionCriteria: '', targetGoal: '',
      prerequisites: [], taskType: activeTab.value, isOptional: false, isDaily: false,
      isAIEnabled: true
    })
  } catch (error) {
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
    // 根据 completion_type 判断
    if (task.completion_type === 'ai_eval') {
      openAIReviewDialog(task_id)
    } else {
      await api.put(`/api/tasks/${task_id}/status?status=completed`)
      await loadTasks()
      await loadUserData()
      ElMessage.success('任务完成！')
    }
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

/**
 * 打开 AI 评判对话框
 */
const openAIReviewDialog = (task_id) => {
  const task = tasks.value.find(t => t.task_id === task_id)
  if (task) {
    currentTaskForAI.value = task
    aiReviewContent.value = ''
    aiReviewVisible.value = true
  }
}

/**
 * 提交 AI 评判
 */
const submitAIReview = async () => {
  if (!aiReviewContent.value.trim()) {
    ElMessage.warning('请输入完成描述')
    return
  }
  isEvaluating.value = true
  try {
    const resp = await api.post(`/api/tasks/${currentTaskForAI.value.task_id}/ai-evaluate`, {
      submission: aiReviewContent.value,
      submission_type: 'markdown',
      media_urls: aiReviewMedia.value.split('\n').filter(l => l.trim().startsWith('http'))
    })
    const evalData = resp.data.data
    if (evalData.status === 'pass') {
      ElMessage.success(`AI 评定通过！得分: ${evalData.score}`)
    } else {
      ElMessage.warning(`AI 评定未通过。反馈：${evalData.feedback}`)
    }
    aiReviewVisible.value = false
    await loadTasks()
  } catch (error) {
    ElMessage.error('AI 评估请求失败')
  } finally {
    isEvaluating.value = false
  }
}

// 组件挂载时加载数据
onMounted(async () => {
    // 仅调用一次 loadUserData，它会并行启动所有子加载函数
    await loadUserData()
})
</script>

<style scoped>
.home-container {
  padding: var(--spacing-lg);
  max-width: 1400px;
  margin: 0 auto;
}

/* Header & Meta */
.settings-header {
  margin-bottom: var(--spacing-xl);
  padding: var(--spacing-xl);
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  border: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  position: relative;
  overflow: hidden;
}

.glitch {
  font-size: 2.2rem;
  font-weight: 800;
  letter-spacing: -1px;
  background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  margin: 0;
}

.user-level-badge {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 80px;
  height: 80px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

.level-label {
  font-size: 0.7rem;
  font-weight: 800;
  color: var(--text-muted);
  text-transform: uppercase;
}

.level-value {
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-primary);
  font-family: var(--font-family-mono);
  line-height: 1;
}

.system-meta {
  display: flex;
  gap: var(--spacing-xl);
  align-items: flex-end;
  flex-wrap: wrap;
}

.exp-bar-container {
  flex: 1;
  min-width: 300px;
}

.exp-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  font-family: var(--font-family-mono);
  color: var(--text-secondary);
  margin-bottom: var(--spacing-sm);
}

.exp-track {
  height: 8px;
  background: var(--bg-tertiary);
  border-radius: var(--radius-full);
  overflow: hidden;
}

.exp-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--color-primary), var(--color-primary-light));
  transition: width var(--transition-slow);
}

.system-status {
  display: flex;
  gap: var(--spacing-lg);
  align-items: center;
  padding: 8px 20px;
  background: var(--bg-secondary);
  border-radius: var(--radius-full);
  border: 1px solid var(--border-color);
}

.status-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: var(--color-success);
  box-shadow: 0 0 10px var(--color-success);
}

/* Stats */
.overview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: var(--spacing-lg);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: var(--spacing-lg);
  padding: var(--spacing-xl);
}

.stat-icon-wrapper {
  font-size: 2.2rem;
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-tertiary);
  border-radius: var(--radius-lg);
  color: var(--color-primary);
}

.stat-value {
  font-size: 2.2rem;
  font-weight: 800;
  line-height: 1;
  font-family: var(--font-family-mono);
}

/* Attributes */
.attributes-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--spacing-xl);
}

.attribute-item {
  padding: var(--spacing-lg);
  background: var(--bg-secondary);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
}

/* Tasks */
.task-group-box {
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--bg-secondary);
}

.group-bar {
  position: relative;
  padding: var(--spacing-lg);
  cursor: pointer;
}

.group-bg-fill {
  position: absolute;
  top: 0; left: 0; bottom: 0;
  background: var(--color-primary);
  opacity: 0.08;
  transition: width var(--transition-slow);
}

.group-children {
  padding: var(--spacing-sm) var(--spacing-lg) var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  background: var(--bg-tertiary);
}

.child-task-row {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-md);
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}

.task-row {
  display: flex;
  justify-content: space-between;
  padding: var(--spacing-lg) var(--spacing-xl);
  border-left: 4px solid var(--color-primary);
}

/* Store */
.store-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: var(--spacing-xl);
}

.item-card {
  text-align: center;
  padding: var(--spacing-xl);
}

.item-icon {
  font-size: 3.5rem;
  margin-bottom: var(--spacing-lg);
}

/* Financials */
.coins-summary {
  display: flex;
  gap: var(--spacing-xl);
}

.summary-item .value {
  font-size: 2.2rem;
  font-weight: 800;
  font-family: var(--font-family-mono);
}

/* Responsive */
@media (max-width: 768px) {

.detail-label {
  font-size: 0.8em;
  font-weight: 700;
  color: var(--color-text-muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  min-width: 100px;
  flex-shrink: 0;
}

/* 优先级颜色 */
.priority-easy  { color: var(--color-success); font-weight: 700; }
.priority-medium { color: var(--color-warning); font-weight: 700; }
.priority-hard  { color: var(--color-error);   font-weight: 700; }

/* 奖励徽章 */
.reward-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: var(--radius-full);
  font-weight: 700;
  font-size: 0.95em;
  font-family: var(--font-family-mono);
}

.reward-badge.coin {
  background: rgba(245, 158, 11, 0.15);
  color: var(--color-warning);
  border: 1px solid rgba(245, 158, 11, 0.3);
}

.reward-badge.attr {
  background: rgba(99, 102, 241, 0.15);
  color: var(--color-primary-light);
  border: 1px solid rgba(99, 102, 241, 0.3);
}

/* 任务证明区块 */
.proof-section {
  margin-top: 16px;
  padding: 16px;
  background: var(--color-bg-tertiary);
  border-radius: var(--radius-md);
  border: 1px solid var(--border-color);
}

.proof-section h5 {
  font-size: 0.9em;
  font-weight: 700;
  color: var(--color-primary-light);
  margin: 0 0 10px 0;
}

.proof-content {
  font-size: 0.9em;
  color: var(--color-text-secondary);
  line-height: 1.6;
  white-space: pre-wrap;
}

.proof-time {
  margin-top: 8px;
  font-size: 0.78em;
  color: var(--color-text-muted);
  font-family: var(--font-family-mono);
}
/* 任务链与进度控制样式 */
.task-card.chain-member {
  border-left: 4px solid var(--color-primary-light);
  background: linear-gradient(to right, rgba(0, 255, 204, 0.05), transparent);
}

.chain-icon {
  margin-right: 8px;
  filter: drop-shadow(0 0 5px var(--color-primary));
}

.reward .sep {
  margin: 0 8px;
  opacity: 0.3;
}

.type-tag {
  background: var(--color-bg-primary);
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 0.75em !important;
  border: 1px solid var(--color-border-light);
}

.task-progress-box {
  margin-top: 15px;
  margin-bottom: 15px;
}

.progress-ctrl {
  margin: 10px 0;
  padding: 0 5px;
}

.progress-text {
  font-size: 0.8em;
  color: var(--color-text-muted);
  text-align: right;
  font-family: var(--font-family-mono);
}

/* 创建任务对话框增强 */
.mode-toggle {
  display: flex;
  justify-content: center;
  margin-bottom: 10px;
}

.ai-tip {
  margin-top: 15px;
  padding: 12px;
  background: rgba(0, 255, 204, 0.05);
  border-radius: 8px;
  border-left: 3px solid var(--color-primary);
  font-size: 0.85em;
  color: var(--color-primary-light);
}

/* AI 评估对话框 */
.eval-header {
  margin-bottom: 20px;
}

.eval-header h4 {
  margin: 0 0 10px 0;
  color: var(--color-primary-light);
}

.criteria-label {
  font-size: 0.85em;
  color: var(--color-text-muted);
  background: var(--color-bg-tertiary);
  padding: 8px;
  border-radius: 4px;
}

.prereqs-tag {
  background: rgba(230, 162, 60, 0.1);
  border: 1px solid rgba(230, 162, 60, 0.2);
  display: block;
  margin-top: 5px;
  width: 100%;
  padding: 2px 8px;
  border-radius: 4px;
}

.prereqs-tag .type-icon {
  color: var(--color-warning);
  font-size: 11px;
}

.task-chain-name {
  font-size: 0.7em;
  color: var(--color-primary-light);
  opacity: 0.7;
  font-weight: 400;
  margin-top: 2px;
}

/* AI 评定展示 */
.ai-suggestion-section {
  margin-top: 16px;
  padding: 16px;
  background: rgba(0, 255, 204, 0.05);
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 255, 204, 0.2);
}

.ai-suggestion-section h5 {
  font-size: 0.9em;
  color: var(--color-primary-light);
  margin: 0 0 12px 0;
}

.ai-eval-result {
  border-left: 3px solid var(--color-error);
  padding-left: 12px;
}

.ai-eval-result.passed {
  border-left-color: var(--color-success);
}

.ai-score {
  font-size: 0.85em;
  margin-bottom: 8px;
  font-weight: 600;
}

.ai-score span {
  font-family: var(--font-family-mono);
  font-size: 1.25em;
  color: var(--color-primary-light);
}

.ai-feedback {
  font-size: 0.9em;
  line-height: 1.6;
  color: var(--color-text-primary);
  margin-bottom: 12px;
}

.ai-suggestions-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ai-suggest-item {
  font-size: 0.8em;
  color: var(--color-text-secondary);
  background: rgba(255, 255, 255, 0.03);
  padding: 4px 8px;
  border-radius: 4px;
}

/* 详情页任务链步进器 */
.chain-stepper-container {
  margin-bottom: 24px;
  padding: 16px;
  background: rgba(0, 255, 204, 0.03);
  border-radius: var(--radius-md);
  border: 1px solid rgba(0, 255, 204, 0.1);
}

.section-title {
  font-size: 0.9em;
  font-weight: 700;
  color: var(--color-primary-light);
  margin-bottom: 16px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.chain-steps {
  display: flex;
  flex-direction: column;
  gap: 12px;
  position: relative;
  padding-left: 20px;
}

.chain-steps::before {
  content: '';
  position: absolute;
  left: 5px;
  top: 10px;
  bottom: 10px;
  width: 2px;
  background: rgba(0, 255, 204, 0.15);
}

.step-item {
  display: flex;
  align-items: center;
  gap: 15px;
  position: relative;
  opacity: 0.6;
  transition: all 0.3s ease;
}

.step-item.active {
  opacity: 1;
  transform: translateX(5px);
}

.step-item.completed {
  opacity: 0.9;
}

.step-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-border);
  border: 2px solid var(--color-bg-primary);
  z-index: 1;
  transition: all 0.3s ease;
}

.step-item.active .step-dot {
  background: var(--color-primary-light);
  box-shadow: 0 0 10px var(--color-primary);
  animation: pulse 2s infinite;
}

.step-item.completed .step-dot {
  background: var(--color-success);
}

.step-info {
  display: flex;
  justify-content: space-between;
  flex: 1;
}

.step-name {
  font-size: 0.95em;
  font-weight: 600;
}

.step-status {
  font-size: 0.8em;
  color: var(--color-text-muted);
}

.task-header-detail {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 1px solid var(--color-border);
}

.detail-title {
  font-size: 1.4em;
  margin: 0;
  color: var(--color-primary-light);
}

.detail-grid {
  margin-bottom: 12px;
}

.full-width {
  grid-column: span 2;
}

/* 任务组及拓扑树样式 */
.task-group-container {
  margin-bottom: 5px;
}
.task-group-bar {
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  padding: 18px 24px;
  cursor: pointer;
  transition: all var(--transition-normal);
  position: relative;
  overflow: hidden;
}
.task-group-bar::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--color-primary);
  z-index: 2;
}
.task-group-bar.is-completed::before {
  background: var(--color-success);
}
.task-group-bar:hover {
  background: var(--color-bg-secondary);
  box-shadow: 0 0 20px rgba(0, 255, 204, 0.1);
  transform: translateY(-2px);
  border-color: var(--color-primary-light);
}
.group-bg-progress {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: linear-gradient(90deg, rgba(99, 102, 241, 0.15) 0%, rgba(14, 165, 233, 0.05) 100%);
  z-index: 0;
  transition: width 0.5s ease-in-out;
}
.task-group-bar.is-completed .group-bg-progress {
  background: linear-gradient(90deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.05) 100%);
}
.group-title {
  color: var(--color-text-primary);
  text-shadow: 0 0 10px rgba(0,0,0,0.5);
}
.subtasks-container {
  padding-left: 20px;
  margin-top: 10px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.subtask-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(10, 13, 32, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-left: 3px solid rgba(255, 255, 255, 0.2);
  padding: 10px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.subtask-item:hover {
  background: rgba(0, 255, 204, 0.05);
  border-left-color: var(--color-primary-light);
}

.subtask-item.is-active {
  border-left: 3px solid var(--color-warning);
  background: rgba(245, 158, 11, 0.05);
}

.subtask-item.is-completed {
  border-left-color: var(--color-success);
  opacity: 0.7;
}

.subtask-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.subtask-diamond {
  width: 8px;
  height: 8px;
  background: var(--color-text-secondary);
  transform: rotate(45deg);
}

.is-active .subtask-diamond {
  background: var(--color-warning);
  box-shadow: 0 0 8px var(--color-warning);
}

.is-completed .subtask-diamond {
  background: var(--color-success);
}

.subtask-name {
  font-size: 0.95em;
  font-weight: 500;
  color: var(--color-text-primary);
}

.subtask-name.line-through {
  text-decoration: line-through;
  color: var(--color-text-muted);
}

.subtask-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pulse-tag {
  animation: pulse 2s infinite;
}

.tree-display {
  padding-left: 10px;
}

.tree-node-visual {
  display: flex;
  flex-direction: column;
  position: relative;
  margin-bottom: 16px;
}

.node-timeline-connector {
  position: absolute;
  left: 23px;
  top: 45px;
  bottom: -20px;
  width: 2px;
  background: var(--color-border);
  z-index: 0;
}

.node-visual-content {
  position: relative;
  z-index: 1;
  background: var(--color-bg-tertiary);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  padding: 16px;
  margin-left: 40px;
  transition: all 0.2s;
  cursor: pointer;
}

.node-visual-content:hover {
  border-color: var(--color-primary-light);
  transform: translateX(4px);
}

.status-completed .node-visual-content {
  border-left: 4px solid var(--color-success);
  opacity: 0.8;
}

.status-in_progress .node-visual-content {
  border-left: 4px solid var(--color-warning);
  background: rgba(245, 158, 11, 0.05);
  box-shadow: 0 0 15px rgba(245, 158, 11, 0.1);
}

.status-completed .node-name { color: var(--color-text-secondary); text-decoration: line-through; }
.status-in_progress .node-name { color: var(--color-warning); }
.status-pending .node-name { color: var(--color-text-primary); }

.tree-node-visual::before {
  content: '';
  position: absolute;
  left: 18px;
  top: 20px;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: var(--color-bg-secondary);
  border: 2px solid var(--color-border);
  z-index: 2;
  transition: all 0.3s;
}

.status-completed::before {
  background: var(--color-success);
  border-color: var(--color-success);
}

.status-in_progress::before {
  background: var(--color-warning);
  border-color: var(--color-warning);
  box-shadow: 0 0 10px var(--color-warning);
}

}
</style>