import test from 'node:test'
import assert from 'node:assert/strict'

import {
  BACKGROUND_WORK_KIND,
  BACKGROUND_WORK_STATE,
  backgroundWorkPresentation,
  knowledgeJobToBackgroundWork,
  planGenerationToBackgroundWork
} from '../src/domain/backgroundWork.js'

function generation(overrides = {}) {
  return {
    generation_id: 'generation-1',
    status: 'generating',
    stage: 'generating_steps',
    progress: 46,
    topic: '完成个人作品集',
    created_at: '2026-07-18T08:00:00.000Z',
    updated_at: '2026-07-18T08:01:00.000Z',
    ...overrides
  }
}

test('active Plan Generation progress is copied from the server without local estimation', () => {
  const work = planGenerationToBackgroundWork(generation({ progress: 46.7 }))

  assert.equal(work.state, BACKGROUND_WORK_STATE.ACTIVE)
  assert.equal(work.progress, 46.7)
  assert.equal(work.source_id, 'generation-1')
  assert.equal(work.result_ref, null)
  assert.deepEqual(backgroundWorkPresentation(work), {
    title: '正在生成可执行步骤',
    copy: '正在生成方案，完成后会检查内容完整性。'
  })
})

test('ready Plan Generation exposes only its durable Draft reference', () => {
  const work = planGenerationToBackgroundWork(generation({
    status: 'ready',
    progress: 100,
    draft_id: 'draft-1'
  }))

  assert.equal(work.state, BACKGROUND_WORK_STATE.READY)
  assert.deepEqual(work.result_ref, { draft_id: 'draft-1' })
  assert.equal(work.raw.result, undefined)
  assert.equal(backgroundWorkPresentation(work).title, '方案已准备好')
})

test('failed and cancelled jobs keep server-provided terminal meaning', () => {
  const failed = planGenerationToBackgroundWork(generation({
    status: 'failed',
    error_message: '模型没有返回可用的结构化结果。'
  }))
  const cancelled = planGenerationToBackgroundWork(generation({ status: 'cancelled' }))

  assert.equal(failed.state, BACKGROUND_WORK_STATE.FAILED)
  assert.equal(backgroundWorkPresentation(failed).copy, '模型没有返回可用的结构化结果。')
  assert.equal(cancelled.state, BACKGROUND_WORK_STATE.CANCELLED)
  assert.equal(backgroundWorkPresentation(cancelled).title, '方案生成已停止')
})

test('knowledge jobs share durable background state without exposing worker internals', () => {
  const work = knowledgeJobToBackgroundWork({
    job_id: 'knowledge-1',
    status: 'processing',
    stage: 'extracting_content',
    progress: 35,
    document_title: '项目笔记',
    document_name: 'notes.txt',
    created_at: '2026-07-18T08:00:00.000Z',
    updated_at: '2026-07-18T08:01:00.000Z'
  })

  assert.equal(work.kind, BACKGROUND_WORK_KIND.KNOWLEDGE_PROCESSING)
  assert.equal(work.state, BACKGROUND_WORK_STATE.ACTIVE)
  assert.equal(work.title, '项目笔记')
  assert.equal(work.progress, 35)
  assert.deepEqual(backgroundWorkPresentation(work), {
    title: '正在提取内容',
    copy: '正在提取可供后续检索使用的内容。'
  })
})

test('malformed jobs fail loudly instead of becoming anonymous work', () => {
  assert.throws(() => planGenerationToBackgroundWork({ status: 'generating' }), /计划生成任务缺少服务端标识/)
  assert.throws(() => knowledgeJobToBackgroundWork({ status: 'processing' }), /知识处理任务缺少服务端标识/)
})
