import { useEffect, useState } from 'react'
import { ReactFlow, Background, Controls } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './App.css'

import mockImpactReport from './mockImpactReport'
import { fetchLatestImpact, submitReview } from './api'

function getDecisionStyle(decision) {
  if (decision === 'ACTION') {
    return {
      border: '2px solid #f59e0b',
      background: '#2a1f0f',
      color: '#fbbf24',
      fontWeight: '600',
      padding: '10px 14px',
      minWidth: '150px',
    }
  }

  if (decision === 'REVIEW_REQUIRED') {
    return {
      border: '2px solid #ef4444',
      background: '#2a1111',
      color: '#f87171',
      fontWeight: '600',
      padding: '10px 14px',
      minWidth: '150px',
    }
  }

  if (decision === 'SILENT') {
    return {
      border: '2px solid #64748b',
      background: '#111827',
      color: '#94a3b8',
      fontWeight: '600',
      opacity: 0.45,
      padding: '10px 14px',
      minWidth: '150px',
    }
  }

  return {}
}

const projectEdges = [
  {
    id: 'project-billing',
    source: 'project',
    target: 'billing',
  },
  {
    id: 'billing-batuhan',
    source: 'billing',
    target: 'batuhan',
  },
  {
    id: 'project-db-expert',
    source: 'project',
    target: 'db-expert',
  },
  {
    id: 'project-notification-dev',
    source: 'project',
    target: 'notification-dev',
  },
]

const fullNetworkEdges = [
  ...projectEdges,
  {
    id: 'project-auth',
    source: 'project',
    target: 'auth',
  },
  {
    id: 'auth-hilal',
    source: 'auth',
    target: 'hilal',
  },
]

