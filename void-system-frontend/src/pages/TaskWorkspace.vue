<template>
  <section class="action-workspace">
    <header class="page-heading">
      <div>
        <p class="page-kicker">行动工作台</p>
        <h1>把目标推进到下一步</h1>
        <p>集中查看正在推进的行动、下一步和需要你确认的事项。</p>
      </div>
      <div class="page-heading__actions">
        <el-button :icon="MagicStick" plain @click="selectView('plan')">规划目标</el-button>
        <el-button type="primary" :icon="Plus" @click="openGoalDialog()">新建目标</el-button>
      </div>
    </header>

    <section class="summary-strip" aria-label="行动概览">
      <div><span>进行中的目标</span><strong>{{ summary.activeGoals }}</strong></div>
      <div><span>正在推进</span><strong>{{ summary.activeRuns }}</strong></div>
      <div><span>等待确认</span><strong>{{ summary.waiting }}</strong></div>
      <div><span>本周完成</span><strong>{{ summary.completedThisWeek }}</strong></div>
    </section>

    <div class="view-switcher">
      <div class="view-switcher__tabs" role="tablist" aria-label="行动工作区视图">
        <button v-for="view in views" :key="view.value" type="button" role="tab" :aria-selected="activeView === view.value" :class="{ 'is-active': activeView === view.value }" @click="selectView(view.value)">
          <el-icon><component :is="view.icon" /></el-icon>
          <span>{{ view.label }}</span>
          <small v-if="view.count">{{ view.count }}</small>
        </button>
      </div>
      <el-button class="view-switcher__refresh" text :icon="Refresh" :loading="loading" aria-label="刷新工作区" @click="loadWorkspace" />
    </div>

    <Advisor v-if="activeView === 'plan'" embedded @published="handlePlanPublished" />

    <div v-else-if="loading && !goals.length && !runs.length" class="loading-state">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在整理你的行动...</span>
    </div>

    <template v-else-if="activeView === 'focus'">
      <div class="focus-layout">
        <main class="focus-main">
          <section class="section-block" aria-labelledby="active-runs-title">
            <div class="section-heading">
              <div><p class="section-kicker">现在</p><h2 id="active-runs-title">正在推进</h2></div>
              <span>{{ activeRuns.length }} 项</span>
            </div>

            <div v-if="activeRuns.length" class="run-list">
              <article v-for="run in activeRuns" :key="run.run_id" class="run-card" tabindex="0" @click="openRun(run)" @keydown.enter="openRun(run)">
                <div class="run-card__topline">
                  <span class="status-dot" :class="'status-dot--' + run.status" aria-hidden="true"></span>
                  <span class="run-card__goal">{{ run.goal_title || '未命名目标' }}</span>
                  <el-tag size="small" effect="plain" :type="runTagType(run.status)">{{ runStatusLabel(run.status) }}</el-tag>
                </div>
                <div class="run-card__body">
                  <div>
                    <h3>{{ run.title }}</h3>
                    <p>{{ run.objective || nextStepSummary(run) }}</p>
                  </div>
                  <strong class="run-card__percent">{{ runProgress(run) }}%</strong>
                </div>
                <el-progress :percentage="runProgress(run)" :show-text="false" :stroke-width="6" />
                <footer>
                  <span><el-icon><List /></el-icon>{{ Number(run.completed_steps || 0) }} / {{ Number(run.step_count || 0) }} 步</span>
                  <span>{{ modeLabel(run.mode) }}</span>
                  <el-icon><ArrowRight /></el-icon>
                </footer>
              </article>
            </div>

            <div v-else class="empty-state">
              <el-icon><CircleCheckFilled /></el-icon>
              <h3>当前没有进行中的行动</h3>
              <p>选择一个目标开始行动，或者让规划助手先帮你整理步骤。</p>
              <div><el-button type="primary" @click="openGoalDialog()">创建目标</el-button><el-button @click="selectView('plan')">规划目标</el-button></div>
            </div>
          </section>

          <section v-if="recentRuns.length" class="section-block section-block--recent" aria-labelledby="recent-runs-title">
            <div class="section-heading">
              <div><p class="section-kicker">最近</p><h2 id="recent-runs-title">执行记录</h2></div>
            </div>
            <div class="recent-list">
              <button v-for="run in recentRuns" :key="run.run_id" type="button" @click="openRun(run)">
                <el-icon :class="'recent-icon--' + run.status"><CircleCheckFilled v-if="run.status === 'completed'" /><Warning v-else /></el-icon>
                <span><strong>{{ run.title }}</strong><small>{{ run.goal_title }} · {{ formatRelativeTime(run.updated_at) }}</small></span>
                <el-tag size="small" effect="plain" :type="runTagType(run.status)">{{ runStatusLabel(run.status) }}</el-tag>
              </button>
            </div>
          </section>
        </main>

        <aside class="goal-rail" aria-labelledby="goals-rail-title">
          <div class="section-heading">
            <div><p class="section-kicker">方向</p><h2 id="goals-rail-title">进行中的目标</h2></div>
            <el-button text :icon="Plus" aria-label="新建目标" @click="openGoalDialog()" />
          </div>
          <div v-if="activeGoals.length" class="goal-rail__list">
            <article v-for="goal in activeGoals.slice(0, 6)" :key="goal.goal_id">
              <button type="button" @click="openGoal(goal)">
                <span class="priority-mark" :class="'priority-mark--' + goal.priority"></span>
                <span><strong>{{ goal.title }}</strong><small>{{ goal.desired_outcome || goal.description || '还没有写下预期结果' }}</small></span>
                <el-icon><ArrowRight /></el-icon>
              </button>
              <div><span>{{ goal.run_count || 0 }} 次行动</span><el-button text size="small" @click.stop="openRunDialog(goal)">开始</el-button></div>
            </article>
          </div>
          <div v-else class="rail-empty"><p>目标会让每一次行动都有明确方向。</p><el-button plain @click="openGoalDialog()">新建目标</el-button></div>
          <button class="rail-view-all" type="button" @click="selectView('goals')">查看全部目标<el-icon><ArrowRight /></el-icon></button>
        </aside>
      </div>
    </template>

    <section v-else-if="activeView === 'goals'" class="catalog-view" aria-labelledby="goal-catalog-title">
      <div class="catalog-toolbar">
        <div><p class="section-kicker">长期方向</p><h2 id="goal-catalog-title">目标</h2></div>
        <el-segmented v-model="goalFilter" :options="goalFilters" />
      </div>
      <div v-if="filteredGoals.length" class="goal-grid">
        <article v-for="goal in filteredGoals" :key="goal.goal_id" class="goal-card">
          <header>
            <div><span class="priority-label" :class="'priority-label--' + goal.priority">{{ priorityLabel(goal.priority) }}</span><el-tag v-if="goal.status !== 'active'" size="small" effect="plain" type="info">{{ goalStatusLabel(goal.status) }}</el-tag></div>
            <el-dropdown trigger="click" @command="(command) => handleGoalCommand(command, goal)">
              <el-button text circle :icon="MoreFilled" aria-label="目标操作" />
              <template #dropdown><el-dropdown-menu>
                <el-dropdown-item command="edit"><el-icon><Edit /></el-icon>编辑</el-dropdown-item>
                <el-dropdown-item v-if="goal.status === 'active'" command="complete"><el-icon><Check /></el-icon>标记达成</el-dropdown-item>
                <el-dropdown-item v-else command="reopen"><el-icon><RefreshRight /></el-icon>重新开启</el-dropdown-item>
                <el-dropdown-item v-if="goal.status !== 'archived'" divided command="archive"><el-icon><Delete /></el-icon>归档</el-dropdown-item>
              </el-dropdown-menu></template>
            </el-dropdown>
          </header>
          <button class="goal-card__content" type="button" @click="openGoal(goal)">
            <h3>{{ goal.title }}</h3>
            <p>{{ goal.desired_outcome || goal.description || '为这个目标补充一个清楚的预期结果。' }}</p>
          </button>
          <footer>
            <span>{{ goal.run_count || 0 }} 次行动 · {{ goal.completed_runs || 0 }} 次完成</span>
            <el-button v-if="goal.status === 'active'" type="primary" plain size="small" :icon="VideoPlay" @click="openRunDialog(goal)">开始行动</el-button>
          </footer>
        </article>
      </div>
      <div v-else class="empty-state"><el-icon><List /></el-icon><h3>这里还没有目标</h3><p>创建一个方向明确、结果可判断的目标。</p><el-button type="primary" @click="openGoalDialog()">新建目标</el-button></div>
    </section>

    <section v-else-if="activeView === 'automation'" class="catalog-view" aria-labelledby="automation-title">
      <div class="catalog-toolbar">
        <div><p class="section-kicker">何时启动</p><h2 id="automation-title">启动条件</h2><p>为已确认的计划设置开始时间，或在收到指定通知后启动。</p></div>
        <el-button type="primary" :icon="Plus" @click="openTriggerDialog()">添加安排</el-button>
      </div>
      <div v-if="triggers.length" class="automation-list">
        <article v-for="trigger in triggers" :key="trigger.trigger_id" class="automation-row">
          <div class="automation-icon"><el-icon><Calendar v-if="trigger.trigger_type === 'schedule'" /><Bell v-else /></el-icon></div>
          <div class="automation-copy"><div><strong>{{ trigger.name }}</strong><el-tag size="small" effect="plain" :type="trigger.status === 'active' ? 'success' : 'info'">{{ trigger.status === 'active' ? '已启用' : '已暂停' }}</el-tag></div><p>{{ triggerDescription(trigger) }}</p><small>{{ goalTitle(trigger.goal_id) }}</small></div>
          <div class="automation-actions">
            <el-switch :model-value="trigger.status === 'active'" aria-label="启用启动条件" @change="(enabled) => toggleTrigger(trigger, enabled)" />
            <el-button text :icon="Edit" aria-label="编辑启动条件" @click="openTriggerDialog(trigger)" />
            <el-button text :icon="Delete" aria-label="删除启动条件" @click="removeTrigger(trigger)" />
          </div>
        </article>
      </div>
      <div v-else class="empty-state"><el-icon><Calendar /></el-icon><h3>还没有启动条件</h3><p>适合每日复盘、每周计划，或在其他服务发来通知后开始行动。</p><el-button type="primary" @click="openTriggerDialog()">添加安排</el-button></div>
    </section>

    <el-dialog v-model="goalDialogOpen" :title="editingGoal ? '编辑目标' : '新建目标'" width="min(560px, calc(100vw - 28px))" :close-on-click-modal="false">
      <el-form label-position="top" @submit.prevent="saveGoal">
        <el-form-item label="目标名称" required><el-input v-model="goalDraft.title" maxlength="160" show-word-limit placeholder="例如：完成个人作品集并上线" /></el-form-item>
        <el-form-item label="预期结果"><el-input v-model="goalDraft.desired_outcome" type="textarea" :rows="3" maxlength="2000" placeholder="完成时，你希望看到什么具体结果？" /></el-form-item>
        <el-form-item label="补充说明"><el-input v-model="goalDraft.description" type="textarea" :rows="2" maxlength="2000" placeholder="背景、限制或你想坚持的方式" /></el-form-item>
        <el-form-item label="优先级"><el-segmented v-model="goalDraft.priority" :options="priorityOptions" /></el-form-item>
        <el-checkbox v-if="!editingGoal" v-model="goalDraft.startNow">创建后立即开始一次行动</el-checkbox>
      </el-form>
      <template #footer><el-button @click="goalDialogOpen = false">取消</el-button><el-button type="primary" :loading="submitting" :disabled="!goalDraft.title.trim()" @click="saveGoal">{{ editingGoal ? '保存' : '创建目标' }}</el-button></template>
    </el-dialog>

    <el-dialog v-model="runDialogOpen" title="开始一次行动" width="min(620px, calc(100vw - 28px))" :close-on-click-modal="false">
      <div v-if="runGoal" class="dialog-context"><span>目标</span><strong>{{ runGoal.title }}</strong></div>
      <el-form label-position="top" @submit.prevent="createRun">
        <el-form-item label="这次要推进什么"><el-input v-model="runDraft.objective" type="textarea" :rows="2" maxlength="2000" placeholder="写下这次行动希望完成的范围" /></el-form-item>
        <el-form-item label="推进方式"><el-segmented v-model="runDraft.mode" :options="runModeOptions" /></el-form-item>
        <el-form-item label="行动步骤"><el-input v-model="runDraft.stepsText" type="textarea" :rows="5" placeholder="每行一个步骤。留空时会创建一个与目标同名的步骤。" /></el-form-item>
        <el-checkbox v-model="runDraft.startNow">创建后立即开始</el-checkbox>
      </el-form>
      <template #footer><el-button @click="runDialogOpen = false">取消</el-button><el-button type="primary" :loading="submitting" @click="createRun">开始行动</el-button></template>
    </el-dialog>

    <el-dialog v-model="triggerDialogOpen" :title="editingTrigger ? '编辑启动条件' : '添加启动条件'" width="min(620px, calc(100vw - 28px))" :close-on-click-modal="false">
      <el-form label-position="top">
        <el-form-item label="名称" required><el-input v-model="triggerDraft.name" maxlength="160" placeholder="例如：每日学习复盘" /></el-form-item>
        <el-form-item label="关联目标" required><el-select v-model="triggerDraft.goalId" placeholder="选择一个进行中的目标" :disabled="Boolean(editingTrigger)"><el-option v-for="goal in activeGoals" :key="goal.goal_id" :label="goal.title" :value="goal.goal_id" /></el-select></el-form-item>
        <el-form-item label="启动方式"><el-segmented v-model="triggerDraft.type" :options="triggerTypeOptions" :disabled="Boolean(editingTrigger)" /></el-form-item>
        <template v-if="triggerDraft.type === 'schedule'">
          <el-form-item label="重复频率"><el-segmented v-model="triggerDraft.schedulePreset" :options="scheduleOptions" /></el-form-item>
          <div v-if="triggerDraft.schedulePreset === 'daily'" class="form-row"><el-form-item label="每天时间"><el-time-select v-model="triggerDraft.time" start="00:00" step="00:30" end="23:30" /></el-form-item></div>
          <div v-else-if="triggerDraft.schedulePreset === 'weekly'" class="form-row form-row--two"><el-form-item label="星期"><el-select v-model="triggerDraft.weekday"><el-option v-for="day in weekdays" :key="day.value" :label="day.label" :value="day.value" /></el-select></el-form-item><el-form-item label="时间"><el-time-select v-model="triggerDraft.time" start="00:00" step="00:30" end="23:30" /></el-form-item></div>
          <div v-else class="form-row"><el-form-item label="每隔多少小时"><el-input-number v-model="triggerDraft.intervalHours" :min="1" :max="720" /></el-form-item></div>
        </template>
        <el-form-item v-else label="收到哪类通知时"><el-input v-model="triggerDraft.eventType" maxlength="200" placeholder="例如：calendar.event.completed" /><div class="field-help">用于与日历、自动化工具或其他服务对接。</div></el-form-item>
        <el-form-item label="创建行动时的说明"><el-input v-model="triggerDraft.objective" type="textarea" :rows="2" maxlength="2000" placeholder="每次启动时要推进的内容" /></el-form-item>
      </el-form>
      <template #footer><el-button @click="triggerDialogOpen = false">取消</el-button><el-button type="primary" :loading="submitting" :disabled="!canSaveTrigger" @click="saveTrigger">保存安排</el-button></template>
    </el-dialog>

    <el-dialog v-model="stepCompletionDialogOpen" title="记录结果并完成" width="min(600px, calc(100vw - 28px))" :close-on-click-modal="false" @closed="resetStepCompletion">
      <div v-if="completingStep" class="completion-context">
        <span>当前步骤</span>
        <strong>{{ completingStep.title }}</strong>
      </div>
      <el-form label-position="top" @submit.prevent="submitStepCompletion">
        <el-form-item label="完成说明" required>
          <el-input v-model="stepCompletionDraft.note" type="textarea" :rows="4" maxlength="2000" show-word-limit placeholder="写下做了什么、结果如何，以及别人可以怎样核对。" />
          <div class="field-help">这段记录会保留在本次行动的步骤产出中。</div>
        </el-form-item>
        <div class="completion-result-toggle">
          <el-checkbox v-model="stepCompletionDraft.includeResult">同时记录一项可检查的成果</el-checkbox>
          <small>可以是文档、链接、文件、图片，或一项没有链接的文字成果。</small>
        </div>
        <div v-if="stepCompletionDraft.includeResult" class="completion-result-fields">
          <el-form-item label="成果名称">
            <el-input v-model="stepCompletionDraft.resultTitle" maxlength="200" placeholder="留空时会使用步骤名称" />
          </el-form-item>
          <div class="form-row form-row--two">
            <el-form-item label="成果类型"><el-select v-model="stepCompletionDraft.resultKind"><el-option v-for="item in STEP_RESULT_KIND_OPTIONS" :key="item.value" :label="item.label" :value="item.value" /></el-select></el-form-item>
            <el-form-item label="查看地址（可选）"><el-input v-model="stepCompletionDraft.resultUrl" maxlength="2000" placeholder="https://... 或可访问的文件地址" /></el-form-item>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="stepCompletionDialogOpen = false">取消</el-button><el-button type="primary" :loading="submitting" :disabled="!stepCompletionDraft.note.trim()" @click="submitStepCompletion">保存并完成</el-button></template>
    </el-dialog>

    <el-drawer v-model="runDrawerOpen" size="min(760px, 100vw)" :with-header="false" class="run-drawer" @closed="handleRunDrawerClosed">
      <div v-if="selectedRun" class="run-detail">
        <header class="run-detail__header">
          <button type="button" class="drawer-close" aria-label="关闭详情" @click="runDrawerOpen = false"><el-icon><Close /></el-icon></button>
          <div class="run-detail__identity"><span>{{ selectedRun.goal_title }}</span><h2>{{ selectedRun.title }}</h2><p>{{ selectedRun.objective || '按步骤推进这次行动。' }}</p></div>
          <el-tag effect="plain" :type="runTagType(selectedRun.status)">{{ runStatusLabel(selectedRun.status) }}</el-tag>
        </header>

        <section class="run-progress"><div><span>完成进度</span><strong>{{ runProgress(selectedRun) }}%</strong></div><el-progress :percentage="runProgress(selectedRun)" :show-text="false" :stroke-width="8" /></section>

        <section v-if="reviewCompletion" class="result-readiness" :class="{ 'result-readiness--ready': reviewCompletion.ready }" aria-labelledby="result-readiness-title">
          <div class="result-readiness__header"><div><p class="section-kicker">成果准备情况</p><h3 id="result-readiness-title">{{ reviewCompletion.ready ? '成果已经齐全' : '还有内容需要留意' }}</h3></div><span>{{ reviewCompletion.satisfied_steps }} / {{ reviewCompletion.step_count }} 步骤已完成</span></div>
          <p>{{ reviewReadinessDescription }}</p>
          <ul v-if="reviewIssues.length" class="review-issues"><li v-for="issue in reviewIssues" :key="issue.kind + issue.text">{{ issue.text }}</li></ul>
          <div v-if="reviewDeliverables.length" class="deliverable-status"><strong>约定的成果</strong><ul><li v-for="item in reviewDeliverables" :key="item.title"><span>{{ item.title }}</span><small :class="{ 'is-recorded': item.recorded }">{{ item.recorded ? '已记录' : '尚未记录' }}</small></li></ul></div>
          <small v-else>这次行动没有预先约定具体成果；已记录的交付物仍会保留在下方结果中。</small>
        </section>

        <section v-if="pendingApprovals.length" class="approval-panel">
          <div class="approval-panel__copy">
            <el-icon><Warning /></el-icon>
            <span><strong>需要你的确认</strong><small>{{ approvalSummary(pendingApprovals[0]) }}</small></span>
          </div>
          <p v-if="approvalImpact(pendingApprovals[0])" class="approval-panel__impact">影响：{{ approvalImpact(pendingApprovals[0]) }}</p>
          <div class="approval-panel__actions"><el-button :loading="submitting" @click="resolveApproval(pendingApprovals[0], 'rejected')">暂不继续</el-button><el-button type="primary" :loading="submitting" @click="resolveApproval(pendingApprovals[0], 'approved')">确认并继续</el-button></div>
        </section>

        <section v-else-if="resolvedApprovals.length" class="approval-history">
          <span><el-icon><CircleCheckFilled /></el-icon>确认已处理</span>
          <small>{{ resolvedApprovals[0].status === 'approved' ? '已确认继续' : '已选择暂不继续' }} · {{ approvalDecisionNote(resolvedApprovals[0]) }}</small>
        </section>

        <section class="next-action" :class="'next-action--' + selectedRun.status">
          <div><p class="section-kicker">下一步</p><strong>{{ nextActionTitle(selectedRun) }}</strong><small>{{ nextActionDescription(selectedRun) }}</small></div>
          <div class="next-action__controls">
            <el-button v-if="selectedRun.status === 'queued'" type="primary" :icon="VideoPlay" :loading="submitting" @click="transitionRun('start')">开始行动</el-button>
            <el-button v-if="selectedRun.status === 'paused'" type="primary" :icon="VideoPlay" :loading="submitting" @click="transitionRun('resume')">继续行动</el-button>
            <el-button v-if="selectedRun.status === 'failed' && canRetryRun" type="primary" :icon="RefreshRight" :loading="submitting" @click="retryRun">重新开始</el-button>
            <el-button v-if="selectedRun.status === 'running'" :icon="VideoPause" :loading="submitting" @click="transitionRun('pause')">暂停</el-button>
          </div>
        </section>

        <div v-if="selectedRun.status === 'failed'" class="run-problem">
          <span><el-icon><Warning /></el-icon>行动遇到问题</span>
          <p>{{ selectedRun.error_summary || failedStepSummary(selectedRun) || '这次行动尚未完成。' }}</p>
          <small v-if="canRetryRun">可以从失败的步骤继续；原有步骤、记录和交付物都会保留。</small>
          <small v-else>这一步的可用尝试次数已经用完，请结束本次行动后调整计划再创建新的行动。</small>
        </div>

        <div v-if="!terminalRun(selectedRun)" class="run-toolbar">
          <el-button v-if="selectedRun.status === 'running'" text @click="transitionRun('pause')">稍后继续</el-button>
          <el-button text type="danger" @click="cancelRun">结束本次行动</el-button>
        </div>

        <section v-if="terminalRun(selectedRun) && runReview" class="detail-section result-review" aria-labelledby="result-title">
          <div class="detail-section__heading"><div><p class="section-kicker">结果与复盘</p><h3 id="result-title">把这次行动留下来</h3></div><span>{{ runStatusLabel(selectedRun.status) }}</span></div>
          <p class="result-review__summary">{{ resultReviewSummary }}</p>
          <div class="result-evidence">
            <div class="evidence-block"><strong>已记录成果</strong><ul v-if="runReview.artifacts?.length" class="evidence-list"><li v-for="artifact in runReview.artifacts" :key="artifact.artifact_id || artifact.title"><a v-if="artifact.uri" :href="artifact.uri" target="_blank" rel="noreferrer">{{ artifact.title || '未命名成果' }}</a><span v-else>{{ artifact.title || '未命名成果' }}</span><small>{{ artifactKindLabel(artifact.kind) }}</small></li></ul><p v-else>尚未记录可交付的成果。</p></div>
            <div class="evidence-block"><strong>步骤产出</strong><ul v-if="runReview.outputs?.length" class="evidence-list"><li v-for="output in runReview.outputs" :key="output.step_id"><span>{{ output.step_title || '行动步骤' }}</span><small>{{ outputSummary(output.data) }}</small></li></ul><p v-else>没有额外的步骤产出记录。</p></div>
            <div class="evidence-block"><strong>确认记录</strong><ul v-if="runReview.approvals?.length" class="evidence-list"><li v-for="approval in runReview.approvals" :key="approval.approval_id"><span>{{ approval.summary }}</span><small>{{ approvalStatusLabel(approval.status) }}</small></li></ul><p v-else>这次行动不需要额外确认。</p></div>
            <div class="evidence-block"><strong>已结算奖励</strong><p>{{ rewardSummary }}</p></div>
          </div>
          <div class="reflection-form">
            <div><strong>留下复盘</strong><p>这不会改动已完成的步骤、成果或执行记录。</p></div>
            <el-form label-position="top">
              <el-form-item label="这次结果如何"><el-segmented v-model="reviewDraft.outcome" :options="reviewOutcomeOptions" /></el-form-item>
              <el-form-item label="满意程度"><el-rate v-model="reviewDraft.rating" :max="5" show-score /></el-form-item>
              <el-form-item label="复盘笔记"><el-input v-model="reviewDraft.notes" type="textarea" :rows="3" maxlength="4000" show-word-limit placeholder="哪些地方值得保留，哪些地方下次要改？" /></el-form-item>
              <el-form-item label="下一步意图"><el-input v-model="reviewDraft.nextAction" maxlength="1000" placeholder="例如：把这次做法整理成下次可复用的模板" /></el-form-item>
            </el-form>
            <div class="reflection-form__actions"><small v-if="runReview.next_action?.text">建议：{{ runReview.next_action.text }}</small><div><el-button :icon="Plus" @click="openFollowUpDraft">创建下一项行动</el-button><el-button type="primary" :loading="submitting" @click="saveReview">保存复盘</el-button></div></div>
          </div>
        </section>

        <section class="detail-section" aria-labelledby="steps-title">
          <div class="detail-section__heading"><div><p class="section-kicker">行动路径</p><h3 id="steps-title">步骤</h3></div><span>{{ completedStepCount }} / {{ selectedRun.steps?.length || 0 }}</span></div>
          <ol class="step-list">
            <li v-for="(step, index) in selectedRun.steps || []" :key="step.step_id" :class="'step-item step-item--' + step.status">
              <div class="step-index"><el-icon v-if="['completed', 'skipped'].includes(step.status)"><Check /></el-icon><span v-else>{{ index + 1 }}</span></div>
              <div class="step-copy"><div><h4>{{ step.title }}</h4><el-tag size="small" effect="plain" :type="stepTagType(step.status)">{{ stepStatusLabel(step.status) }}</el-tag></div><p v-if="step.description">{{ step.description }}</p><small v-if="step.depends_on?.length">完成“{{ step.depends_on.map((item) => item.client_key).join('、') }}”后开始</small><small v-if="step.status === 'failed' && step.error_summary" class="step-copy__problem">原因：{{ step.error_summary }}</small></div>
              <div class="step-actions">
                <el-button v-if="step.status === 'ready' && selectedRun.status === 'running'" type="primary" plain size="small" :loading="submitting" @click="startStep(step)">开始</el-button>
                <el-button v-if="step.status === 'running'" type="primary" size="small" :loading="submitting" @click="openStepCompletion(step)">记录结果并完成</el-button>
                <el-button v-if="step.status === 'failed' && selectedRun.status === 'failed' && stepCanRetry(step)" type="primary" plain size="small" :icon="RefreshRight" :loading="submitting" @click="retryRun">从这里继续</el-button>
                <el-dropdown v-if="canSkipStep(step)" trigger="click" @command="() => skipStep(step)"><el-button text circle :icon="MoreFilled" aria-label="更多步骤操作" /><template #dropdown><el-dropdown-menu><el-dropdown-item command="skip">跳过这个步骤</el-dropdown-item></el-dropdown-menu></template></el-dropdown>
              </div>
            </li>
          </ol>
        </section>

        <section v-if="canSteerRun || runCommands.length" class="detail-section command-section">
          <div class="detail-section__heading"><div><p class="section-kicker">调整要求</p><h3>告诉系统接下来怎么调整</h3></div><span v-if="pendingCommands.length">{{ pendingCommands.length }} 条待处理</span></div>
          <div v-if="canSteerRun" class="command-composer"><el-input v-model="commandText" type="textarea" :rows="2" maxlength="4000" placeholder="补充限制、纠正方向，或说明新的要求" /><el-button type="primary" :icon="Promotion" :loading="submitting" :disabled="!commandText.trim()" @click="submitCommand">发送</el-button></div>
          <div v-if="pendingCommands.length" class="command-group"><strong>等待处理</strong><div class="command-list"><div v-for="command in pendingCommands" :key="command.command_id"><span>{{ command.instruction }}</span><small>已提交，等待系统采纳</small></div></div></div>
          <div v-if="acknowledgedCommands.length" class="command-group"><strong>已采纳</strong><div class="command-list"><div v-for="command in acknowledgedCommands" :key="command.command_id"><span>{{ command.instruction }}</span><small>已纳入后续行动</small></div></div></div>
        </section>

        <el-collapse class="history-collapse"><el-collapse-item name="history"><template #title><span class="history-title"><el-icon><Clock /></el-icon>查看执行记录</span></template><div v-if="runEvents.length" class="event-list"><div v-for="event in runEvents" :key="event.event_id"><span></span><p><strong>{{ eventLabel(event.event_type) }}</strong><small>{{ formatDateTime(event.created_at) }}</small></p></div></div><p v-else class="history-empty">还没有执行记录。</p></el-collapse-item></el-collapse>
      </div>
    </el-drawer>
  </section>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, Bell, Calendar, Check, CircleCheckFilled, Clock, Close, Delete, Edit, List, Loading, MagicStick, MoreFilled, Plus, Promotion, Refresh, RefreshRight, VideoPause, VideoPlay, Warning } from '@element-plus/icons-vue'
