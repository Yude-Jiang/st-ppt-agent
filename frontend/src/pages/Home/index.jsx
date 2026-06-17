import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { submitTask, pollUntil } from '../../api/tasks.js'
import './Home.css'

export default function Home() {
  const navigate = useNavigate()
  const [text, setText] = useState('')
  const [targetSlides, setTargetSlides] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    if (!text.trim()) {
      setError('请粘贴文案内容')
      return
    }
    setError(null)
    setLoading(true)
    try {
      const { task_id } = await submitTask(text.trim(), targetSlides)
      await pollUntil(task_id, ['draft', 'failed'])
      navigate(`/review?task_id=${task_id}`)
    } catch (err) {
      setError(err.message || '发生未知错误')
      setLoading(false)
    }
  }

  return (
    <div className="home-container">
      <div className="home-card">
        <h1 className="home-title">ST PPT Agent</h1>
        <p className="home-subtitle">粘贴文案，AI 自动规划 PPT 分页结构</p>
        <form onSubmit={handleSubmit} className="home-form">
          <textarea
            className="home-textarea"
            placeholder="粘贴产品或技术介绍文案..."
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={loading}
            rows={12}
          />
          <div className="home-options">
            <label className="home-label">
              目标页数（留空由 AI 自动决定）
              <input
                type="number"
                className="home-slides-input"
                value={targetSlides}
                onChange={(e) => setTargetSlides(e.target.value)}
                min={1}
                max={50}
                disabled={loading}
                placeholder="自动"
              />
            </label>
          </div>
          {error && <div className="home-error">{error}</div>}
          <button type="submit" className="home-btn" disabled={loading}>
            {loading ? (
              <>
                <span className="spinner" />
                AI 正在规划分页，请稍候...
              </>
            ) : (
              '开始生成 PPT 规划'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
