const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

export async function fetchLatestImpact() {
  const response = await fetch(`${API_BASE_URL}/impact/latest`)
  if (!response.ok) throw new Error('Failed to fetch latest impact report')
  return response.json()
}

export async function submitReview(developerId, decision) {
  const response = await fetch(`${API_BASE_URL}/review/${developerId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision }),
  })
  if (!response.ok) throw new Error('Failed to submit review decision')
  return response.json()
}

export async function analyzeChange() {
  const response = await fetch(`${API_BASE_URL}/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
  if (!response.ok) throw new Error('Failed to analyze change')
  return response.json()
}

export async function fetchNotification(developerId) {
  const response = await fetch(`${API_BASE_URL}/notify/${developerId}`)
  if (!response.ok) throw new Error('Failed to fetch notification')
  return response.json()
}

export async function submitNotificationAnswer(developerId, optionId) {
  const response = await fetch(`${API_BASE_URL}/notify/${developerId}/ask`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ option_id: optionId }),
  })
  if (!response.ok) throw new Error('Failed to submit notification answer')
  return response.json()
}