import { goalsApi } from '@/api/goals'
import { runsApi } from '@/api/runs'
import { triggersApi } from '@/api/triggers'
import { formatAxiosErrorMessage } from '@/utils/apiPayload'
import { buildStepCompletionInput, createStepCompletionDraft, STEP_RESULT_KIND_OPTIONS } from '@/domain/stepCompletion'
import { artifactKindLabel, mergeDeclaredDeliverables } from '@/domain/runReviewPresentation'
import Advisor from '@/pages/Advisor.vue'

const route = useRoute()
const router = useRouter()
const goals = ref([])
const runs = ref([])
const triggers = ref([])
const loading = ref(false)
const submitting = ref(false)
const activeView = ref('focus')
const goalFilter = ref('active')
const selectedRun = ref(null)
const runEvents = ref([])
const runCommands = ref([])
const runReview = ref(null)
const commandText = ref('')
const runDrawerOpen = ref(false)
const goalDialogOpen = ref(false)
const runDialogOpen = ref(false)
const triggerDialogOpen = ref(false)
const stepCompletionDialogOpen = ref(false)
const editingGoal = ref(null)
const editingTrigger = ref(null)
const completingStep = ref(null)
const runGoal = ref(null)

const goalDraft = reactive(defaultGoalDraft())
const runDraft = reactive(defaultRunDraft())
const triggerDraft = reactive(defaultTriggerDraft())
const reviewDraft = reactive(defaultReviewDraft())
const stepCompletionDraft = reactive(createStepCompletionDraft())

