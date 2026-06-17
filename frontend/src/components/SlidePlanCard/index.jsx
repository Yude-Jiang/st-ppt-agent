import { useState, useEffect } from 'react'
import ArchetypeSelect from '../ArchetypeSelect/index.jsx'
import './SlidePlanCard.css'

function EditableInput({ value, maxLen, onCommit, placeholder }) {
  const [local, setLocal] = useState(value || '')

  useEffect(() => {
    setLocal(value || '')
  }, [value])

  const tooLong = maxLen && local.length > maxLen

  return (
    <input
      type="text"
      className={`card-input ${tooLong ? 'card-input--error' : ''}`}
      value={local}
      placeholder={placeholder}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={() => {
        if (local !== value) onCommit(local)
      }}
    />
  )
}

function EditableTextarea({ value, onCommit, placeholder }) {
  const [local, setLocal] = useState(value || '')

  useEffect(() => {
    setLocal(value || '')
  }, [value])

  return (
    <textarea
      className="card-textarea"
      value={local}
      placeholder={placeholder}
      onChange={(e) => setLocal(e.target.value)}
      onBlur={() => {
        if (local !== value) onCommit(local)
      }}
      rows={3}
    />
  )
}

function BulletList({ bullets, fieldKey, onCommit }) {
  return (
    <div className="card-bullets">
      {(bullets || []).map((bullet, idx) => (
        <div key={idx} className="card-bullet-row">
          <span className="card-bullet-dot">•</span>
          <EditableInput
            value={typeof bullet === 'string' ? bullet : bullet.text || ''}
            maxLen={40}
            onCommit={(val) => {
              const next = [...(bullets || [])]
              if (typeof next[idx] === 'string') {
                next[idx] = val
              } else {
                next[idx] = { ...next[idx], text: val }
              }
              onCommit(fieldKey, next)
            }}
          />
        </div>
      ))}
    </div>
  )
}

export default function SlidePlanCard({ item, onUpdate, compatibleArchetypes }) {
  const { order, archetype, content_fields = {}, user_edited } = item

  function commitField(fieldKey, value) {
    onUpdate({ content_fields: { ...content_fields, [fieldKey]: value } })
  }

  function commitArchetype(newArchetype) {
    onUpdate({ archetype: newArchetype })
  }

  function renderFields() {
    const fields = []

    if ('title' in content_fields) {
      fields.push(
        <div key="title" className="card-field">
          <label className="card-field-label">标题</label>
          <EditableInput
            value={content_fields.title}
            maxLen={18}
            onCommit={(val) => commitField('title', val)}
            placeholder="幻灯片标题"
          />
        </div>
      )
    }

    if ('subtitle' in content_fields) {
      fields.push(
        <div key="subtitle" className="card-field">
          <label className="card-field-label">副标题</label>
          <EditableInput
            value={content_fields.subtitle}
            onCommit={(val) => commitField('subtitle', val)}
            placeholder="副标题"
          />
        </div>
      )
    }

    if ('bullets' in content_fields) {
      fields.push(
        <div key="bullets" className="card-field">
          <label className="card-field-label">要点</label>
          <BulletList
            bullets={content_fields.bullets}
            fieldKey="bullets"
            onCommit={commitField}
          />
        </div>
      )
    }

    if ('left_bullets' in content_fields) {
      fields.push(
        <div key="left_bullets" className="card-field">
          <label className="card-field-label">左侧要点</label>
          <BulletList
            bullets={content_fields.left_bullets}
            fieldKey="left_bullets"
            onCommit={commitField}
          />
        </div>
      )
    }

    if ('right_bullets' in content_fields) {
      fields.push(
        <div key="right_bullets" className="card-field">
          <label className="card-field-label">右侧要点</label>
          <BulletList
            bullets={content_fields.right_bullets}
            fieldKey="right_bullets"
            onCommit={commitField}
          />
        </div>
      )
    }

    if ('steps' in content_fields) {
      fields.push(
        <div key="steps" className="card-field">
          <label className="card-field-label">步骤</label>
          {(content_fields.steps || []).map((step, idx) => (
            <div key={idx} className="card-step">
              <EditableInput
                value={step.title || ''}
                onCommit={(val) => {
                  const next = [...content_fields.steps]
                  next[idx] = { ...next[idx], title: val }
                  commitField('steps', next)
                }}
                placeholder={`步骤 ${idx + 1} 标题`}
              />
              <EditableInput
                value={step.description || ''}
                onCommit={(val) => {
                  const next = [...content_fields.steps]
                  next[idx] = { ...next[idx], description: val }
                  commitField('steps', next)
                }}
                placeholder="描述"
              />
            </div>
          ))}
        </div>
      )
    }

    if ('cards' in content_fields) {
      fields.push(
        <div key="cards" className="card-field">
          <label className="card-field-label">卡片</label>
          {(content_fields.cards || []).map((card, idx) => (
            <div key={idx} className="card-step">
              <EditableInput
                value={card.title || ''}
                onCommit={(val) => {
                  const next = [...content_fields.cards]
                  next[idx] = { ...next[idx], title: val }
                  commitField('cards', next)
                }}
                placeholder={`卡片 ${idx + 1} 标题`}
              />
              <EditableInput
                value={card.content || ''}
                onCommit={(val) => {
                  const next = [...content_fields.cards]
                  next[idx] = { ...next[idx], content: val }
                  commitField('cards', next)
                }}
                placeholder="内容"
              />
            </div>
          ))}
        </div>
      )
    }

    if ('quote' in content_fields) {
      fields.push(
        <div key="quote" className="card-field">
          <label className="card-field-label">引用</label>
          <EditableTextarea
            value={content_fields.quote}
            onCommit={(val) => commitField('quote', val)}
            placeholder="引用内容"
          />
        </div>
      )
    }

    if ('attribution' in content_fields) {
      fields.push(
        <div key="attribution" className="card-field">
          <label className="card-field-label">来源</label>
          <EditableInput
            value={content_fields.attribution}
            onCommit={(val) => commitField('attribution', val)}
            placeholder="引用来源"
          />
        </div>
      )
    }

    const readonlyFields = ['placeholder_hint', 'image_hint']
    readonlyFields.forEach((key) => {
      if (key in content_fields) {
        fields.push(
          <div key={key} className="card-field">
            <label className="card-field-label">{key === 'image_hint' ? '图片提示' : '占位提示'}</label>
            <p className="card-hint">{content_fields[key]}</p>
          </div>
        )
      }
    })

    return fields
  }

  return (
    <div className={`slide-card ${user_edited ? 'slide-card--edited' : ''}`}>
      <div className="slide-card-header">
        <span className="slide-card-order">第 {order} 页</span>
        <span className="slide-card-archetype">{archetype}</span>
        {user_edited && <span className="slide-card-badge">已修改</span>}
      </div>
      <div className="slide-card-body">
        {renderFields()}
      </div>
      <div className="slide-card-footer">
        <ArchetypeSelect
          current={archetype}
          compatibles={compatibleArchetypes}
          onChange={commitArchetype}
        />
      </div>
    </div>
  )
}