function App() {
  const [reviewDecision, setReviewDecision] = useState(null)
  const [viewMode, setViewMode] = useState('project')
  const [impactReport, setImpactReport] = useState(mockImpactReport)
  const [dataSource, setDataSource] = useState('mock')

  async function handleReview(decision) {
  try {
    await submitReview('db-expert', decision)
    console.log('Review sent to backend:', decision)
  } catch (error) {
    console.warn('Backend unavailable, applying review locally')
  }

  if (decision === 'approve') {
    setReviewDecision('approved')
  }

  if (decision === 'request_changes') {
    setReviewDecision('changes_requested')
  }
}

  useEffect(() => {
    async function loadImpactReport() {
      try {
        const data = await fetchLatestImpact()
        setImpactReport(data)
        setDataSource('live')
        console.log('Using backend impact report')
      } catch (error) {
        console.warn('Backend unavailable, using mock impact report')
      }
    }

    loadImpactReport()
  }, [])

  const projectNodes = [
    {
      id: 'project',
      position: { x: 60, y: 220 },
      data: { label: 'novaHB Project' },
      style: {
        background: '#f8fafc',
        color: '#0f172a',
        border: '1px solid #cbd5e1',
        fontWeight: '600',
        padding: '10px 16px',
        minWidth: '140px',
      },
    },
    {
      id: 'billing',
      position: { x: 360, y: 100 },
      data: { label: 'Billing Module' },
      style: {
        background: '#f8fafc',
        color: '#0f172a',
        border: '1px solid #cbd5e1',
        fontWeight: '600',
        padding: '10px 16px',
        minWidth: '140px',
      },
    },
    {
      id: 'batuhan',
      position: { x: 720, y: 70 },
      data: {
        label: `Batuhan — ${impactReport.routing[0].decision}`,
      },
      style: getDecisionStyle(impactReport.routing[0].decision),
    },
    {
      id: 'db-expert',
      position: { x: 720, y: 260 },
      data: {
        label:
          reviewDecision === 'approved'
            ? 'Database Expert — APPROVED'
            : reviewDecision === 'changes_requested'
              ? 'Database Expert — CHANGES_REQUESTED'
              : `Database Expert — ${impactReport.routing[1].decision}`,
      },
      style:
        reviewDecision === 'approved'
          ? {
              border: '2px solid #22c55e',
              background: '#052e16',
              color: '#86efac',
              fontWeight: '600',
              padding: '10px 14px',
              minWidth: '150px',
            }
          : reviewDecision === 'changes_requested'
            ? {
                border: '2px solid #ef4444',
                background: '#450a0a',
                color: '#fca5a5',
                fontWeight: '600',
                padding: '10px 14px',
                minWidth: '150px',
              }
            : getDecisionStyle(impactReport.routing[1].decision),
    },
    {
      id: 'notification-dev',
      position: { x: 720, y: 450 },
      data: {
        label: `Notification Developer — ${impactReport.routing[2].decision}`,
      },
      style: getDecisionStyle(impactReport.routing[2].decision),
    },
  ]

  const fullNetworkNodes = [
    ...projectNodes,
    {
      id: 'auth',
      position: { x: 360, y: 350 },
      data: { label: 'Auth Module' },
      style: {
        background: '#f8fafc',
        color: '#0f172a',
        border: '1px solid #cbd5e1',
        fontWeight: '600',
        padding: '10px 16px',
        minWidth: '140px',
      },
    },
    {
      id: 'hilal',
      position: { x: 720, y: 620 },
      data: { label: 'Hilal — Auth / Frontend' },
      style: {
        background: '#0f172a',
        color: '#93c5fd',
        border: '2px solid #3b82f6',
        fontWeight: '600',
        padding: '10px 14px',
        minWidth: '150px',
      },
    },
  ]

  return (
    <div
      style={{
        width: '100vw',
        height: '100vh',
        background: '#0d1117',
        color: 'white',
        overflow: 'hidden',
      }}
    >
      <header
        style={{
          height: '130px',
          padding: '18px 24px',
          boxSizing: 'border-box',
          borderBottom: '1px solid #1f2937',
          background: '#0d1117',
        }}
      >
        <h2 style={{ margin: 0, fontSize: '22px' }}>
          novaHB
        </h2>

        <p
          style={{
            margin: '4px 0 8px',
            color: '#94a3b8',
          }}
        >
          Route attention, not notifications.
        </p>

        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '10px',
            flexWrap: 'wrap',
          }}
        >
          <button
            onClick={() => setViewMode('project')}
            style={{
              background:
                viewMode === 'project' ? '#2563eb' : '#1f2937',
              color:
                viewMode === 'project' ? 'white' : '#94a3b8',
              border: '1px solid #374151',
              padding: '7px 11px',
              borderRadius: '6px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Project Focus
          </button>

          <button
            onClick={() => setViewMode('full')}
            style={{
              background:
                viewMode === 'full' ? '#2563eb' : '#1f2937',
              color:
                viewMode === 'full' ? 'white' : '#94a3b8',
              border: '1px solid #374151',
              padding: '7px 11px',
              borderRadius: '6px',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            Full Network
          </button>

          <button
            style={{
              background: '#1f2937',
              color: '#64748b',
              border: '1px solid #374151',
              padding: '7px 11px',
              borderRadius: '6px',
            }}
          >
            3D
          </button>

          <div
            style={{
              marginLeft: '6px',
              padding: '4px 8px',
              borderRadius: '999px',
              fontSize: '11px',
              fontWeight: '700',
              background:
                dataSource === 'live' ? '#052e16' : '#3f3f46',
              color:
                dataSource === 'live' ? '#86efac' : '#d4d4d8',
              border:
                dataSource === 'live'
                  ? '1px solid #166534'
                  : '1px solid #52525b',
            }}
          >
            {dataSource === 'live' ? 'LIVE API' : 'MOCK DATA'}
          </div>
        </div>
      </header>

      <div
        style={{
          height: 'calc(100vh - 130px)',
          display: 'flex',
        }}
      >
        <aside
          style={{
            width: '320px',
            flexShrink: 0,
            borderRight: '1px solid #1f2937',
            padding: '16px',
            boxSizing: 'border-box',
            overflowY: 'auto',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
            background: '#0d1117',
          }}
        >
          <section
            style={{
              width: '100%',
              boxSizing: 'border-box',
              background: '#111827',
              border: '1px solid #374151',
              borderRadius: '8px',
              padding: '12px',
            }}
          >
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>
              Commit {impactReport.commit.id}
            </div>

            <div
              style={{
                marginTop: '5px',
                fontWeight: '700',
                fontSize: '16px',
              }}
            >
              {impactReport.commit.summary}
            </div>

            <div
              style={{
                marginTop: '5px',
                fontSize: '12px',
                color: '#94a3b8',
              }}
            >
              Author: {impactReport.commit.author}
            </div>

            <div
              style={{
                marginTop: '12px',
                paddingTop: '10px',
                borderTop: '1px solid #374151',
                fontSize: '12px',
                color: '#cbd5e1',
              }}
            >
              {impactReport.semantic_change.summary}
            </div>

            <div
              style={{
                marginTop: '10px',
                display: 'inline-block',
                padding: '4px 8px',
                borderRadius: '999px',
                background: '#3f1d1d',
                color: '#f87171',
                fontSize: '11px',
                fontWeight: '700',
                textTransform: 'uppercase',
              }}
            >
              {impactReport.semantic_change.criticality} criticality
            </div>
          </section>

          <section
            style={{
              width: '100%',
              boxSizing: 'border-box',
              background: '#111827',
              border: '1px solid #f59e0b',
              borderRadius: '8px',
              padding: '12px',
            }}
          >
            <div
              style={{
                fontSize: '12px',
                fontWeight: '700',
                color: '#fbbf24',
              }}
            >
              ACTION — Batuhan
            </div>

            <div
              style={{
                marginTop: '8px',
                fontSize: '13px',
                color: '#cbd5e1',
                lineHeight: '1.5',
              }}
            >
              {impactReport.routing[0].reason}
            </div>

            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop: '1px solid #374151',
                fontSize: '12px',
                color: '#94a3b8',
              }}
            >
              Recommended action
            </div>

            <div
              style={{
                marginTop: '5px',
                fontSize: '13px',
                lineHeight: '1.5',
              }}
            >
              {impactReport.routing[0].recommended_action}
            </div>
          </section>

          <section
            style={{
              width: '100%',
              boxSizing: 'border-box',
              background: '#111827',
              border: '1px solid #ef4444',
              borderRadius: '8px',
              padding: '12px',
            }}
          >
            <div
              style={{
                fontSize: '12px',
                fontWeight: '700',
                color: '#f87171',
              }}
            >
              REVIEW_REQUIRED — Database Expert
            </div>

            <div
              style={{
                marginTop: '8px',
                fontSize: '13px',
                color: '#cbd5e1',
              }}
            >
              {impactReport.routing[1].reason}
            </div>

            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop: '1px solid #374151',
                fontSize: '12px',
                color: '#94a3b8',
              }}
            >
              Recommended review
            </div>

            <div
              style={{
                marginTop: '5px',
                fontSize: '13px',
              }}
            >
              {impactReport.routing[1].recommended_action}
            </div>

            <div
              style={{
                marginTop: '12px',
                display: 'flex',
                gap: '8px',
              }}
            >
              <button
                onClick={() => handleReview('approve')}
                style={{
                  flex: 1,
                  background: '#166534',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                Approve
              </button>

              <button
                onClick={() => handleReview('request_changes')}
                style={{
                  flex: 1,
                  background: '#7f1d1d',
                  color: 'white',
                  border: 'none',
                  borderRadius: '6px',
                  padding: '8px',
                  fontWeight: '600',
                  cursor: 'pointer',
                }}
              >
                Request Changes
              </button>
            </div>

            {reviewDecision === 'approved' && (
              <div
                style={{
                  marginTop: '10px',
                  padding: '8px',
                  borderRadius: '6px',
                  background: '#052e16',
                  color: '#86efac',
                  fontSize: '12px',
                  fontWeight: '700',
                  textAlign: 'center',
                }}
              >
                Review approved
              </div>
            )}

            {reviewDecision === 'changes_requested' && (
              <div
                style={{
                  marginTop: '10px',
                  padding: '8px',
                  borderRadius: '6px',
                  background: '#450a0a',
                  color: '#fca5a5',
                  fontSize: '12px',
                  fontWeight: '700',
                  textAlign: 'center',
                }}
              >
                Changes requested
              </div>
            )}
          </section>

          <section
            style={{
              width: '100%',
              boxSizing: 'border-box',
              background: '#111827',
              border: '1px solid #475569',
              borderRadius: '8px',
              padding: '12px',
              opacity: 0.7,
            }}
          >
            <div
              style={{
                fontSize: '12px',
                fontWeight: '700',
                color: '#94a3b8',
              }}
            >
              SILENT — Notification Developer
            </div>

            <div
              style={{
                marginTop: '8px',
                fontSize: '13px',
                color: '#cbd5e1',
              }}
            >
              {impactReport.routing[2].reason}
            </div>

            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop: '1px solid #374151',
                fontSize: '12px',
                color: '#64748b',
              }}
            >
              No action required
            </div>
          </section>
          <section
  style={{
    width: '100%',
    boxSizing: 'border-box',
    background: '#111827',
    border: '1px solid #2563eb',
    borderRadius: '8px',
    padding: '12px',
  }}