const priorityOptions = [{ label: '稍后', value: 'low' }, { label: '正常', value: 'medium' }, { label: '优先', value: 'high' }]
const runModeOptions = [{ label: '自己完成', value: 'manual' }, { label: '和系统一起', value: 'assisted' }, { label: '交给系统', value: 'agent' }]
const triggerTypeOptions = [{ label: '按时间', value: 'schedule' }, { label: '收到通知', value: 'event' }]
const scheduleOptions = [{ label: '每天', value: 'daily' }, { label: '每周', value: 'weekly' }, { label: '按间隔', value: 'interval' }]
const weekdays = [{ label: '周一', value: 1 }, { label: '周二', value: 2 }, { label: '周三', value: 3 }, { label: '周四', value: 4 }, { label: '周五', value: 5 }, { label: '周六', value: 6 }, { label: '周日', value: 0 }]
const goalFilters = [{ label: '进行中', value: 'active' }, { label: '已达成', value: 'completed' }, { label: '已归档', value: 'archived' }]
const reviewOutcomeOptions = [{ label: '达成', value: 'met' }, { label: '部分达成', value: 'partially_met' }, { label: '未达成', value: 'not_met' }]

const activeGoals = computed(() => goals.value.filter((goal) => goal.status === 'active'))
const activeRuns = computed(() => runs.value.filter((run) => !terminalRun(run)))
const recentRuns = computed(() => runs.value.filter(terminalRun).slice(0, 6))
const filteredGoals = computed(() => goals.value.filter((goal) => goal.status === goalFilter.value))
const pendingApprovals = computed(() => (selectedRun.value?.approvals || []).filter((approval) => approval.status === 'pending'))
const resolvedApprovals = computed(() => (selectedRun.value?.approvals || []).filter((approval) => approval.status !== 'pending').slice().reverse())
const pendingCommands = computed(() => runCommands.value.filter((command) => command.status !== 'acknowledged').slice().reverse())
const acknowledgedCommands = computed(() => runCommands.value.filter((command) => command.status === 'acknowledged').slice().reverse())
const completedStepCount = computed(() => (selectedRun.value?.steps || []).filter((step) => ['completed', 'skipped'].includes(step.status)).length)
const canSteerRun = computed(() => selectedRun.value && !terminalRun(selectedRun.value) && ['assisted', 'agent'].includes(selectedRun.value.mode))
const canRetryRun = computed(() => selectedRun.value?.status === 'failed' && (selectedRun.value.steps || []).some(stepCanRetry))
const reviewCompletion = computed(() => runReview.value?.completion || null)
const reviewDeliverables = computed(() => mergeDeclaredDeliverables(reviewCompletion.value?.deliverables?.declared))
const reviewIssues = computed(() => {
  const completion = reviewCompletion.value
  if (!completion) return []
  return [
    ...(completion.incomplete_steps || []).map((item) => ({ kind: 'step', text: '未结束步骤：' + (item.title || '未命名步骤') })),
    ...(completion.pending_approvals || []).map((item) => ({ kind: 'approval', text: '待确认：' + (item.summary || '需要确认的事项') })),
    ...reviewDeliverables.value
      .filter((item) => !item.recorded)
      .map((item) => ({ kind: 'deliverable', text: '尚未记录成果：' + item.title }))
  ]
})
const reviewReadinessDescription = computed(() => {
  const completion = reviewCompletion.value
  if (!completion) return ''
  if (completion.ready) return '步骤、确认和约定成果都已经有记录。'
  return reviewIssues.value.length ? '结束前仍有 ' + reviewIssues.value.length + ' 项需要留意。' : '正在根据当前记录整理成果。'
})
const resultReviewSummary = computed(() => {
  if (!runReview.value) return ''
  const count = Number(runReview.value.summary?.artifact_count || 0)
  const outputCount = Number(runReview.value.outputs?.length || 0)
  return '本次行动留下 ' + count + ' 项成果和 ' + outputCount + ' 条步骤产出。执行证据保持不变，你可以补充自己的评价和下一步意图。'
})
const rewardSummary = computed(() => {
  const totals = runReview.value?.rewards?.totals
  if (!totals?.settlements) return '暂无已结算奖励。'
  return '已结算 ' + totals.settlements + ' 次：' + totals.coins + ' 金币，' + totals.experience + ' 经验。'
})
const summary = computed(() => ({
  activeGoals: activeGoals.value.length,
  activeRuns: activeRuns.value.length,
  waiting: runs.value.filter((run) => run.status === 'waiting_approval').length,
  completedThisWeek: runs.value.filter((run) => run.status === 'completed' && isThisWeek(run.completed_at || run.updated_at)).length
}))
const views = computed(() => [
  { label: '正在推进', value: 'focus', icon: VideoPlay, count: activeRuns.value.length },
  { label: '规划', value: 'plan', icon: MagicStick, count: 0 },
  { label: '目标', value: 'goals', icon: List, count: activeGoals.value.length },
  { label: '启动条件', value: 'automation', icon: Calendar, count: triggers.value.filter((trigger) => trigger.status === 'active').length }
])
const canSaveTrigger = computed(() => triggerDraft.name.trim() && triggerDraft.goalId && (triggerDraft.type === 'schedule' || triggerDraft.eventType.trim()))

