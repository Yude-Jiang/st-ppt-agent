import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import {
  getTask,
  patchItem,
  confirmPlan,
  replanTask,
  renderTask,
  pollUntil,
  ARCHETYPE_COMPAT,
} from '../../api/tasks.js'
import SlidePlanCard from '../../components/SlidePlanCard/index.jsx'
import './Review.css'

export default function Review() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const taskId = searchParams.get('task_id')

  const [task, setTask] = useState(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [error, setError] = useState(null)
  const [targetSlides, setTargetSlides] = useState('')

  const loadTask = useCallback(async () => {
    if (!taskId) return
    try {
      const t = await getTask(taskId)
      setTask(t)
      if (t.status === 'pending' || t.status === 'planning') {
        const updated = await pollUntil(taskId, ['draft', 'failed'])
        setTask(updated)
      }
    } catch (err) {
      setError(err.message || '加载任务失败')
    } finally {
      setLoading(false)
    }
  }, [taskId])

  useEffect(() => {
    if (!taskId) {
      navigate('/')
      return
    }
    loadTask()
  }, [taskId, loadTask, navigate])

  async function handleUpdate(order, updates) {
    try {
      const updated = await patchItem(taskId, order, updates)
      setTask((prev) => {
        if (!prev) return prev
        return {
          ...prev,
          slide_plan: {
            ...prev.slide_plan,
            items: prev.slide_plan.items.map((item) =>
              item.order === order ? { ...item, ...updated, user_edited: true } : item
            ),
          },
        }
      })
    } catch (err) {
      setError(err.message || '更新失败')
    }
  }

  async function handleReplan() {
    setError(null)
    setActionLoading(true)
    try {
      await replanTask(taskId, targetSlides)
      const updated = await pollUntil(taskId, ['draft', 'failed'])
      setTask(updated)
    } catch (err) {
      setError(err.message || '重新规划失败')
    } finally {
      setActionLoading(false)
    }
  }

  async function handleConfirmAndRender() {
    setError(null)
    setActionLoading(true)
    try {
      await confirmPlan(taskId)
      await renderTask(taskId)
      const updated = await pollUntil(taskId, ['done', 'failed'])
      setTask(updated)
    } catch (err) {
      setError(err.message || '生成失败')
    } finally {
      setActionLoading(false)
    }
  }

  if (!taskId) return null

  if (loading) {
    return (
      <div className="review-loading">
        <span className="spinner" />
        <span>加载任务中...</span>
      </div>
    )
  }

  if (error && !task) {
    return (
      <div className="review-error-page">
        <div className="review-error-box">{error}</div>
        <button className="review-btn-secondary" onClick={() => navigate('/')}>
          返回首页
        </button>
      </div>
    )
  }

  if (!task) return null

  const items = task.slide_plan?.items || []

  return (
    <div className="review-container">
      <div className="review-header">
        <h1 className="review-title">PPT 规划预览</h1>
        <button
          className="review-btn-secondary"
          onClick={() => navigate('/')}
          disabled={actionLoading}
        >
          ← 重新输入
        </button>
      </div>

      {error && <div className="review-error">{error}</div>}

      {(task.status === 'pending' || task.status === 'planning') && (
        <div className="review-loading-inline">
          <span className="spinner" />
          AI 正在规划分页，请稍候...
        </div>
      )}

      {task.status === 'draft' && (
        <>
          <div className="review-controls">
            <label className="review-label">
              目标页数
              <input
                type="number"
                className="review-slides-input"
                value={targetSlides}
                onChange={(e) => setTargetSlides(e.target.value)}
                min={1}
                max={50}
                placeholder="自动"
                disabled={actionLoading}
              />
            </label>
            <button
              className="review-btn-secondary"
              onClick={handleReplan}
              disabled={actionLoading}
            >
              {actionLoading ? <><span className="spinner" />处理中...</> : '重新规划'}
            </button>
          </div>

          <div className="review-cards">
            {items.map((item) => (
              <SlidePlanCard
                key={item.order}
                item={item}
                onUpdate={(updates) => handleUpdate(item.order, updates)}
                compatibleArchetypes={ARCHETYPE_COMPAT[item.archetype] || []}
              />
            ))}
          </div>

          <div className="review-footer">
            <p className="review-footer-info">共 {items.length} 张幻灯片</p>
            <button
              className="review-btn-primary"
              onClick={handleConfirmAndRender}
              disabled={actionLoading}
            >
              {actionLoading ? (
                <><span className="spinner" />正在生成 .pptx...</>
              ) : (
                '确认并生成 PPT'
              )}
            </button>
          </div>
        </>
      )}

      {task.status === 'rendering' && (
        <div className="review-loading-inline">
          <span className="spinner" />
          正在渲染 .pptx 文件，请稍候...
        </div>
      )}

      {task.status === 'done' && task.generated_deck && (
        <div className="review-done">
          <div className="review-done-icon">✓</div>
          <h2>PPT 已生成完成！</h2>
          <p>文件将在 7 天后过期</p>
          <a
            href={task.generated_deck.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="review-btn-primary review-download-btn"
          >
            下载 .pptx 文件
          </a>
          <button
            className="review-btn-secondary"
            onClick={() => navigate('/')}
          >
            生成新的 PPT
          </button>
        </div>
      )}

      {task.status === 'failed' && (
        <div className="review-failed">
          <div className="review-error-box">
            任务失败：{task.error_message || '未知错误'}
          </div>
          <button
            className="review-btn-secondary"
            onClick={() => navigate('/')}
          >
            返回重试
          </button>
        </div>
      )}
    </div>
  )
}