>
  <div
    style={{
      fontSize: '12px',
      fontWeight: '700',
      color: '#93c5fd',
      marginBottom: '10px',
    }}
  >
    DEMO IMPACT
  </div>

  <div
    style={{
      display: 'grid',
      gridTemplateColumns: '1fr 1fr',
      gap: '8px',
    }}
  >
    <div
      style={{
        background: '#0f172a',
        borderRadius: '6px',
        padding: '10px',
      }}
    >
      <div style={{ fontSize: '11px', color: '#94a3b8' }}>
        Traditional routing
      </div>

      <div
        style={{
          marginTop: '4px',
          fontSize: '22px',
          fontWeight: '700',
        }}
      >
        4
      </div>

      <div style={{ fontSize: '11px', color: '#94a3b8' }}>
        notifications
      </div>
    </div>

    <div
      style={{
        background: '#0f172a',
        borderRadius: '6px',
        padding: '10px',
      }}
    >
      <div style={{ fontSize: '11px', color: '#94a3b8' }}>
        novaHB routing
      </div>

      <div
        style={{
          marginTop: '4px',
          fontSize: '22px',
          fontWeight: '700',
          color: '#86efac',
        }}
      >
        2
      </div>

      <div style={{ fontSize: '11px', color: '#94a3b8' }}>
        attention events
      </div>
    </div>
  </div>

  <div
    style={{
      marginTop: '10px',
      paddingTop: '10px',
      borderTop: '1px solid #374151',
      fontSize: '12px',
      color: '#cbd5e1',
      lineHeight: '1.5',
    }}
  >
    1 ACTION · 1 REVIEW_REQUIRED · 2 SILENT
  </div>

  <div
    style={{
      marginTop: '8px',
      color: '#86efac',
      fontWeight: '700',
      fontSize: '13px',
    }}
  >
    50% fewer attention events in this controlled demo
  </div>
</section>
        </aside>

        <main
          style={{
            flex: 1,
            minWidth: 0,
            position: 'relative',
            background: '#0d1117',
          }}
        >
          <ReactFlow
            nodes={
              viewMode === 'full'
                ? fullNetworkNodes
                : projectNodes
            }
            edges={
              viewMode === 'full'
                ? fullNetworkEdges
                : projectEdges
            }
            fitView
            fitViewOptions={{
              padding: 0.08,
            }}
          >
            <Background />
            <Controls position="bottom-right" />
          </ReactFlow>
        </main>
      </div>
    </div>
  )
}

export default App