function defaultGoalDraft() { return { title: '', desired_outcome: '', description: '', priority: 'medium', startNow: true } }
function defaultRunDraft() { return { objective: '', mode: 'manual', stepsText: '', startNow: true } }
function defaultTriggerDraft() { return { name: '', goalId: '', type: 'schedule', schedulePreset: 'daily', time: '09:00', weekday: 1, intervalHours: 24, eventType: '', objective: '' } }
function defaultReviewDraft() { return { outcome: '', rating: 0, notes: '', nextAction: '' } }
function syncReviewDraft(review = null) {
  const reflection = review?.reflection || {}
  Object.assign(reviewDraft, defaultReviewDraft(), {
    outcome: reflection.outcome || '',
    rating: Number(reflection.rating || 0),
    notes: reflection.notes || '',
    nextAction: reflection.next_action || ''
  })
}
function terminalRun(run) { return ['completed', 'failed', 'cancelled'].includes(run?.status) }
function stepCanRetry(step) { return step.status === 'failed' && Number(step.attempt_count || 0) < Number(step.max_attempts || 1) }
function failedStepSummary(run) { return (run?.steps || []).find((step) => step.status === 'failed')?.error_summary || '' }
function approvalSummary(approval) { return approval?.summary || approval?.request_data?.summary || '请确认是否继续这次行动。' }
function approvalImpact(approval) {
  const details = approval?.request_data?.details || approval?.request_data?.impact || approval?.request_data?.reason || ''
  if (typeof details === 'string') return details
  return details?.impact || details?.description || details?.reason || ''
}
function approvalDecisionNote(approval) { return approval?.decision_data?.note || '结果已记录' }
function nextActionTitle(run) {
  const readyStep = (run?.steps || []).find((step) => step.status === 'ready')
  const runningStep = (run?.steps || []).find((step) => step.status === 'running')
  if (run?.status === 'queued') return '准备开始这次行动'
  if (run?.status === 'running') return runningStep ? '正在处理：' + runningStep.title : readyStep ? '下一步：' + readyStep.title : '等待这次行动继续推进'
  if (run?.status === 'paused') return '行动已暂停，可以继续'
  if (run?.status === 'waiting_approval') return '先处理一项确认'
  if (run?.status === 'failed') return stepCanRetry((run?.steps || []).find((step) => step.status === 'failed') || {}) ? '从失败步骤继续行动' : '这次行动无法继续重试'
  if (run?.status === 'completed') return '这次行动已完成'
  if (run?.status === 'cancelled') return '本次行动已结束'
  return '查看行动状态'
}
function nextActionDescription(run) {
  const readyStep = (run?.steps || []).find((step) => step.status === 'ready')
  const failedStep = (run?.steps || []).find((step) => step.status === 'failed')
  if (run?.status === 'queued') return '确认后按既定步骤开始推进。'
  if (run?.status === 'running') return readyStep ? '可以开始下一步，也可以先补充新的要求。' : '当前步骤完成后，系统会继续检查后续路径。'
  if (run?.status === 'paused') return '继续后会保留当前进度和已完成记录。'
  if (run?.status === 'waiting_approval') return '确认影响后，行动才能继续。'
  if (run?.status === 'failed') return stepCanRetry(failedStep || {}) ? '会保留已有步骤、执行记录和交付物。' : '请调整计划后创建新的行动。'
  if (run?.status === 'completed') return '可在执行记录中回看过程和结果。'
  if (run?.status === 'cancelled') return '记录会保留，不能再继续推进。'
  return ''
}
function runProgress(run) { const total = Number(run?.step_count ?? run?.steps?.length ?? 0); const done = Number(run?.completed_steps ?? (run?.steps || []).filter((step) => ['completed', 'skipped'].includes(step.status)).length); return total ? Math.round(done / total * 100) : 0 }
function runStatusLabel(status) { return ({ queued: '准备开始', running: '进行中', paused: '已暂停', waiting_approval: '等待确认', completed: '已完成', failed: '未完成', cancelled: '已结束' })[status] || '未知状态' }
function runTagType(status) { return ({ running: 'primary', waiting_approval: 'warning', completed: 'success', failed: 'danger', cancelled: 'info', paused: 'info', queued: '' })[status] || 'info' }
function stepStatusLabel(status) { return ({ pending: '等待前序', ready: '可以开始', running: '进行中', waiting_approval: '等待确认', completed: '已完成', failed: '需要处理', skipped: '已跳过', cancelled: '已结束' })[status] || '未知状态' }
function stepTagType(status) { return ({ ready: 'primary', running: 'primary', waiting_approval: 'warning', completed: 'success', failed: 'danger', skipped: 'info', cancelled: 'info', pending: 'info' })[status] || 'info' }
function goalStatusLabel(status) { return ({ active: '进行中', completed: '已达成', archived: '已归档' })[status] || status }
function priorityLabel(priority) { return ({ low: '稍后', medium: '正常', high: '优先' })[priority] || '正常' }
function modeLabel(mode) { return ({ manual: '自己完成', assisted: '和系统一起', agent: '交给系统' })[mode] || '自己完成' }
function nextStepSummary(run) { return run.status === 'waiting_approval' ? '有一步需要你确认后才能继续。' : '打开查看下一步行动。' }
function goalTitle(goalId) { return goals.value.find((goal) => goal.goal_id === goalId)?.title || '关联目标' }
function isThisWeek(value) { if (!value) return false; const date = new Date(value); const now = new Date(); const start = new Date(now); const day = (now.getDay() + 6) % 7; start.setDate(now.getDate() - day); start.setHours(0, 0, 0, 0); return date >= start }
function formatRelativeTime(value) { if (!value) return ''; const delta = Date.now() - new Date(value).getTime(); const minutes = Math.max(1, Math.floor(delta / 60000)); if (minutes < 60) return minutes + ' 分钟前'; const hours = Math.floor(minutes / 60); if (hours < 24) return hours + ' 小时前'; return Math.floor(hours / 24) + ' 天前' }
function formatDateTime(value) { return value ? new Intl.DateTimeFormat('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }).format(new Date(value)) : '' }
function eventLabel(type) { return ({ 'run.created': '行动已创建', 'run.started': '开始行动', 'run.paused': '暂停行动', 'run.resumed': '继续行动', 'run.completed': '行动已完成', 'run.cancelled': '行动已结束', 'step.started': '步骤已开始', 'step.completed': '步骤已完成', 'step.skipped': '步骤已跳过', 'step.failed': '步骤遇到问题', 'approval.requested': '请求确认', 'approval.resolved': '确认已处理', 'run.command_added': '补充了新要求', 'run.command_acknowledged': '新要求已采纳' })[type] || '执行状态已更新' }
function approvalStatusLabel(status) { return ({ approved: '已确认继续', rejected: '已选择暂不继续', pending: '仍在等待确认' })[status] || '已处理' }
function outputSummary(data) {
  if (!data || typeof data !== 'object') return '已记录产出'
  const preferred = data.summary || data.result || data.message || data.description
  if (typeof preferred === 'string' && preferred.trim()) return preferred.trim()
  const keys = Object.keys(data)
  return keys.length ? '已记录：' + keys.slice(0, 3).join('、') : '已记录产出'
}

async function loadWorkspace() {
  loading.value = true
  try {
    const [goalList, runList, triggerList] = await Promise.all([goalsApi.list(), runsApi.list(), triggersApi.list()])
    goals.value = goalList
    runs.value = runList
    triggers.value = triggerList
  } catch (error) {
    ElMessage.error(formatAxiosErrorMessage(error, '行动工作台暂时不可用。'))
  } finally { loading.value = false }
}

function selectView(view) {
  activeView.value = view
  const query = { ...route.query, view }
  if (view !== 'focus') delete query.run
  return router.replace({ query })
}

async function handlePlanPublished({ run }) {
  await loadWorkspace()
  await selectView('focus')
  await openRun(run)
}

function openGoalDialog(goal = null) {
  editingGoal.value = goal
  Object.assign(goalDraft, defaultGoalDraft(), goal ? { title: goal.title, desired_outcome: goal.desired_outcome || '', description: goal.description || '', priority: goal.priority || 'medium', startNow: false } : {})
  goalDialogOpen.value = true
}

async function saveGoal() {
  if (!goalDraft.title.trim()) return
  submitting.value = true
  try {
    const payload = { title: goalDraft.title.trim(), desired_outcome: goalDraft.desired_outcome.trim(), description: goalDraft.description.trim(), priority: goalDraft.priority }
    if (editingGoal.value) {
      await goalsApi.update(editingGoal.value.goal_id, payload)
      ElMessage.success('目标已保存')
    } else {
      const goal = await goalsApi.create(payload)
      if (goalDraft.startNow) {
        const run = await runsApi.create(goal.goal_id, { title: goal.title, objective: goal.desired_outcome || goal.description, mode: 'manual' })
        await runsApi.start(run.run_id)
      }
      ElMessage.success(goalDraft.startNow ? '目标已创建并开始行动' : '目标已创建')
    }
    goalDialogOpen.value = false
    await loadWorkspace()
  } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '保存目标失败。')) } finally { submitting.value = false }
}

