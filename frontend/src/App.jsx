import { useEffect, useMemo, useState, useCallback } from 'react'
import {
  Background,
  Controls,
  MarkerType,
  Position,
  ReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './App.css'
import Network3D from './Network3D'
import mockImpactReport from './mockImpactReport'
import {
  analyzeChange,
  fetchLatestImpact,
  submitReview,
  fetchNotification,
  submitNotificationAnswer,
} from './api'

const DECISION_META = {
  ACTION: {
    label: 'ACTION',
    tone: 'action',
    color: '#fb923c',
  },
  REVIEW_REQUIRED: {
    label: 'REVIEW REQUIRED',
    tone: 'review',
    color: '#ef4444',
  },
  SILENT: {
    label: 'SILENT',
    tone: 'silent',
    color: '#64748b',
  },
}

function formatDeveloperName(id) {
  if (!id) return 'Unknown'

  const names = {
    hilal: 'Hilal',
    batuhan: 'Batuhan',
    ayse: 'Ayşe',
    emre: 'Emre',
    selin: 'Selin',
    mert: 'Mert',
  }

  return (
    names[id] ??
    id
      .split('-')
      .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
      .join(' ')
  )
}

function initials(name) {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

function BrandMark() {
  return (
    <svg className="brand-mark" viewBox="0 0 24 24" aria-hidden="true">
      <rect width="24" height="24" rx="6" fill="currentColor" />
      <circle cx="7" cy="12" r="2.1" fill="#080b10" />
      <circle cx="17" cy="7" r="2.1" fill="#080b10" />
      <circle cx="17" cy="17" r="2.1" fill="#080b10" opacity="0.55" />
      <path d="M9 11 15 7.8M9 13l6 3.2" stroke="#080b10" strokeWidth="1.4" fill="none" />
    </svg>
  )
}

function DecisionBadge({ decision }) {
  const meta = DECISION_META[decision] ?? DECISION_META.SILENT
  return <span className={`decision-badge ${meta.tone}`}>{meta.label}</span>
}

function GraphNodeLabel({ eyebrow, title, tag, tone = 'neutral', muted = false }) {
  return (
    <div className={`graph-node-card ${tone} ${muted ? 'muted' : ''}`}>
      <div className="graph-node-topline">
        <span className="graph-node-dot" />
        <span className="graph-node-eyebrow">{eyebrow}</span>
        {tag && <span className="graph-node-tag">{tag}</span>}
      </div>
      <div className="graph-node-title">{title}</div>
    </div>
  )
}

function RailSection({ title, action, children, compact = false }) {
  return (
    <section className={`rail-section ${compact ? 'compact' : ''}`}>
      <div className="rail-section-head">
        <h3>{title}</h3>
        {action}
      </div>
      {children}
    </section>
  )
}

function RouteCard({ route, onSelect }) {
  const name = formatDeveloperName(route.developer_id)
  const meta = DECISION_META[route.decision] ?? DECISION_META.SILENT

  return (
    <button
      className={`route-card ${meta.tone}`}
      type="button"
      onClick={() => onSelect(route)}
    >
      <span className={`avatar ${meta.tone}`}>{initials(name)}</span>
      <span className="route-card-body">
        <span className="route-card-title-row">
          <strong>{name}</strong>
          <DecisionBadge decision={route.decision} />
        </span>
        <span className="route-card-reason">{route.reason}</span>
        {route.recommended_action && (
          <span className="route-card-action">{route.recommended_action}</span>
        )}
      </span>
      <span className="route-chevron">›</span>
    </button>
  )
}

function App() {
  const [reviewDecision, setReviewDecision] = useState(null)
  const [viewMode, setViewMode] = useState('project')
  const [impactReport, setImpactReport] = useState(null)
  const [dataSource, setDataSource] = useState('mock')
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [hasAnalyzed, setHasAnalyzed] = useState(true)
  const [showResultHighlight, setShowResultHighlight] = useState(false)
  const [selectedDetail, setSelectedDetail] = useState(null)
  const [backendError, setBackendError] = useState(null)

  const routingItems = impactReport?.routing ?? []
  const affectedModules = impactReport?.affected_modules ?? []
  const semanticChange = impactReport?.semantic_change ?? {}

  const actionRoute =
    routingItems.find((item) => item.decision === 'ACTION') ?? null

  const reviewRoute =
    routingItems.find((item) => item.decision === 'REVIEW_REQUIRED') ?? null

  const silentRoutes = routingItems.filter((item) => item.decision === 'SILENT')
  const notificationSilentRoute =
    silentRoutes.find((item) => {
      const text = `${item.developer_id} ${item.reason}`.toLowerCase()
      return text.includes('notification') || item.developer_id === 'ayse'
    }) ??
    silentRoutes[0] ??
    null

  const actionCount = routingItems.filter((item) => item.decision === 'ACTION').length
  const reviewCount = routingItems.filter((item) => item.decision === 'REVIEW_REQUIRED').length
  const silentCount = silentRoutes.length
  const attentionCount = actionCount + reviewCount

  const affectedPrimary =
    affectedModules.find((module) => module.status === 'affected') ?? affectedModules[0]

  useEffect(() => {
    let cancelled = false

    async function loadImpactReport() {
      try {
        const data = await fetchLatestImpact()
        if (!cancelled) {
          setImpactReport(data)
          setDataSource('live')
          setBackendError(null)
        }
        return
      } catch {
        // no cached report yet — try a fresh analysis
      }

      try {
        const data = await analyzeChange()
        if (!cancelled) {
          setImpactReport(data)
          setDataSource('live')
          setBackendError(null)
        }
      } catch {
        if (!cancelled) {
          setBackendError('Live backend is unreachable. No impact report could be loaded.')
        }
      }
    }

    loadImpactReport()

    return () => { cancelled = true }
  }, [])

  async function handleReview(decision) {
    try {
      await submitReview(reviewRoute.developer_id, decision)
    } catch (error) {
      console.warn('Backend unavailable, applying review locally')
    }

    if (decision === 'approve') setReviewDecision('approved')
    if (decision === 'request_changes') setReviewDecision('changes_requested')
  }

  async function handleAnalyze() {
    setIsAnalyzing(true)
    setHasAnalyzed(false)
    setReviewDecision(null)
    setSelectedDetail(null)
    setBackendError(null)

    try {
      const data = await analyzeChange()
      setImpactReport(data)
      setDataSource('live')
    } catch {
      setBackendError('Live backend is unreachable. Analysis could not be completed.')
    } finally {
      setIsAnalyzing(false)
      setHasAnalyzed(true)
      setShowResultHighlight(true)
      setTimeout(() => setShowResultHighlight(false), 1800)
    }
  }

  const projectNodes = useMemo(() => {
    if (!actionRoute || !reviewRoute || !notificationSilentRoute) return []

    const moduleName = affectedPrimary?.module ?? 'affected module'
    const moduleStatus = affectedPrimary?.status ?? 'affected'

    return [
      {
        id: 'project',
        position: { x: 40, y: 215 },
        sourcePosition: Position.Right,
        data: {
          label: (
            <GraphNodeLabel
              eyebrow="CODE CHANGE"
              title={impactReport.commit?.summary ?? 'Semantic code change'}
              tag={(impactReport.commit?.id ?? '').slice(0, 7)}
              tone="change"
            />
          ),
          detail: {
            type: 'Code change',
            title: impactReport.commit?.summary ?? 'Semantic code change',
            status: semanticChange.criticality,
            reason: semanticChange.summary,
            meta: semanticChange.evidence?.[0],
          },
        },
        style: { background: 'transparent', border: 0, padding: 0, width: 210 },
      },
      {
        id: 'billing',
        position: { x: 360, y: 90 },
        sourcePosition: Position.Right,
        targetPosition: Position.Left,
        data: {
          label: (
            <GraphNodeLabel
              eyebrow={moduleStatus === 'affected' ? 'AFFECTED MODULE' : 'MODULE'}
              title={moduleName}
              tag={moduleStatus.toUpperCase()}
              tone={moduleStatus === 'affected' ? 'affected' : 'safe'}
            />
          ),
          detail: {
            type: 'Module',
            title: moduleName,
            status: moduleStatus,
            reason: affectedPrimary?.reason,
            meta: affectedPrimary?.evidence,
          },
        },
        style: { background: 'transparent', border: 0, padding: 0, width: 205 },
      },
      {
        id: 'action-dev',
        position: { x: 700, y: 55 },
        targetPosition: Position.Left,
        data: {
          label: (
            <GraphNodeLabel
              eyebrow={formatDeveloperName(actionRoute.developer_id)}
              title="Needs action"
              tag="ACTION"
              tone="action"
            />
          ),
          detail: {
            type: 'Developer',
            developerId: actionRoute.developer_id,
            title: formatDeveloperName(actionRoute.developer_id),
            status: actionRoute.decision,
            reason: actionRoute.reason,
            recommendedAction: actionRoute.recommended_action,
          },
        },
        style: { background: 'transparent', border: 0, padding: 0, width: 205 },
      },
      {
        id: 'review-dev',
        position: { x: 700, y: 245 },
        targetPosition: Position.Left,
        data: {
          label: (
            <GraphNodeLabel
              eyebrow={formatDeveloperName(reviewRoute.developer_id)}
              title={
                reviewDecision === 'approved'
                  ? 'Review approved'
                  : reviewDecision === 'changes_requested'
                    ? 'Changes requested'
                    : 'Expert review'
              }
              tag={
                reviewDecision === 'approved'
                  ? 'APPROVED'
                  : reviewDecision === 'changes_requested'
                    ? 'CHANGES'
                    : 'REVIEW'
              }
              tone={reviewDecision === 'approved' ? 'safe' : 'review'}
            />
          ),
          detail: {
            type: 'Developer',
            developerId: reviewRoute.developer_id,
            title: formatDeveloperName(reviewRoute.developer_id),
            status: reviewRoute.decision,
            reason: reviewRoute.reason,
            recommendedAction: reviewRoute.recommended_action,
          },
        },
        style: { background: 'transparent', border: 0, padding: 0, width: 205 },
      },
      {
        id: 'silent-dev',
        position: { x: 700, y: 420 },
        targetPosition: Position.Left,
        data: {
          label: (
            <GraphNodeLabel
              eyebrow={formatDeveloperName(notificationSilentRoute.developer_id)}
              title="No action required"
              tag="SILENT"
              tone="silent"
              muted
            />
          ),
          detail: {
            type: 'Developer',
            developerId: notificationSilentRoute.developer_id,
            title: formatDeveloperName(notificationSilentRoute.developer_id),
            status: notificationSilentRoute.decision,
            reason: notificationSilentRoute.reason,
          },
        },
        style: { background: 'transparent', border: 0, padding: 0, width: 205 },
      },
    ]
  }, [
    impactReport,
    semanticChange,
    affectedPrimary,
    actionRoute,
    reviewRoute,
    notificationSilentRoute,
    reviewDecision,
  ])

  const projectEdges = useMemo(() => {
    const base = [
      ['project-billing', 'project', 'billing', '#fb923c'],
      ['billing-action', 'billing', 'action-dev', '#fb923c'],
      ['project-review', 'project', 'review-dev', '#ef4444'],
      ['project-silent', 'project', 'silent-dev', '#475569'],
    ]

    return base.map(([id, source, target, color]) => {
      const quiet = id === 'project-silent'
      const active = showResultHighlight && !quiet
      return {
        id,
        source,
        target,
        type: 'smoothstep',
        animated: active,
        markerEnd: { type: MarkerType.ArrowClosed, color },
        style: {
          stroke: color,
          strokeWidth: active ? 2.6 : quiet ? 1.2 : 1.7,
          opacity: quiet ? 0.28 : showResultHighlight ? 1 : 0.68,
        },
      }
    })
  }, [showResultHighlight])

  const fullNetworkNodes = useMemo(() => {
    const moduleNodes = affectedModules.map((module, index) => ({
      id: `module-${module.module}`,
      position: { x: 390, y: 60 + index * 155 },
      sourcePosition: Position.Right,
      targetPosition: Position.Left,
      data: {
        label: (
          <GraphNodeLabel
            eyebrow="MODULE"
            title={module.module}
            tag={module.status.toUpperCase()}
            tone={module.status === 'affected' ? 'affected' : 'safe'}
          />
        ),
        detail: {
          type: 'Module',
          title: module.module,
          status: module.status,
          reason: module.reason,
          meta: module.evidence,
        },
      },
      style: { background: 'transparent', border: 0, padding: 0, width: 205 },
    }))

    const developerNodes = routingItems.map((route, index) => ({
      id: `developer-${route.developer_id}`,
      position: { x: 785, y: 15 + index * 100 },
      targetPosition: Position.Left,
      data: {
        label: (
          <GraphNodeLabel
            eyebrow={formatDeveloperName(route.developer_id)}
            title={route.decision === 'SILENT' ? 'No action required' : route.decision === 'ACTION' ? 'Needs action' : 'Expert review'}
            tag={DECISION_META[route.decision]?.label ?? route.decision}
            tone={DECISION_META[route.decision]?.tone ?? 'silent'}
            muted={route.decision === 'SILENT'}
          />
        ),
        detail: {
          type: 'Developer',
          developerId: route.developer_id,
          title: formatDeveloperName(route.developer_id),
          status: route.decision,
          reason: route.reason,
          recommendedAction: route.recommended_action,
        },
      },
      style: { background: 'transparent', border: 0, padding: 0, width: 205 },
    }))

    return [
      {
        id: 'project',
        position: { x: 35, y: 235 },
        sourcePosition: Position.Right,
        data: {
          label: (
            <GraphNodeLabel
              eyebrow="CODE CHANGE"
              title={impactReport.commit?.summary ?? 'Semantic change'}
              tag={(impactReport.commit?.id ?? '').slice(0, 7)}
              tone="change"
            />
          ),
          detail: {
            type: 'Code change',
            title: impactReport.commit?.summary,
            status: semanticChange.criticality,
            reason: semanticChange.summary,
            meta: semanticChange.evidence?.[0],
          },
        },
        style: { background: 'transparent', border: 0, padding: 0, width: 210 },
      },
      ...moduleNodes,
      ...developerNodes,
    ]
  }, [affectedModules, routingItems, impactReport, semanticChange])

  const fullNetworkEdges = useMemo(() => {
    const moduleEdges = affectedModules.map((module) => {
      const color = module.status === 'affected' ? '#fb923c' : '#22c55e'
      return {
        id: `project-module-${module.module}`,
        source: 'project',
        target: `module-${module.module}`,
        type: 'smoothstep',
        animated: showResultHighlight && module.status === 'affected',
        markerEnd: { type: MarkerType.ArrowClosed, color },
        style: {
          stroke: color,
          strokeWidth: module.status === 'affected' && showResultHighlight ? 2.6 : 1.35,
          opacity: module.status === 'affected' ? 0.85 : 0.35,
        },
      }
    })

    const developerEdges = routingItems.map((route) => {
      const reason = route.reason?.toLowerCase() ?? ''
      const matchedModule = affectedModules.find((module) =>
        reason.includes(module.module.toLowerCase())
      )
      const meta = DECISION_META[route.decision] ?? DECISION_META.SILENT
      const quiet = route.decision === 'SILENT'

      return {
        id: `route-${route.developer_id}`,
        source: matchedModule ? `module-${matchedModule.module}` : 'project',
        target: `developer-${route.developer_id}`,
        type: 'smoothstep',
        animated: showResultHighlight && !quiet,
        markerEnd: { type: MarkerType.ArrowClosed, color: meta.color },
        style: {
          stroke: meta.color,
          strokeWidth: showResultHighlight && !quiet ? 2.5 : quiet ? 1.1 : 1.65,
          opacity: quiet ? 0.24 : showResultHighlight ? 1 : 0.72,
        },
      }
    })

    return [...moduleEdges, ...developerEdges]
  }, [affectedModules, routingItems, showResultHighlight])

  const currentNodes = viewMode === 'full' ? fullNetworkNodes : projectNodes
  const currentEdges = viewMode === 'full' ? fullNetworkEdges : projectEdges
  const graphTitle = viewMode === 'full' ? 'Full Network' : 'Project Focus'
  const graphSubtitle =
    viewMode === 'full'
      ? 'All modules and developers evaluated'
      : 'Only the attention path that matters'

  function selectRoute(route) {
    setSelectedDetail({
      type: 'Developer',
      title: formatDeveloperName(route.developer_id),
      status: route.decision,
      reason: route.reason,
      recommendedAction: route.recommended_action,
    })
  }

  return (
    <div className="app-shell">
      <header className="top-bar">
        <div className="brand-area">
          <BrandMark />
          <strong className="wordmark">novaHB</strong>
          <span className="brand-divider" />
          <span className="tagline">Route attention, not notifications.</span>
        </div>

        <nav className="view-switch" aria-label="Graph view">
          <button
            type="button"
            className={viewMode === 'project' ? 'active' : ''}
            onClick={() => {
              setViewMode('project')
              setSelectedDetail(null)
            }}
          >
            <span className="nav-icon">◎</span>
            Project Focus
          </button>
          <button
            type="button"
            className={viewMode === 'full' ? 'active' : ''}
            onClick={() => {
              setViewMode('full')
              setSelectedDetail(null)
            }}
          >
            <span className="nav-icon">⌘</span>
            Full Network
          </button>
          <button
            type="button"
            className={viewMode === '3d' ? 'active' : ''}
            onClick={() => {
              setViewMode('3d')
              setSelectedDetail(null)
            }}
          >
            <span className="nav-icon">◇</span>
            3D Network
          </button>
        </nav>

        <div className="top-actions">
          <span className={`source-badge ${dataSource}`}>
            <span className="source-dot" />
            {dataSource === 'live' ? 'LIVE API' : 'MOCK DATA'}
          </span>
          <button
            className="analyze-button"
            type="button"
            onClick={handleAnalyze}
            disabled={isAnalyzing}
          >
            <span className={isAnalyzing ? 'spinner' : 'play-icon'}>{isAnalyzing ? '' : '▶'}</span>
            {isAnalyzing ? 'Analyzing…' : 'Analyze Change'}
          </button>
        </div>
      </header>

      {backendError && (
        <div className="backend-error-banner" role="alert">
          <span className="backend-error-icon">⚠</span>
          <span>{backendError}</span>
          <button type="button" className="backend-error-dismiss" onClick={() => setBackendError(null)} aria-label="Dismiss">×</button>
        </div>
      )}

      <div className="workspace">
        <aside className={`intelligence-rail ${isAnalyzing ? 'dimmed' : ''}`}>
          <RailSection
            title="Change summary"
            action={
              <span className={`criticality ${(semanticChange.criticality ?? 'unknown').toLowerCase()}`}>
                {semanticChange.criticality ?? 'unknown'}
              </span>
            }
          >
            <div className="commit-line">
              <span className="commit-glyph">⌁</span>
              <code>{(impactReport.commit?.id ?? '').slice(0, 8)}</code>
              <span>{impactReport.commit?.summary}</span>
            </div>

            <div className="semantic-box">
              <div className="semantic-file">{semanticChange.evidence?.[0] ?? 'semantic change'}</div>
              <div className="semantic-summary">{semanticChange.summary}</div>
            </div>

            {semanticChange.domains?.length > 0 && (
              <div className="domain-block">
                <span className="rail-label">Affected domains</span>
                <div className="domain-list">
                  {semanticChange.domains.map((domain) => {
                    const module = affectedModules.find((item) => item.module === domain)
                    const tone = module?.status === 'affected' ? 'affected' : module?.status === 'safe' ? 'safe' : 'neutral'
                    return (
                      <span key={domain} className={`domain-pill ${tone}`}>
                        <span className="domain-dot" />
                        {domain}
                      </span>
                    )
                  })}
                </div>
              </div>
            )}

            {semanticChange.broken_contracts?.length > 0 && (
              <div className="broken-contract-box">
                <span className="warning-icon">△</span>
                <div>
                  <strong>Bob semantic insight</strong>
                  {semanticChange.broken_contracts.map((contract, index) => (
                    <p key={`${contract}-${index}`}>{contract}</p>
                  ))}
                </div>
              </div>
            )}
          </RailSection>

          <RailSection
            title="Attention routing"
            action={<span className="section-count">{routingItems.length} evaluated</span>}
          >
            <div className="route-list">
              {actionRoute && <RouteCard route={actionRoute} onSelect={selectRoute} />}
              {reviewRoute && <RouteCard route={reviewRoute} onSelect={selectRoute} />}
            </div>

            <button className="silent-summary" type="button" onClick={() => silentRoutes[0] && selectRoute(silentRoutes[0])}>
              <span className="muted-icon">⌁</span>
              <span>
                <strong>{silentCount} kept silent</strong>
                <small>{silentRoutes.map((route) => formatDeveloperName(route.developer_id)).join(', ')}</small>
              </span>
              <span className="silent-badge">SILENT</span>
            </button>
          </RailSection>

          <RailSection title="Review" compact>
            <p className="review-copy">
              {reviewRoute?.recommended_action ?? 'Review the expert-routed change before merge.'}
            </p>
            <div className="review-actions">
              <button
                type="button"
                className="approve-button"
                disabled={isAnalyzing}
                onClick={() => handleReview('approve')}
              >
                Approve
              </button>
              <button
                type="button"
                className="changes-button"
                disabled={isAnalyzing}
                onClick={() => handleReview('request_changes')}
              >
                Request changes
              </button>
            </div>
            {reviewDecision && (
              <div className={`review-state ${reviewDecision}`}>
                {reviewDecision === 'approved' ? 'Review approved' : 'Changes requested'}
              </div>
            )}
          </RailSection>

          <RailSection title="Analysis impact" compact>
            <div className="impact-grid">
              <div>
                <span>Developers</span>
                <strong>{routingItems.length}</strong>
                <small>evaluated</small>
              </div>
              <div>
                <span>Attention</span>
                <strong className="attention-number">{attentionCount}</strong>
                <small>events</small>
              </div>
              <div>
                <span>Kept silent</span>
                <strong>{silentCount}</strong>
                <small>no action</small>
              </div>
            </div>
            <div className="impact-line">
              {actionCount} ACTION · {reviewCount} REVIEW REQUIRED · {silentCount} SILENT
            </div>
          </RailSection>
        </aside>

        <main className="canvas-column">
          <section className={`graph-shell ${showResultHighlight ? 'analysis-highlight' : ''}`}>
            {viewMode !== '3d' && (
              <div className="graph-toolbar">
                <div className="graph-heading">
                  <strong>{graphTitle}</strong>
                  <span>{graphSubtitle}</span>
                  <code>{currentNodes.length} nodes · {currentEdges.length} edges</code>
                </div>
                <div className="legend">
                  <span><i className="legend-dot action" />Action</span>
                  <span><i className="legend-dot review" />Review required</span>
                  <span><i className="legend-dot silent" />Silent</span>
                  <span><i className="legend-dot affected" />Affected module</span>
                  <span><i className="legend-dot safe" />Safe module</span>
                </div>
              </div>
            )}

            <div className="graph-stage">
              {hasAnalyzed ? (
                viewMode === '3d' ? (
                  <Network3D impactReport={impactReport} />
                ) : (
                  <ReactFlow
                    nodes={currentNodes}
                    edges={currentEdges}
                    fitView
                    minZoom={0.55}
                    maxZoom={1.65}
                    fitViewOptions={{ padding: viewMode === 'full' ? 0.14 : 0.18 }}
                    onNodeClick={(_, node) => setSelectedDetail(node.data?.detail ?? null)}
                    proOptions={{ hideAttribution: true }}
                  >
                    <Background gap={20} size={1} color="#18202b" />
                    <Controls position="bottom-right" showInteractive={false} />
                  </ReactFlow>
                )
              ) : (
                <div className="analysis-state">
                  <span className="analysis-orb" />
                  <strong>Analyzing semantic change</strong>
                  <p>Mapping affected modules and routing only the attention that matters.</p>
                </div>
              )}
            </div>

            {selectedDetail && viewMode !== '3d' && (
              <aside className="node-inspector">
                <button className="inspector-close" type="button" onClick={() => setSelectedDetail(null)} aria-label="Close inspector">×</button>
                <span className="inspector-label">{selectedDetail.type}</span>
                <h4>{selectedDetail.title}</h4>
                {selectedDetail.status && <span className="inspector-status">{selectedDetail.status}</span>}
                {selectedDetail.reason && <p>{selectedDetail.reason}</p>}
                {selectedDetail.meta && <code>{selectedDetail.meta}</code>}
                {selectedDetail.recommendedAction && (
                  <div className="inspector-action">
                    <span>Recommended action</span>
                    <p>{selectedDetail.recommendedAction}</p>
                  </div>
                )}
                {selectedDetail.type === 'Developer' && selectedDetail.developerId && (
                  <NotificationPanel developerId={selectedDetail.developerId} />
                )}
              </aside>
            )}
          </section>
        </main>
      </div>
    </div>
  )
}

function NotificationPanel({ developerId }) {
  const [status, setStatus] = useState('idle') // 'idle' | 'loading' | 'error'
  const [options, setOptions] = useState([])
  const [answers, setAnswers] = useState({}) // { [option_id]: { status, text } }

  useEffect(() => {
    if (!developerId) return
    let cancelled = false
    setStatus('loading')
    setOptions([])
    setAnswers({})

    fetchNotification(developerId)
      .then((data) => {
        if (!cancelled) {
          setOptions(data.options ?? [])
          setStatus('idle')
        }
      })
      .catch(() => {
        if (!cancelled) setStatus('error')
      })

    return () => { cancelled = true }
  }, [developerId])

  const handleSelect = useCallback(async (optionId) => {
    setAnswers((prev) => ({ ...prev, [optionId]: { status: 'loading', text: null } }))
    try {
      const data = await submitNotificationAnswer(developerId, optionId)
      setAnswers((prev) => ({
        ...prev,
        [optionId]: { status: 'done', text: data.answer ?? data.message ?? JSON.stringify(data) },
      }))
    } catch {
      setAnswers((prev) => ({
        ...prev,
        [optionId]: { status: 'error', text: 'Failed to get an answer. Please try again.' },
      }))
    }
  }, [developerId])

  if (status === 'loading') {
    return (
      <div className="notif-panel">
        <div className="notif-spinner" aria-label="Loading notifications…">
          <span className="notif-spinner-dot" />
          <span className="notif-spinner-dot" />
          <span className="notif-spinner-dot" />
        </div>
      </div>
    )
  }

  if (status === 'error') {
    return (
      <div className="notif-panel">
        <p className="notif-error">Failed to load notifications. Please try again.</p>
      </div>
    )
  }

  if (options.length === 0) return null

  return (
    <div className="notif-panel">
      <h4 className="notif-heading">AI Assistant</h4>
      <ul className="notif-list">
        {options.map((opt) => {
          const ans = answers[opt.id]
          return (
            <li key={opt.id} className="notif-item">
              <button
                type="button"
                className={`notif-btn${ans ? ' notif-btn--active' : ''}`}
                onClick={() => handleSelect(opt.id)}
                disabled={ans?.status === 'loading'}
              >
                {opt.label ?? opt.question ?? opt.id}
              </button>
              {ans && (
                <div className={`notif-answer notif-answer--${ans.status}`}>
                  {ans.status === 'loading' && <span className="notif-answer-loading">Thinking…</span>}
                  {ans.status === 'error' && <span>{ans.text}</span>}
                  {ans.status === 'done' && <span>{ans.text}</span>}
                </div>
              )}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export { NotificationPanel }
export default App
