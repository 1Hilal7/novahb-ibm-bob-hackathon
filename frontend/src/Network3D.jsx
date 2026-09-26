import { useMemo, useRef, useState } from 'react'
import ForceGraph3D from 'react-force-graph-3d'
import SpriteText from 'three-spritetext'
import * as THREE from 'three'

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

  return names[id] ?? id.charAt(0).toUpperCase() + id.slice(1)
}

function decisionColor(decision) {
  if (decision === 'ACTION') return '#f59e0b'
  if (decision === 'REVIEW_REQUIRED') return '#ef4444'
  if (decision === 'SILENT') return '#64748b'
  return '#8b5cf6'
}

function moduleColor(status) {
  return status === 'affected' ? '#f97316' : '#22c55e'
}

export default function Network3D({ impactReport }) {
  const graphRef = useRef()
  const [selectedNode, setSelectedNode] = useState(null)

  const graphData = useMemo(() => {
    const affectedModules =
      impactReport?.affected_modules ?? []

    const routing =
      impactReport?.routing ?? []

    const nodes = [
      {
        id: 'project',
        label: 'novaHB Project',
        type: 'project',
        color: '#e2e8f0',
        size: 7,
      },

      ...affectedModules.map((module) => ({
        id: `module-${module.module}`,
        label: `${module.module.toUpperCase()} · ${module.status}`,
        type: 'module',
        module: module.module,
        status: module.status,
        reason: module.reason,
        color: moduleColor(module.status),
        size: module.status === 'affected' ? 6 : 5,
      })),

      ...routing.map((route) => ({
        id: `developer-${route.developer_id}`,
        label: `${formatDeveloperName(
          route.developer_id
        )} · ${route.decision}`,
        type: 'developer',
        developerId: route.developer_id,
        decision: route.decision,
        reason: route.reason,
        recommendedAction:
          route.recommended_action,
        color: decisionColor(route.decision),
        size:
          route.decision === 'SILENT'
            ? 3.5
            : 5.5,
      })),
    ]

    const links = [
      ...affectedModules.map((module) => ({
        source: 'project',
        target: `module-${module.module}`,
        type: 'module',
        color:
          module.status === 'affected'
            ? '#f97316'
            : '#334155',
      })),

      ...routing.map((route) => {
        const reason =
          route.reason?.toLowerCase() ?? ''

        const matchedModule =
          affectedModules.find((module) =>
            reason.includes(
              module.module.toLowerCase()
            )
          )

        return {
          source: matchedModule
            ? `module-${matchedModule.module}`
            : 'project',
          target: `developer-${route.developer_id}`,
          type: 'routing',
          decision: route.decision,
          color: decisionColor(route.decision),
        }
      }),
    ]

    return {
      nodes,
      links,
    }
  }, [impactReport])

  const handleNodeClick = (node) => {
    setSelectedNode(node)

    if (
      !graphRef.current ||
      node.x === undefined ||
      node.y === undefined ||
      node.z === undefined
    ) {
      return
    }

    const distance = 90

    const length =
      Math.hypot(node.x, node.y, node.z) || 1

    const ratio =
      1 + distance / length

    graphRef.current.cameraPosition(
      {
        x: node.x * ratio,
        y: node.y * ratio,
        z: node.z * ratio,
      },
      node,
      900
    )
  }

  return (
    <div
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        background:
          'radial-gradient(circle at center, #111827 0%, #080b12 70%)',
      }}
    >
      <ForceGraph3D
        ref={graphRef}
        graphData={graphData}
        backgroundColor="#080b12"
        showNavInfo={false}
        nodeRelSize={4}
        nodeVal={(node) => node.size}
        nodeColor={(node) => node.color}
        nodeOpacity={0.95}
        linkColor={(link) => link.color}
        linkOpacity={0.55}
        linkWidth={(link) =>
          link.decision === 'ACTION' ||
          link.decision === 'REVIEW_REQUIRED'
            ? 2
            : 1
        }
        linkDirectionalParticles={(link) =>
          link.decision === 'ACTION' ||
          link.decision === 'REVIEW_REQUIRED'
            ? 3
            : 0
        }
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.006}
        onNodeClick={handleNodeClick}
        nodeLabel={(node) => node.label}
        nodeThreeObject={(node) => {
          const group = new THREE.Group()

          const geometry =
            new THREE.SphereGeometry(
              node.size * 0.8,
              18,
              18
            )

          const material =
            new THREE.MeshStandardMaterial({
              color: node.color,
              emissive: node.color,
              emissiveIntensity:
                node.type === 'developer' &&
                node.decision === 'SILENT'
                  ? 0.15
                  : 0.35,
              roughness: 0.5,
              metalness: 0.1,
            })

          const sphere =
            new THREE.Mesh(
              geometry,
              material
            )

          group.add(sphere)

          const label =
            new SpriteText(node.label)

          label.color =
            node.type === 'developer' &&
            node.decision === 'SILENT'
              ? '#94a3b8'
              : '#f8fafc'

          label.textHeight = 4.5
          label.position.set(
            0,
            node.size + 6,
            0
          )

          group.add(label)

          return group
        }}
      />

      <div
        style={{
          position: 'absolute',
          top: '18px',
          left: '18px',
          background: 'rgba(15, 23, 42, 0.88)',
          border: '1px solid #334155',
          borderRadius: '10px',
          padding: '12px 14px',
          color: '#cbd5e1',
          fontSize: '12px',
          backdropFilter: 'blur(12px)',
          pointerEvents: 'none',
        }}
      >
        <div
          style={{
            color: '#f8fafc',
            fontWeight: '700',
            marginBottom: '5px',
          }}
        >
          3D Attention Network
        </div>

        Drag to rotate · Scroll to zoom · Click a node
      </div>

      <div
        style={{
          position: 'absolute',
          bottom: '18px',
          left: '18px',
          display: 'flex',
          gap: '12px',
          flexWrap: 'wrap',
          fontSize: '11px',
          color: '#94a3b8',
          background: 'rgba(15, 23, 42, 0.82)',
          border: '1px solid #334155',
          borderRadius: '9px',
          padding: '9px 12px',
          backdropFilter: 'blur(10px)',
          pointerEvents: 'none',
        }}
      >
        <span>🟠 ACTION</span>
        <span>🔴 REVIEW_REQUIRED</span>
        <span>⚪ SILENT</span>
        <span>🟢 SAFE MODULE</span>
      </div>

      {selectedNode && (
        <div
          style={{
            position: 'absolute',
            top: '18px',
            right: '18px',
            width: '270px',
            background: 'rgba(15, 23, 42, 0.94)',
            border: `1px solid ${
              selectedNode.color ??
              '#334155'
            }`,
            borderRadius: '10px',
            padding: '14px',
            color: '#e2e8f0',
            backdropFilter: 'blur(12px)',
            boxShadow:
              '0 18px 50px rgba(0,0,0,.35)',
          }}
        >
          <div
            style={{
              fontWeight: '800',
              marginBottom: '8px',
              color:
                selectedNode.color ??
                '#f8fafc',
            }}
          >
            {selectedNode.label}
          </div>

          {selectedNode.reason && (
            <div
              style={{
                fontSize: '12px',
                lineHeight: '1.55',
                color: '#cbd5e1',
              }}
            >
              {selectedNode.reason}
            </div>
          )}

          {selectedNode.recommendedAction && (
            <div
              style={{
                marginTop: '10px',
                paddingTop: '10px',
                borderTop:
                  '1px solid #334155',
                fontSize: '12px',
                lineHeight: '1.55',
                color: '#f8fafc',
              }}
            >
              <strong>
                Recommended action
              </strong>

              <div
                style={{
                  marginTop: '4px',
                  color: '#cbd5e1',
                }}
              >
                {
                  selectedNode.recommendedAction
                }
              </div>
            </div>
          )}

          <button
            onClick={() =>
              setSelectedNode(null)
            }
            style={{
              marginTop: '12px',
              width: '100%',
              border: '1px solid #475569',
              background: '#1e293b',
              color: '#cbd5e1',
              borderRadius: '6px',
              padding: '7px',
              cursor: 'pointer',
            }}
          >
            Close
          </button>
        </div>
      )}
    </div>
  )
}