function openGoal(goal) { activeView.value = 'goals'; goalFilter.value = goal.status }
function openRunDialog(goal) { runGoal.value = goal; Object.assign(runDraft, defaultRunDraft(), { objective: goal.desired_outcome || goal.description || goal.title }); runDialogOpen.value = true }
async function createRun() {
  if (!runGoal.value) return
  submitting.value = true
  try {
    const lines = runDraft.stepsText.split(/\r?\n/).map((line) => line.trim()).filter(Boolean)
    const steps = lines.length ? lines.map((title, index) => ({ client_key: 'step-' + (index + 1), title, kind: runDraft.mode === 'agent' ? 'agent' : 'manual', depends_on: index ? ['step-' + index] : [], max_attempts: runDraft.mode === 'agent' ? 3 : 1 })) : undefined
    let run = await runsApi.create(runGoal.value.goal_id, { title: runGoal.value.title, objective: runDraft.objective.trim(), mode: runDraft.mode, steps })
    if (runDraft.startNow) run = await runsApi.start(run.run_id)
    runDialogOpen.value = false
    ElMessage.success(runDraft.startNow ? '行动已开始' : '行动已创建')
    await loadWorkspace()
    await openRun(run)
  } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '创建行动失败。')) } finally { submitting.value = false }
}

async function openRun(run) {
  runDrawerOpen.value = true
  try {
    const detail = await runsApi.get(run.run_id)
    const [events, commands, review] = await Promise.all([
      runsApi.events(detail.run_id),
      terminalRun(detail) ? Promise.resolve([]) : runsApi.listCommands(detail.run_id),
      runsApi.review(detail.run_id)
    ])
    selectedRun.value = detail
    runEvents.value = events
    runCommands.value = commands
    runReview.value = review
    syncReviewDraft(review)
    if (route.query.run !== detail.run_id || route.query.view !== 'focus') {
      await router.replace({ query: { ...route.query, view: 'focus', run: detail.run_id } })
    }
  } catch (error) { runDrawerOpen.value = false; ElMessage.error(formatAxiosErrorMessage(error, '无法打开行动详情。')) }
}
function handleRunDrawerClosed() {
  selectedRun.value = null
  runEvents.value = []
  runCommands.value = []
  runReview.value = null
  syncReviewDraft()
  if (route.query.run) {
    const query = { ...route.query }
    delete query.run
    router.replace({ query })
  }
}
async function refreshSelectedRun(run = null) {
  if (!selectedRun.value && !run) return
  const runId = run?.run_id || selectedRun.value.run_id
  selectedRun.value = run || await runsApi.get(runId)
  const [events, review] = await Promise.all([runsApi.events(runId), runsApi.review(runId)])
  runEvents.value = events
  runReview.value = review
  syncReviewDraft(review)
  runCommands.value = terminalRun(selectedRun.value) ? [] : await runsApi.listCommands(runId)
  await loadWorkspace()
}
async function transitionRun(action) { if (!selectedRun.value) return; submitting.value = true; try { const run = await runsApi[action](selectedRun.value.run_id); await refreshSelectedRun(run); ElMessage.success(action === 'start' ? '行动已开始' : action === 'pause' ? '行动已暂停' : '继续行动') } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '更新行动状态失败。')) } finally { submitting.value = false } }
async function cancelRun() { if (!selectedRun.value) return; try { await ElMessageBox.confirm('结束后仍可查看记录，但不能继续推进。', '结束本次行动', { confirmButtonText: '结束行动', cancelButtonText: '取消', type: 'warning' }); const run = await runsApi.cancel(selectedRun.value.run_id, '用户主动结束'); await refreshSelectedRun(run); ElMessage.success('本次行动已结束') } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(formatAxiosErrorMessage(error, '结束行动失败。')) } }
async function startStep(step) { submitting.value = true; try { const run = await runsApi.startStep(selectedRun.value.run_id, step.step_id); await refreshSelectedRun(run) } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '无法开始这个步骤。')) } finally { submitting.value = false } }
function openStepCompletion(step) {
  completingStep.value = step
  Object.assign(stepCompletionDraft, createStepCompletionDraft(step))
  stepCompletionDialogOpen.value = true
}
function resetStepCompletion() {
  completingStep.value = null
  Object.assign(stepCompletionDraft, createStepCompletionDraft())
}
async function submitStepCompletion() {
  if (!selectedRun.value || !completingStep.value) return
  let input
  try {
    input = buildStepCompletionInput(stepCompletionDraft, completingStep.value)
  } catch (error) {
    ElMessage.warning(error.message || '请补充完成说明。')
    return
  }
  submitting.value = true
  try {
    const run = await runsApi.completeStep(selectedRun.value.run_id, completingStep.value.step_id, input)
    stepCompletionDialogOpen.value = false
    await refreshSelectedRun(run)
    ElMessage.success('结果已记录，步骤已完成')
  } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '无法保存这个步骤的结果。')) } finally { submitting.value = false }
}
function canSkipStep(step) { return selectedRun.value?.status === 'running' && ['pending', 'ready', 'failed'].includes(step.status) }
async function skipStep(step) { try { await ElMessageBox.confirm('跳过后，依赖它的后续步骤可以继续。', '跳过步骤', { confirmButtonText: '跳过', cancelButtonText: '取消', type: 'warning' }); const run = await runsApi.skipStep(selectedRun.value.run_id, step.step_id); await refreshSelectedRun(run); ElMessage.success('步骤已跳过') } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(formatAxiosErrorMessage(error, '无法跳过这个步骤。')) } }
async function retryRun() { if (!selectedRun.value) return; submitting.value = true; try { const run = await runsApi.retry(selectedRun.value.run_id); await refreshSelectedRun(run); ElMessage.success('已从失败步骤继续行动') } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '暂时无法重新开始这次行动。')) } finally { submitting.value = false } }
async function resolveApproval(approval, decision) { try { const run = await runsApi.resolveApproval(approval.approval_id, decision); await refreshSelectedRun(run); ElMessage.success(decision === 'approved' ? '已同意继续' : '已拒绝') } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '处理确认失败。')) } }
async function submitCommand() { if (!commandText.value.trim() || !selectedRun.value) return; submitting.value = true; try { await runsApi.submitCommand(selectedRun.value.run_id, { command_type: 'instruction', instruction: commandText.value.trim(), idempotency_key: 'web-' + Date.now() }); commandText.value = ''; runCommands.value = await runsApi.listCommands(selectedRun.value.run_id); runEvents.value = await runsApi.events(selectedRun.value.run_id); ElMessage.success('补充要求已发送') } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '发送补充要求失败。')) } finally { submitting.value = false } }
async function saveReview() {
  if (!selectedRun.value || !terminalRun(selectedRun.value)) return
  const values = {
    outcome: reviewDraft.outcome || null,
    rating: reviewDraft.rating || null,
    notes: reviewDraft.notes.trim(),
    next_action: reviewDraft.nextAction.trim()
  }
  if (!values.outcome && !values.rating && !values.notes && !values.next_action) {
    ElMessage.warning('请至少写下一项复盘内容。')
    return
  }
  submitting.value = true
  try {
    const review = await runsApi.saveReview(selectedRun.value.run_id, values)
    runReview.value = review
    syncReviewDraft(review)
    runEvents.value = await runsApi.events(selectedRun.value.run_id)
    ElMessage.success('复盘已保存')
  } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '保存复盘失败。')) } finally { submitting.value = false }
}
function openFollowUpDraft() {
  if (!selectedRun.value) return
  const goal = goals.value.find((item) => item.goal_id === selectedRun.value.goal_id)
  if (!goal) { ElMessage.warning('找不到关联目标，无法预填新的行动。'); return }
  runDrawerOpen.value = false
  runGoal.value = goal
  Object.assign(runDraft, defaultRunDraft(), {
    objective: runReview.value?.next_action?.text || reviewDraft.nextAction || selectedRun.value.objective || goal.desired_outcome || goal.title,
    mode: selectedRun.value.mode || 'manual',
    startNow: false
  })
  runDialogOpen.value = true
}

