const API_BASE_URL = 'http://localhost:8000'

export async function fetchLatestImpact() {
  const response = await fetch(`${API_BASE_URL}/impact/latest`)

  if (!response.ok) {
    throw new Error('Failed to fetch latest impact report')
  }

  return response.json()
}