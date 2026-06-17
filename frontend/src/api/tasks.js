const BASE = '/api'

export const ARCHETYPE_COMPAT = {
  'title-slide': ['section-divider'],
  'title-bullets': ['two-column', 'quote-highlight'],
  'title-image': ['content-placeholder', 'title-bullets'],
  'two-column': ['title-bullets', 'product-comparison-2up'],
  'three-column': ['cards-row'],
  'product-comparison-2up': ['two-column'],
  'process-flow': ['cards-row', 'three-column'],
  'cards-row': ['three-column', 'process-flow'],
  'quote-highlight': ['title-bullets', 'section-divider'],
  'content-placeholder': ['title-image', 'title-bullets'],
  'section-divider': ['title-slide', 'quote-highlight'],
}

async function handleResponse(res) {
  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      msg = body.detail || body.message || msg
    } catch (_) {}
    throw new Error(msg)
  }
  return res.json()
}

export async function submitTask(text, targetSlides) {
  const body = { text }
  if (targetSlides != null && targetSlides !== '') {
    body.target_slides = Number(targetSlides)
  }
  const res = await fetch(`${BASE}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse(res)
}

export async function getTask(taskId) {
  const res = await fetch(`${BASE}/tasks/${taskId}`)
  return handleResponse(res)
}

export async function patchItem(taskId, order, updates) {
  const res = await fetch(`${BASE}/tasks/${taskId}/items/${order}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  })
  return handleResponse(res)
}

export async function confirmPlan(taskId) {
  const res = await fetch(`${BASE}/tasks/${taskId}/confirm`, {
    method: 'POST',
  })
  return handleResponse(res)
}

export async function replanTask(taskId, targetSlides) {
  const body = {}
  if (targetSlides != null && targetSlides !== '') {
    body.target_slides = Number(targetSlides)
  }
  const res = await fetch(`${BASE}/tasks/${taskId}/replan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return handleResponse(res)
}

export async function renderTask(taskId) {
  const res = await fetch(`${BASE}/tasks/${taskId}/render`, {
    method: 'POST',
  })
  return handleResponse(res)
}

export async function pollUntil(taskId, targetStatuses, intervalMs = 2000, timeoutMs = 180000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const task = await getTask(taskId)
    if (targetStatuses.includes(task.status)) {
      return task
    }
    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }
  throw new Error(`任务 ${taskId} 轮询超时（${timeoutMs / 1000}秒）`)
}