async function handleGoalCommand(command, goal) {
  if (command === 'edit') return openGoalDialog(goal)
  const status = command === 'complete' ? 'completed' : command === 'archive' ? 'archived' : 'active'
  try { await goalsApi.update(goal.goal_id, { status }); ElMessage.success(status === 'completed' ? '目标已标记为达成' : status === 'archived' ? '目标已归档' : '目标已重新开启'); await loadWorkspace() } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '更新目标失败。')) }
}

function openTriggerDialog(trigger = null) {
  editingTrigger.value = trigger
  const goal = trigger ? goals.value.find((item) => item.goal_id === trigger.goal_id) : activeGoals.value[0]
  Object.assign(triggerDraft, defaultTriggerDraft(), { goalId: goal?.goal_id || '', objective: goal?.desired_outcome || goal?.description || goal?.title || '' })
  if (trigger) {
    const config = trigger.configuration || {}
    const cron = String(config.cron || '')
    let preset = config.interval_seconds ? 'interval' : 'daily'
    let time = '09:00'
    let weekday = 1
    if (cron) { const parts = cron.split(/\s+/); time = String(parts[1] || '9').padStart(2, '0') + ':' + String(parts[0] || '0').padStart(2, '0'); if (parts[4] && parts[4] !== '*') { preset = 'weekly'; weekday = Number(parts[4]) } }
    Object.assign(triggerDraft, { name: trigger.name, goalId: trigger.goal_id, type: trigger.trigger_type, schedulePreset: preset, time, weekday, intervalHours: Math.max(1, Math.round(Number(config.interval_seconds || 86400) / 3600)), eventType: config.event_type || '', objective: trigger.run_template?.objective || '' })
  }
  triggerDialogOpen.value = true
}
function triggerConfiguration() { if (triggerDraft.type === 'event') return { event_type: triggerDraft.eventType.trim() }; if (triggerDraft.schedulePreset === 'interval') return { interval_seconds: triggerDraft.intervalHours * 3600 }; const [hour, minute] = triggerDraft.time.split(':').map(Number); return { cron: triggerDraft.schedulePreset === 'weekly' ? `${minute} ${hour} * * ${triggerDraft.weekday}` : `${minute} ${hour} * * *` } }
async function saveTrigger() {
  if (!canSaveTrigger.value) return
  submitting.value = true
  try {
    const goal = goals.value.find((item) => item.goal_id === triggerDraft.goalId)
    const updates = { name: triggerDraft.name.trim(), configuration: triggerConfiguration(), run_template: { title: goal?.title || triggerDraft.name.trim(), objective: triggerDraft.objective.trim(), mode: 'assisted' } }
    if (editingTrigger.value) await triggersApi.update(editingTrigger.value.trigger_id, updates)
    else await triggersApi.create({ goal_id: triggerDraft.goalId, trigger_type: triggerDraft.type, ...updates })
    triggerDialogOpen.value = false
    ElMessage.success(editingTrigger.value ? '启动条件已更新' : '启动条件已创建')
    await loadWorkspace()
  } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '保存启动条件失败。')) } finally { submitting.value = false }
}
async function toggleTrigger(trigger, enabled) { try { if (enabled) await triggersApi.resume(trigger.trigger_id); else await triggersApi.pause(trigger.trigger_id); await loadWorkspace() } catch (error) { ElMessage.error(formatAxiosErrorMessage(error, '更新启动条件失败。')) } }
async function removeTrigger(trigger) { try { await ElMessageBox.confirm('删除后不会影响已经创建的行动记录。', '删除启动条件', { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }); await triggersApi.remove(trigger.trigger_id); ElMessage.success('启动条件已删除'); await loadWorkspace() } catch (error) { if (error !== 'cancel' && error !== 'close') ElMessage.error(formatAxiosErrorMessage(error, '删除启动条件失败。')) } }
function triggerDescription(trigger) { const config = trigger.configuration || {}; if (trigger.trigger_type === 'event') return '收到“' + (config.event_type || '指定通知') + '”时开始'; if (config.interval_seconds) { const hours = Math.round(Number(config.interval_seconds) / 3600); return '每隔 ' + hours + ' 小时开始' } const parts = String(config.cron || '').split(/\s+/); if (parts.length >= 5) { const time = String(parts[1]).padStart(2, '0') + ':' + String(parts[0]).padStart(2, '0'); if (parts[4] !== '*') return '每周' + (weekdays.find((day) => day.value === Number(parts[4]))?.label || '') + ' ' + time; return '每天 ' + time } return '按设定时间开始' }

watch(() => route.query.view, (view) => {
  const requested = String(view || 'focus')
  activeView.value = views.value.some((item) => item.value === requested) ? requested : 'focus'
})

watch(() => route.query.run, (runId) => {
  if (!runId || (runDrawerOpen.value && selectedRun.value?.run_id === runId)) return
  activeView.value = 'focus'
  openRun({ run_id: String(runId) })
})

onMounted(async () => {
  const requestedView = String(route.query.view || 'focus')
  activeView.value = views.value.some((item) => item.value === requestedView) ? requestedView : 'focus'
  await loadWorkspace()
  if (route.query.run) await openRun({ run_id: String(route.query.run) })
})
</script>

