import { useEffect, useState } from 'react'
import { ReactFlow, Background, Controls } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './App.css'
import Network3D from './Network3D'

import mockImpactReport from './mockImpactReport'
import {
  analyzeChange,
  fetchLatestImpact,
  submitReview,
} from './api'

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

function formatDeveloperName(id) {
  if (!id) return 'Unknown'

  return id
    .split('-')
    .map(
      (part) =>
        part.charAt(0).toUpperCase() + part.slice(1)
    )
    .join(' ')
}

const projectEdges = [
  {
    id: 'project-billing',
    source: 'project',
    target: 'billing',
  },
  {
    id: 'billing-action',
    source: 'billing',
    target: 'action-dev',
  },
  {
    id: 'project-review',
    source: 'project',
    target: 'review-dev',
  },
  {
    id: 'project-silent',
    source: 'project',
    target: 'silent-dev',
  },
]



function App() {
  const [reviewDecision, setReviewDecision] = useState(null)
  const [viewMode, setViewMode] = useState('project')
  const [impactReport, setImpactReport] =
    useState(mockImpactReport)

  const [dataSource, setDataSource] = useState('mock')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [hasAnalyzed, setHasAnalyzed] = useState(true)
  const [showResultHighlight, setShowResultHighlight] =
    useState(false)

  const actionRoute =
    impactReport.routing.find(
      (item) => item.decision === 'ACTION'
    ) ??
    mockImpactReport.routing.find(
      (item) => item.decision === 'ACTION'
    )

  const reviewRoute =
    impactReport.routing.find(
      (item) => item.decision === 'REVIEW_REQUIRED'
    ) ??
    mockImpactReport.routing.find(
      (item) => item.decision === 'REVIEW_REQUIRED'
    )

  const silentRoutes = impactReport.routing.filter(
    (item) => item.decision === 'SILENT'
  )

  const notificationSilentRoute =
    silentRoutes.find((item) => {
      const text = `${item.developer_id} ${item.reason}`.toLowerCase()

      return (
        text.includes('notification') ||
        item.developer_id === 'ayse'
      )
    }) ??
    silentRoutes[0] ??
    mockImpactReport.routing.find(
      (item) => item.decision === 'SILENT'
    )

  const actionCount = impactReport.routing.filter(
    (item) => item.decision === 'ACTION'
  ).length

  const reviewCount = impactReport.routing.filter(
    (item) => item.decision === 'REVIEW_REQUIRED'
  ).length

  const silentCount = silentRoutes.length

  const attentionCount = actionCount + reviewCount

  useEffect(() => {
    async function loadImpactReport() {
      try {
        const data = await fetchLatestImpact()

        setImpactReport(data)
        setDataSource('live')

        console.log('Using backend impact report')
      } catch (error) {
        console.warn(
          'Backend unavailable, using mock impact report'
        )
      }
    }

    loadImpactReport()
  }, [])

  async function handleReview(decision) {
    try {
      await submitReview(
        reviewRoute.developer_id,
        decision
      )

      console.log(
        'Review sent to backend:',
        decision
      )
    } catch (error) {
      console.warn(
        'Backend unavailable, applying review locally'
      )
    }

    if (decision === 'approve') {
      setReviewDecision('approved')
    }

    if (decision === 'request_changes') {
      setReviewDecision('changes_requested')
    }
  }

  async function handleAnalyze() {
    setIsAnalyzing(true)
    setHasAnalyzed(false)
    setReviewDecision(null)

    try {
      const data = await analyzeChange()

      setImpactReport(data)
      setDataSource('live')
    } catch (error) {
      console.warn(
        'Backend unavailable, using mock analysis'
      )

      await new Promise((resolve) =>
        setTimeout(resolve, 1200)
      )

      setImpactReport(mockImpactReport)
      setDataSource('mock')
    } finally {
      setIsAnalyzing(false)
      setHasAnalyzed(true)

      setShowResultHighlight(true)

      setTimeout(() => {
        setShowResultHighlight(false)
      }, 1800)
    }
  }

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
      id: 'action-dev',
      position: { x: 720, y: 70 },
      data: {
        label: `${formatDeveloperName(
          actionRoute.developer_id
        )} — ${actionRoute.decision}`,
      },
      style: getDecisionStyle(
        actionRoute.decision
      ),
    },
    {
      id: 'review-dev',
      position: { x: 720, y: 260 },
      data: {
        label:
          reviewDecision === 'approved'
            ? `${formatDeveloperName(
                reviewRoute.developer_id
              )} — APPROVED`
            : reviewDecision === 'changes_requested'
              ? `${formatDeveloperName(
                  reviewRoute.developer_id
                )} — CHANGES_REQUESTED`
              : `${formatDeveloperName(
                  reviewRoute.developer_id
                )} — ${reviewRoute.decision}`,
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
          : reviewDecision ===
              'changes_requested'
            ? {
                border: '2px solid #ef4444',
                background: '#450a0a',
                color: '#fca5a5',
                fontWeight: '600',
                padding: '10px 14px',
                minWidth: '150px',
              }
            : getDecisionStyle(
                reviewRoute.decision
              ),
    },
    {
      id: 'silent-dev',
      position: { x: 720, y: 450 },
      data: {
        label: `${formatDeveloperName(
          notificationSilentRoute.developer_id
        )} — ${notificationSilentRoute.decision}`,
      },
      style: getDecisionStyle(
        notificationSilentRoute.decision
      ),
    },
  ]

    const affectedModules =
    impactReport.affected_modules ?? []

  const routingItems =
    impactReport.routing ?? []

  const moduleNodes = affectedModules.map(
    (module, index) => ({
      id: `module-${module.module}`,
      position: {
        x: 360,
        y: 60 + index * 170,
      },
      data: {
        label: `${module.module.toUpperCase()} · ${module.status}`,
      },
      style: {
        background:
          module.status === 'affected'
            ? '#2a1710'
            : '#10231b',
        color:
          module.status === 'affected'
            ? '#fdba74'
            : '#86efac',
        border:
          module.status === 'affected'
            ? '1px solid #f97316'
            : '1px solid #22c55e',
        fontWeight: '700',
        padding: '12px 16px',
        minWidth: '170px',
        borderRadius: '8px',
      },
    })
  )

  const developerNodes = routingItems.map(
    (route, index) => ({
      id: `developer-${route.developer_id}`,
      position: {
        x: 760,
        y: 20 + index * 115,
      },
      data: {
        label: `${formatDeveloperName(
          route.developer_id
        )} · ${route.decision}`,
      },
      style: getDecisionStyle(route.decision),
    })
  )

  const projectRootNode =
    projectNodes.find(
      (node) => node.id === 'project'
    ) ?? projectNodes[0]

  const fullNetworkNodes = [
    {
      ...projectRootNode,
      position: {
        x: 20,
        y: 260,
      },
    },
    ...moduleNodes,
    ...developerNodes,
  ]

  const fullNetworkEdges = [
    ...affectedModules.map((module) => ({
      id: `project-module-${module.module}`,
      source: 'project',
      target: `module-${module.module}`,
    })),

    ...routingItems.map((route) => {
      const reason =
        route.reason?.toLowerCase() ?? ''

      const matchedModule =
        affectedModules.find((module) =>
          reason.includes(
            module.module.toLowerCase()
          )
        )

      return {
        id: `route-${route.developer_id}`,
        source: matchedModule
          ? `module-${matchedModule.module}`
          : 'project',
        target: `developer-${route.developer_id}`,
      }
    }),
  ]
  const highlightedProjectEdges =
    projectEdges.map((edge) => {
      if (!showResultHighlight) {
        return edge
      }

      if (edge.id === 'project-silent') {
        return {
          ...edge,
          style: {
            stroke: '#475569',
            strokeWidth: 1.5,
            opacity: 0.25,
          },
        }
      }

      if (edge.id === 'billing-action') {
        return {
          ...edge,
          animated: true,
          style: {
            stroke: '#f59e0b',
            strokeWidth: 3,
          },
        }
      }

      if (edge.id === 'project-review') {
        return {
          ...edge,
          animated: true,
          style: {
            stroke: '#ef4444',
            strokeWidth: 3,
          },
        }
      }

      return {
        ...edge,
        animated: true,
        style: {
          stroke: '#8b5cf6',
          strokeWidth: 2.5,
        },
      }
    })

    const highlightedFullNetworkEdges =
    fullNetworkEdges.map((edge) => {
      if (!showResultHighlight) {
        return {
          ...edge,
          style: {
            stroke: '#475569',
            strokeWidth: 1.8,
          },
        }
      }

      const route = routingItems.find(
        (item) =>
          edge.target ===
          `developer-${item.developer_id}`
      )

      if (!route) {
        const module =
          affectedModules.find(
            (item) =>
              edge.target ===
              `module-${item.module}`
          )

        return {
          ...edge,
          style: {
            stroke:
              module?.status === 'affected'
                ? '#f97316'
                : '#475569',
            strokeWidth:
              module?.status === 'affected'
                ? 2.6
                : 1.6,
            opacity:
              module?.status === 'affected'
                ? 1
                : 0.55,
          },
        }
      }

      const decisionColors = {
        ACTION: '#f59e0b',
        REVIEW_REQUIRED: '#ef4444',
        SILENT: '#64748b',
      }

      return {
        ...edge,
        animated:
          route.decision !== 'SILENT',
        style: {
          stroke:
            decisionColors[
              route.decision
            ] ?? '#8b5cf6',
          strokeWidth:
            route.decision === 'SILENT'
              ? 1.5
              : 3,
          opacity:
            route.decision === 'SILENT'
              ? 0.3
              : 1,
        },
      }
    })

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
        <h2
          style={{
            margin: 0,
            fontSize: '22px',
          }}
        >
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
            onClick={() =>
              setViewMode('project')
            }
            style={{
              background:
                viewMode === 'project'
                  ? '#2563eb'
                  : '#1f2937',
              color:
                viewMode === 'project'
                  ? 'white'
                  : '#94a3b8',
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
            onClick={() =>
              setViewMode('full')
            }
            style={{
              background:
                viewMode === 'full'
                  ? '#2563eb'
                  : '#1f2937',
              color:
                viewMode === 'full'
                  ? 'white'
                  : '#94a3b8',
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
  onClick={() => setViewMode('3d')}
  style={{
    background:
      viewMode === '3d'
        ? '#7c3aed'
        : '#1f2937',
    color:
      viewMode === '3d'
        ? 'white'
        : '#94a3b8',
    border: '1px solid #374151',
    padding: '7px 11px',
    borderRadius: '6px',
    fontWeight: '600',
    cursor: 'pointer',
  }}
>
  3D
</button>

          <button
            onClick={handleAnalyze}
            disabled={isAnalyzing}
            style={{
              background: isAnalyzing
                ? '#374151'
                : '#7c3aed',
              color: 'white',
              border: '1px solid #8b5cf6',
              padding: '7px 12px',
              borderRadius: '6px',
              fontWeight: '700',
              cursor: isAnalyzing
                ? 'not-allowed'
                : 'pointer',
            }}
          >
            {isAnalyzing
              ? 'Analyzing...'
              : 'Analyze Change'}
          </button>

          <div
            style={{
              marginLeft: '6px',
              padding: '4px 8px',
              borderRadius: '999px',
              fontSize: '11px',
              fontWeight: '700',
              background:
                dataSource === 'live'
                  ? '#052e16'
                  : '#3f3f46',
              color:
                dataSource === 'live'
                  ? '#86efac'
                  : '#d4d4d8',
              border:
                dataSource === 'live'
                  ? '1px solid #166534'
                  : '1px solid #52525b',
            }}
          >
            {dataSource === 'live'
              ? 'LIVE API'
              : 'MOCK DATA'}
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
            <div
              style={{
                fontSize: '12px',
                color: '#94a3b8',
              }}
            >
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
                borderTop:
                  '1px solid #374151',
                fontSize: '12px',
                color: '#cbd5e1',
              }}
            >
              {
                impactReport.semantic_change
                  .summary
              }
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
              {
                impactReport.semantic_change
                  .criticality
              }{' '}
              criticality
                       </div>

            {impactReport?.semantic_change?.broken_contracts?.length > 0 && (
              <div
                style={{
                  marginTop: '12px',
                  padding: '10px',
                  background: '#1e1b4b',
                  border: '1px solid #7c3aed',
                  borderRadius: '7px',
                }}
              >
                <div
                  style={{
                    fontSize: '11px',
                    fontWeight: '700',
                    color: '#c4b5fd',
                    marginBottom: '7px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.04em',
                  }}
                >
                  Bob Semantic Insight · Broken Contracts
                </div>

                <ul
                  style={{
                    margin: 0,
                    paddingLeft: '18px',
                    color: '#ddd6fe',
                    fontSize: '12px',
                    lineHeight: '1.6',
                  }}
                >
                  {impactReport.semantic_change.broken_contracts.map(
                    (contract, index) => (
                      <li key={`${contract}-${index}`}>
                        {contract}
                      </li>
                    )
                  )}
                </ul>
              </div>
            )}
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
              ACTION —{' '}
              {formatDeveloperName(
                actionRoute.developer_id
              )}
            </div>

            <div
              style={{
                marginTop: '8px',
                fontSize: '13px',
                color: '#cbd5e1',
                lineHeight: '1.5',
              }}
            >
              {actionRoute.reason}
            </div>

            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop:
                  '1px solid #374151',
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
              {actionRoute.recommended_action}
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
              REVIEW_REQUIRED —{' '}
              {formatDeveloperName(
                reviewRoute.developer_id
              )}
            </div>

            <div
              style={{
                marginTop: '8px',
                fontSize: '13px',
                color: '#cbd5e1',
              }}
            >
              {reviewRoute.reason}
            </div>

            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop:
                  '1px solid #374151',
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
              {reviewRoute.recommended_action}
            </div>

            <div
              style={{
                marginTop: '12px',
                display: 'flex',
                gap: '8px',
              }}
            >
              <button
                onClick={() =>
                  handleReview('approve')
                }
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
                onClick={() =>
                  handleReview(
                    'request_changes'
                  )
                }
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

            {reviewDecision ===
              'approved' && (
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

            {reviewDecision ===
              'changes_requested' && (
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
              SILENT —{' '}
              {formatDeveloperName(
                notificationSilentRoute.developer_id
              )}
            </div>

            <div
              style={{
                marginTop: '8px',
                fontSize: '13px',
                color: '#cbd5e1',
              }}
            >
              {notificationSilentRoute.reason}
            </div>

            <div
              style={{
                marginTop: '10px',
                paddingTop: '8px',
                borderTop:
                  '1px solid #374151',
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
              ANALYSIS IMPACT
            </div>

            <div
              style={{
                display: 'grid',
                gridTemplateColumns:
                  '1fr 1fr',
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
                <div
                  style={{
                    fontSize: '11px',
                    color: '#94a3b8',
                  }}
                >
                  Developers evaluated
                </div>

                <div
                  style={{
                    marginTop: '4px',
                    fontSize: '22px',
                    fontWeight: '700',
                  }}
                >
                  {impactReport.routing.length}
                </div>
              </div>

              <div
                style={{
                  background: '#0f172a',
                  borderRadius: '6px',
                  padding: '10px',
                }}
              >
                <div
                  style={{
                    fontSize: '11px',
                    color: '#94a3b8',
                  }}
                >
                  Attention events
                </div>

                <div
                  style={{
                    marginTop: '4px',
                    fontSize: '22px',
                    fontWeight: '700',
                    color: '#86efac',
                  }}
                >
                  {attentionCount}
                </div>
              </div>
            </div>

            <div
              style={{
                marginTop: '10px',
                paddingTop: '10px',
                borderTop:
                  '1px solid #374151',
                fontSize: '12px',
                color: '#cbd5e1',
                lineHeight: '1.6',
              }}
            >
              {actionCount} ACTION ·{' '}
              {reviewCount} REVIEW_REQUIRED ·{' '}
              {silentCount} SILENT
            </div>

            <div
              style={{
                marginTop: '8px',
                color: '#86efac',
                fontWeight: '700',
                fontSize: '13px',
              }}
            >
              {silentCount} developers kept
              silent because no action was
              required
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
          {hasAnalyzed ? (
  viewMode === '3d' ? (
    <Network3D
      impactReport={impactReport}
    />
  ) : (
    <ReactFlow
      className={
        showResultHighlight
          ? 'analysis-highlight'
          : ''
      }
      nodes={
        viewMode === 'full'
          ? fullNetworkNodes
          : projectNodes
      }
      edges={
        viewMode === 'full'
          ? highlightedFullNetworkEdges
          : highlightedProjectEdges
      }
      fitView
      fitViewOptions={{
        padding: 0.08,
      }}
    >
      <Background />
      <Controls position="bottom-right" />
    </ReactFlow>
  )
) : (
            <div
              style={{
                height: '100%',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#94a3b8',
                fontSize: '14px',
              }}
            >
              Analyzing semantic change and
              routing attention...
            </div>
          )}
        </main>
      </div>
    </div>
  )
}

export default App