<style scoped>
.action-workspace { width: min(1240px, calc(100% - 48px)); margin: 0 auto; padding: 42px 0 72px; }
.page-heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 32px; }
.page-kicker, .section-kicker { margin: 0 0 6px; color: var(--color-primary); font-size: 12px; font-weight: 800; }
.page-heading h1 { margin: 0; color: var(--text-primary); font-size: 38px; line-height: 1.16; letter-spacing: 0; }
.page-heading > div > p:last-child { max-width: 640px; margin: 10px 0 0; color: var(--text-secondary); line-height: 1.65; }
.page-heading__actions { display: flex; flex: 0 0 auto; gap: 8px; }
.summary-strip { display: grid; grid-template-columns: repeat(4, 1fr); margin-top: 32px; border-block: 1px solid var(--border-color); }
.summary-strip > div { display: grid; gap: 7px; padding: 18px 22px; border-right: 1px solid var(--border-color-light); }
.summary-strip > div:last-child { border-right: 0; }
.summary-strip span { color: var(--text-muted); font-size: 12px; }
.summary-strip strong { color: var(--text-primary); font-size: 24px; line-height: 1; }
.view-switcher { display: flex; align-items: center; gap: 4px; min-width: 0; margin: 28px 0 24px; border-bottom: 1px solid var(--border-color); }
.view-switcher__tabs { display: flex; flex: 1; align-items: center; min-width: 0; }
.view-switcher__tabs > button { position: relative; display: flex; align-items: center; gap: 8px; min-height: 46px; border: 0; padding: 0 14px; color: var(--text-muted); background: transparent; cursor: pointer; font: inherit; font-size: 14px; }
.view-switcher__tabs > button::after { position: absolute; right: 10px; bottom: -1px; left: 10px; height: 2px; background: transparent; content: ''; }
.view-switcher__tabs > button:hover { color: var(--text-primary); }
.view-switcher__tabs > button.is-active { color: var(--text-primary); font-weight: 700; }
.view-switcher__tabs > button.is-active::after { background: var(--color-primary); }
.view-switcher__tabs small { min-width: 20px; border-radius: 10px; padding: 2px 6px; color: var(--text-muted); background: var(--bg-tertiary); font-size: 10px; }
.view-switcher__refresh { flex: 0 0 36px; margin-left: auto; }
.focus-layout { display: grid; grid-template-columns: minmax(0, 1fr) 330px; gap: 42px; }
.focus-main { min-width: 0; }
.section-block + .section-block { margin-top: 42px; }
.section-heading, .detail-section__heading { display: flex; align-items: flex-end; justify-content: space-between; gap: 20px; margin-bottom: 14px; }
.section-heading h2, .catalog-toolbar h2 { margin: 0; color: var(--text-primary); font-size: 20px; }
.section-heading > span, .detail-section__heading > span { color: var(--text-muted); font-size: 12px; }
.run-list { display: grid; gap: 12px; }
.run-card { box-sizing: border-box; min-width: 0; max-width: 100%; border: 1px solid var(--border-color); border-radius: 8px; padding: 18px 20px; background: var(--bg-secondary); cursor: pointer; transition: border-color .18s ease, box-shadow .18s ease, transform .18s ease; }
.run-card:hover, .run-card:focus-visible { border-color: color-mix(in srgb, var(--color-primary) 42%, var(--border-color)); box-shadow: var(--shadow-sm); transform: translateY(-1px); outline: none; }
.run-card__topline { display: flex; align-items: center; gap: 8px; min-width: 0; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--text-muted); }
.status-dot--running { background: var(--color-primary); box-shadow: 0 0 0 4px color-mix(in srgb, var(--color-primary) 12%, transparent); }
.status-dot--waiting_approval { background: var(--color-warning); }
.run-card__goal { overflow: hidden; flex: 1; min-width: 0; color: var(--text-muted); font-size: 12px; text-overflow: ellipsis; white-space: nowrap; }
.run-card__body { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 24px; min-width: 0; margin: 15px 0; }
.run-card__body > div { min-width: 0; }
.run-card h3 { overflow-wrap: anywhere; margin: 0; color: var(--text-primary); font-size: 17px; }
.run-card__body p { overflow: hidden; margin: 6px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.5; text-overflow: ellipsis; white-space: nowrap; }
.run-card__percent { color: var(--text-primary); font-size: 22px; }
.run-card footer { display: flex; align-items: center; gap: 16px; margin-top: 12px; color: var(--text-muted); font-size: 11px; }
.run-card footer span { display: inline-flex; align-items: center; gap: 5px; }
.run-card footer > .el-icon { margin-left: auto; color: var(--color-primary); }
.recent-list { border-top: 1px solid var(--border-color-light); }
.recent-list button { display: grid; grid-template-columns: 30px minmax(0, 1fr) auto; align-items: center; gap: 12px; width: 100%; border: 0; border-bottom: 1px solid var(--border-color-light); padding: 13px 4px; color: inherit; background: transparent; cursor: pointer; text-align: left; }
.recent-list button:hover { background: var(--bg-secondary); }
.recent-list button > span { display: grid; gap: 3px; min-width: 0; }
.recent-list strong, .recent-list small { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.recent-list strong { font-size: 13px; }.recent-list small { color: var(--text-muted); font-size: 11px; }
.recent-icon--completed { color: var(--color-success); }.recent-icon--failed, .recent-icon--cancelled { color: var(--text-muted); }
.goal-rail { padding-left: 28px; border-left: 1px solid var(--border-color); }
.goal-rail__list article { padding: 3px 0 14px; border-bottom: 1px solid var(--border-color-light); }
.goal-rail__list article + article { padding-top: 14px; }
.goal-rail__list article > button { display: grid; grid-template-columns: 8px minmax(0, 1fr) 18px; align-items: start; gap: 10px; width: 100%; border: 0; padding: 0; color: inherit; background: transparent; cursor: pointer; text-align: left; }
.priority-mark { width: 7px; height: 7px; margin-top: 5px; border-radius: 50%; background: var(--text-muted); }.priority-mark--high { background: var(--color-danger); }.priority-mark--medium { background: var(--color-primary); }
.goal-rail__list button > span:nth-child(2) { display: grid; gap: 4px; min-width: 0; }.goal-rail__list strong { overflow: hidden; font-size: 13px; text-overflow: ellipsis; white-space: nowrap; }.goal-rail__list small { display: -webkit-box; overflow: hidden; color: var(--text-muted); font-size: 11px; line-height: 1.45; -webkit-box-orient: vertical; -webkit-line-clamp: 2; }
.goal-rail__list article > div { display: flex; align-items: center; justify-content: space-between; margin: 8px 0 0 18px; color: var(--text-muted); font-size: 10px; }
.rail-view-all { display: flex; align-items: center; justify-content: space-between; width: 100%; min-height: 44px; border: 0; padding: 12px 0 0; color: var(--color-primary-dark); background: transparent; cursor: pointer; font-size: 12px; font-weight: 700; }
.rail-empty { display: grid; gap: 12px; padding: 22px 0; color: var(--text-muted); font-size: 12px; line-height: 1.6; }
.catalog-view { min-height: 420px; }
.catalog-toolbar { display: flex; align-items: flex-end; justify-content: space-between; gap: 24px; margin-bottom: 20px; }
.catalog-toolbar > div > p:last-child { margin: 6px 0 0; color: var(--text-muted); font-size: 13px; }
.goal-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px; }
.goal-card { display: grid; min-height: 230px; border: 1px solid var(--border-color); border-radius: 8px; padding: 18px; background: var(--bg-secondary); }
.goal-card header, .goal-card footer { display: flex; align-items: center; justify-content: space-between; gap: 12px; }.goal-card header > div { display: flex; align-items: center; gap: 6px; }
.priority-label { color: var(--text-muted); font-size: 11px; font-weight: 700; }.priority-label--high { color: var(--color-danger); }.priority-label--medium { color: var(--color-primary-dark); }
.goal-card__content { align-self: start; border: 0; padding: 18px 0; color: inherit; background: transparent; cursor: pointer; text-align: left; }.goal-card h3 { margin: 0; color: var(--text-primary); font-size: 17px; }.goal-card p { display: -webkit-box; overflow: hidden; margin: 9px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.6; -webkit-box-orient: vertical; -webkit-line-clamp: 3; }
.goal-card footer { align-self: end; border-top: 1px solid var(--border-color-light); padding-top: 14px; }.goal-card footer > span { color: var(--text-muted); font-size: 10px; }
.automation-list { border-top: 1px solid var(--border-color); }
.automation-row { display: grid; grid-template-columns: 42px minmax(0, 1fr) auto; align-items: center; gap: 14px; min-height: 92px; border-bottom: 1px solid var(--border-color-light); padding: 16px 4px; }
.automation-icon { display: grid; place-items: center; width: 38px; height: 38px; border: 1px solid var(--border-color); border-radius: 8px; color: var(--color-primary); background: var(--bg-secondary); }
.automation-copy { display: grid; gap: 5px; min-width: 0; }.automation-copy > div { display: flex; align-items: center; gap: 8px; }.automation-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }.automation-copy p, .automation-copy small { margin: 0; color: var(--text-secondary); font-size: 12px; }.automation-copy small { color: var(--text-muted); }
.automation-actions { display: flex; align-items: center; gap: 4px; }
.empty-state, .loading-state { display: grid; justify-items: center; gap: 11px; padding: 72px 20px; color: var(--text-muted); text-align: center; }.empty-state > .el-icon { color: var(--color-primary); font-size: 30px; }.empty-state h3 { margin: 0; color: var(--text-primary); }.empty-state p { max-width: 390px; margin: 0; color: var(--text-secondary); font-size: 13px; line-height: 1.6; }.loading-state { grid-template-columns: auto auto; justify-content: center; }
.dialog-context { display: grid; gap: 3px; margin-bottom: 18px; border-left: 3px solid var(--color-primary); padding: 6px 12px; background: var(--bg-tertiary); }.dialog-context span { color: var(--text-muted); font-size: 11px; }.dialog-context strong { font-size: 13px; }
.form-row :deep(.el-select), .form-row :deep(.el-input-number), .form-row :deep(.el-input) { width: 100%; }.form-row--two { display: grid; grid-template-columns: 1fr 1fr; gap: 14px; }.field-help { margin-top: 6px; color: var(--text-muted); font-size: 11px; }
.run-detail { min-height: 100%; padding: 28px 30px 48px; }
.run-detail__header { display: grid; grid-template-columns: 36px minmax(0, 1fr) auto; align-items: start; gap: 14px; }.drawer-close { display: grid; place-items: center; width: 34px; height: 34px; border: 1px solid var(--border-color); border-radius: 7px; color: var(--text-secondary); background: transparent; cursor: pointer; }.run-detail__identity { min-width: 0; }.run-detail__identity > span { color: var(--color-primary); font-size: 11px; font-weight: 700; }.run-detail__identity h2 { margin: 4px 0 0; color: var(--text-primary); font-size: 24px; }.run-detail__identity p { margin: 8px 0 0; color: var(--text-secondary); line-height: 1.6; }
.run-progress { display: grid; gap: 9px; margin: 28px 0 22px; }.run-progress > div { display: flex; justify-content: space-between; color: var(--text-muted); font-size: 12px; }.run-progress strong { color: var(--text-primary); }
.approval-panel { display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px 18px; margin: 0 0 16px; border: 1px solid color-mix(in srgb, var(--color-warning) 42%, var(--border-color)); border-radius: 8px; padding: 15px 16px; background: color-mix(in srgb, var(--color-warning) 8%, var(--bg-secondary)); }.approval-panel__copy { display: flex; align-items: flex-start; gap: 10px; min-width: 0; }.approval-panel__copy > .el-icon { flex: 0 0 auto; margin-top: 1px; color: var(--color-warning); font-size: 20px; }.approval-panel__copy span { display: grid; gap: 3px; min-width: 0; }.approval-panel__copy small, .approval-panel__impact { color: var(--text-secondary); font-size: 12px; line-height: 1.55; }.approval-panel__impact { grid-column: 1; margin: -4px 0 0 30px; }.approval-panel__actions { display: flex; align-items: center; gap: 8px; }.approval-history { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin: 0 0 16px; padding: 0 2px; color: var(--text-secondary); font-size: 12px; }.approval-history > span { display: inline-flex; align-items: center; gap: 6px; color: var(--color-success); font-weight: 600; }.approval-history small { color: var(--text-muted); }
.next-action { display: flex; align-items: center; justify-content: space-between; gap: 18px; border-top: 2px solid var(--color-primary); border-bottom: 1px solid var(--border-color); padding: 17px 0 18px; }.next-action--failed { border-top-color: var(--color-danger); }.next-action--waiting_approval { border-top-color: var(--color-warning); }.next-action > div:first-child { display: grid; gap: 4px; min-width: 0; }.next-action strong { color: var(--text-primary); font-size: 17px; }.next-action small { color: var(--text-secondary); font-size: 12px; line-height: 1.55; }.next-action__controls { display: flex; flex: 0 0 auto; gap: 8px; }.run-problem { display: grid; gap: 7px; margin: 18px 0 0; border-left: 3px solid var(--color-danger); padding: 2px 0 2px 12px; }.run-problem > span { display: inline-flex; align-items: center; gap: 6px; color: var(--color-danger); font-size: 13px; font-weight: 700; }.run-problem p { margin: 0; color: var(--text-secondary); font-size: 12px; line-height: 1.6; }.run-problem small { color: var(--text-muted); font-size: 11px; line-height: 1.5; }
.run-toolbar { display: flex; flex-wrap: wrap; gap: 8px; min-height: 38px; margin: 20px 0 30px; }
.detail-section { margin-top: 30px; }.detail-section__heading h3 { margin: 0; color: var(--text-primary); font-size: 17px; }
.step-list { margin: 0; padding: 0; list-style: none; border-top: 1px solid var(--border-color); }.step-item { display: grid; grid-template-columns: 34px minmax(0, 1fr) auto; align-items: start; gap: 12px; border-bottom: 1px solid var(--border-color-light); padding: 16px 0; }.step-index { display: grid; place-items: center; width: 30px; height: 30px; border: 1px solid var(--border-color); border-radius: 50%; color: var(--text-muted); font-size: 11px; font-weight: 700; }.step-item--completed .step-index { border-color: color-mix(in srgb, var(--color-success) 35%, var(--border-color)); color: var(--color-success); background: color-mix(in srgb, var(--color-success) 8%, var(--bg-secondary)); }.step-item--running .step-index, .step-item--ready .step-index { border-color: color-mix(in srgb, var(--color-primary) 40%, var(--border-color)); color: var(--color-primary); }.step-item--failed .step-index { border-color: color-mix(in srgb, var(--color-danger) 45%, var(--border-color)); color: var(--color-danger); }
.step-copy { min-width: 0; }.step-copy > div { display: flex; align-items: center; gap: 8px; }.step-copy h4 { margin: 0; color: var(--text-primary); font-size: 14px; }.step-copy p { margin: 6px 0 0; color: var(--text-secondary); font-size: 12px; line-height: 1.55; }.step-copy small { display: block; margin-top: 6px; color: var(--text-muted); font-size: 10px; }.step-copy__problem { color: var(--color-danger) !important; }.step-actions { display: flex; align-items: center; gap: 4px; }
.command-section { border-top: 1px solid var(--border-color); padding-top: 26px; }.command-composer { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: 10px; }.command-group { margin-top: 18px; }.command-group > strong { color: var(--text-primary); font-size: 12px; }.command-list { display: grid; gap: 8px; margin-top: 9px; }.command-list > div { display: grid; gap: 3px; border-left: 2px solid var(--border-color); padding: 7px 10px; color: var(--text-secondary); font-size: 12px; line-height: 1.5; }.command-group:first-of-type .command-list > div { border-left-color: var(--color-warning); background: color-mix(in srgb, var(--color-warning) 5%, transparent); }.command-group + .command-group .command-list > div { border-left-color: var(--color-success); }.command-list small { color: var(--text-muted); font-size: 11px; }
.history-collapse { margin-top: 30px; border-top: 1px solid var(--border-color); }.history-title { display: flex; align-items: center; gap: 8px; color: var(--text-secondary); }.event-list { display: grid; gap: 0; }.event-list > div { display: grid; grid-template-columns: 12px minmax(0, 1fr); gap: 10px; min-height: 48px; }.event-list > div > span { position: relative; width: 7px; height: 7px; margin-top: 5px; border-radius: 50%; background: var(--color-primary); }.event-list > div > span::after { position: absolute; top: 10px; left: 3px; width: 1px; height: 35px; background: var(--border-color); content: ''; }.event-list > div:last-child > span::after { display: none; }.event-list p { display: grid; gap: 3px; margin: 0; }.event-list strong { font-size: 12px; }.event-list small, .history-empty { color: var(--text-muted); font-size: 10px; }
@media (max-width: 1050px) { .focus-layout { grid-template-columns: minmax(0, 1fr) 280px; gap: 28px; }.goal-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
@media (max-width: 820px) { .page-heading h1 { font-size: 32px; } .action-workspace { width: min(100% - 28px, 760px); padding-top: 28px; }.page-heading { align-items: flex-start; flex-direction: column; }.page-heading__actions { width: 100%; }.page-heading__actions :deep(.el-button) { flex: 1; }.summary-strip { grid-template-columns: repeat(2, 1fr); }.summary-strip > div:nth-child(2) { border-right: 0; }.summary-strip > div:nth-child(n + 3) { border-top: 1px solid var(--border-color-light); }.focus-layout { grid-template-columns: 1fr; }.goal-rail { padding: 28px 0 0; border-top: 1px solid var(--border-color); border-left: 0; }.goal-rail__list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 0 22px; }.catalog-toolbar { align-items: flex-start; flex-direction: column; }.goal-grid { grid-template-columns: 1fr; }.automation-row { grid-template-columns: 42px minmax(0, 1fr); }.automation-actions { grid-column: 2; justify-content: flex-start; }.run-detail { padding: 20px 18px 40px; } }
@media (max-width: 560px) { .view-switcher { display: grid; grid-template-columns: minmax(0, 1fr) 40px; align-items: start; gap: 8px; border-bottom: 0; }.view-switcher__tabs { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 6px; }.view-switcher__tabs > button { justify-content: center; min-width: 0; min-height: 42px; border: 1px solid var(--border-color-light); border-radius: 6px; padding: 0 8px; background: var(--bg-secondary); font-size: 13px; }.view-switcher__tabs > button::after { display: none; }.view-switcher__tabs > button.is-active { border-color: color-mix(in srgb, var(--color-primary) 38%, var(--border-color)); background: color-mix(in srgb, var(--color-primary) 9%, var(--bg-secondary)); color: var(--color-primary-dark); }.view-switcher__tabs small { min-width: 18px; padding: 1px 5px; }.view-switcher__refresh { width: 40px; min-height: 42px; margin-left: 0; border: 1px solid var(--border-color-light); border-radius: 6px; background: var(--bg-secondary); }.summary-strip > div { padding: 15px 14px; }.run-card { padding: 16px; }.run-card__body { gap: 12px; }.run-card__percent { font-size: 18px; }.goal-rail__list { grid-template-columns: 1fr; }.form-row--two { grid-template-columns: 1fr; }.run-detail__header { grid-template-columns: 34px minmax(0, 1fr); }.run-detail__header > .el-tag { grid-column: 2; justify-self: start; }.approval-panel { grid-template-columns: 1fr; }.approval-panel__impact { grid-column: auto; margin-left: 30px; }.approval-panel__actions { width: 100%; justify-content: flex-end; }.approval-history, .next-action { align-items: flex-start; flex-direction: column; }.next-action__controls { width: 100%; }.next-action__controls :deep(.el-button) { flex: 1; }.step-item { grid-template-columns: 30px minmax(0, 1fr); }.step-actions { grid-column: 2; }.command-composer { grid-template-columns: 1fr; }.command-composer :deep(.el-button) { width: 100%; }.automation-row { align-items: start; }.automation-actions { flex-wrap: wrap; } }
.completion-context { display: grid; gap: 4px; margin: -4px 0 20px; border-left: 2px solid var(--color-primary); padding: 4px 0 4px 12px; }
.completion-context span { color: var(--text-muted); font-size: 11px; }
.completion-context strong { color: var(--text-primary); font-size: 15px; line-height: 1.5; }
.completion-result-toggle { display: grid; gap: 4px; margin-top: 4px; border-top: 1px solid var(--border-color-light); padding-top: 16px; }
.completion-result-toggle small { padding-left: 24px; color: var(--text-muted); font-size: 11px; line-height: 1.55; }
.completion-result-fields { margin-top: 16px; border: 1px solid var(--border-color-light); border-radius: 6px; padding: 16px 16px 0; background: color-mix(in srgb, var(--bg-secondary) 55%, transparent); }
.completion-result-fields :deep(.el-select) { width: 100%; }
@media (max-width: 560px) { .completion-result-fields { padding: 14px 12px 0; }.completion-result-toggle small { padding-left: 0; } }
.result-readiness { margin-top: 28px; border-top: 1px solid var(--border-color); border-bottom: 1px solid var(--border-color); padding: 22px 0; }
.result-readiness--ready { border-top-color: color-mix(in srgb, var(--color-success) 35%, var(--border-color)); }
.result-readiness__header { display: flex; align-items: flex-start; justify-content: space-between; gap: 18px; }
.result-readiness__header h3 { margin: 0; color: var(--text-primary); font-size: 17px; }
.result-readiness__header > span { flex: 0 0 auto; color: var(--text-muted); font-size: 11px; line-height: 1.8; }
.result-readiness > p { margin: 10px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.65; }
.review-issues { display: grid; gap: 6px; margin: 14px 0 0; padding: 0; list-style: none; }
.review-issues li { border-left: 2px solid var(--color-warning); background: color-mix(in srgb, var(--color-warning) 6%, transparent); padding: 7px 10px; color: var(--text-secondary); font-size: 12px; line-height: 1.45; }
.deliverable-status { margin-top: 16px; }
.deliverable-status > strong, .evidence-block > strong { color: var(--text-primary); font-size: 12px; }
.deliverable-status ul, .evidence-list { display: grid; gap: 7px; margin: 9px 0 0; padding: 0; list-style: none; }
.deliverable-status li, .evidence-list li { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; min-width: 0; color: var(--text-secondary); font-size: 12px; line-height: 1.5; }
.deliverable-status li span, .evidence-list li > span, .evidence-list li > a { min-width: 0; overflow-wrap: anywhere; }
.deliverable-status li small, .evidence-list small { flex: 0 0 auto; color: var(--text-muted); font-size: 10px; }
.deliverable-status li small.is-recorded { color: var(--color-success); }
.result-readiness > small { display: block; margin-top: 14px; color: var(--text-muted); font-size: 11px; line-height: 1.6; }
.result-review { border-top: 1px solid var(--border-color); padding-top: 28px; }
.result-review__summary { margin: 12px 0 0; color: var(--text-secondary); font-size: 13px; line-height: 1.7; }
.result-evidence { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px 26px; margin-top: 20px; border-top: 1px solid var(--border-color-light); border-bottom: 1px solid var(--border-color-light); padding: 18px 0; }
.evidence-block { min-width: 0; }
.evidence-block p { margin: 9px 0 0; color: var(--text-muted); font-size: 11px; line-height: 1.6; }
.evidence-list a { color: var(--color-primary); text-decoration: none; }
.evidence-list a:hover { text-decoration: underline; }
.reflection-form { margin-top: 22px; border-left: 2px solid var(--color-primary); padding: 2px 0 0 16px; }
.reflection-form > div:first-child > strong { color: var(--text-primary); font-size: 14px; }
.reflection-form > div:first-child > p { margin: 5px 0 18px; color: var(--text-muted); font-size: 11px; line-height: 1.6; }
.reflection-form :deep(.el-form-item) { margin-bottom: 16px; }
.reflection-form :deep(.el-form-item__label) { color: var(--text-secondary); font-size: 12px; }
.reflection-form__actions { display: flex; align-items: center; justify-content: space-between; gap: 14px; border-top: 1px solid var(--border-color-light); padding-top: 16px; }
.reflection-form__actions > small { max-width: 320px; color: var(--text-muted); font-size: 11px; line-height: 1.55; }
.reflection-form__actions > div { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 8px; }
@media (max-width: 560px) { .result-readiness__header, .reflection-form__actions { align-items: flex-start; flex-direction: column; }.result-evidence { grid-template-columns: 1fr; gap: 18px; }.reflection-form { padding-left: 12px; }.reflection-form__actions { gap: 12px; }.reflection-form__actions > div { width: 100%; }.reflection-form__actions :deep(.el-button) { flex: 1; min-width: 0; }.deliverable-status li, .evidence-list li { align-items: flex-start; flex-direction: column; gap: 2px; } }

/* Keep the action workspace dense enough for daily use without feeling like a console. */
.action-workspace { width: min(1240px, calc(100% - 64px)); padding-top: 48px; }
.page-kicker, .section-kicker { color: var(--color-primary-dark); letter-spacing: .06em; text-transform: uppercase; }
.page-heading h1 { font-size: clamp(30px, 3vw, 40px); letter-spacing: -.02em; }
.summary-strip { margin-top: 36px; background: color-mix(in srgb, var(--bg-secondary) 42%, transparent); }
.summary-strip strong { font-size: 26px; font-weight: 750; }
.view-switcher { margin-top: 34px; }
.run-card { padding: 20px 22px; border-color: var(--border-color-light); box-shadow: 0 8px 20px -24px var(--text-primary); }
.run-card:hover, .run-card:focus-visible { box-shadow: 0 16px 28px -24px var(--text-primary); }
@media (max-width: 820px) { .action-workspace { width: min(100% - 32px, 760px); padding-top: 32px; } }
</style>
