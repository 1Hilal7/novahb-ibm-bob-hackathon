import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

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

  return (
    names[id] ??
    id.charAt(0).toUpperCase() +
      id.slice(1)
  )
}

function decisionColor(decision) {
  if (decision === 'ACTION') {
    return '#fb923c'
  }

  if (decision === 'REVIEW_REQUIRED') {
    return '#ef4444'
  }

  if (decision === 'SILENT') {
    return '#64748b'
  }

  return '#7c6cff'
}

function moduleColor(status) {
  return status === 'affected'
    ? '#f97316'
    : '#39c982'
}

function isPriorityNode(node) {
  if (node.type === 'project') {
    return true
  }

  if (node.type === 'module') {
    return true
  }

  return (
    node.decision === 'ACTION' ||
    node.decision === 'REVIEW_REQUIRED'
  )
}

export default function Network3D({
  impactReport,
}) {
  const graphRef = useRef(null)
  const containerRef = useRef(null)

  const [selectedNode, setSelectedNode] =
    useState(null)

  const [hoveredNode, setHoveredNode] =
    useState(null)

  const [size, setSize] = useState({
    width: 900,
    height: 620,
  })

  useEffect(() => {
    if (!containerRef.current) {
      return
    }

    const observer = new ResizeObserver(
      ([entry]) => {
        const { width, height } =
          entry.contentRect

        if (width > 0 && height > 0) {
          setSize({
            width,
            height,
          })
        }
      }
    )

    observer.observe(
      containerRef.current
    )

    return () => {
      observer.disconnect()
    }
  }, [])

  const graphData = useMemo(() => {
    const affectedModules =
      impactReport?.affected_modules ?? []

    const routing =
      impactReport?.routing ?? []

    /*
      Gerçek 3D düzen:

      x:
        -150 = code change
           0 = modules
         150 = developers

      y:
        dikey ayrım

      z:
        derinlik

      Böylece ağ yalnızca "düz bir flowchart"
      gibi görünmiyor.
    */

    const modulePositions = [
      {
        y: -78,
        z: 58,
      },
      {
        y: 0,
        z: -58,
      },
      {
        y: 78,
        z: 42,
      },
      {
        y: -32,
        z: -90,
      },
    ]

    const developerDepths = [
      78,
      -76,
      34,
      -28,
      98,
      -104,
      55,
      -52,
    ]

    const nodes = [
      {
        id: 'project',

        label: 'CODE CHANGE',

        subtitle:
          impactReport?.commit?.summary ??
          'Semantic change',

        type: 'project',

        color: '#7c6cff',

        size: 6.8,

        fx: -150,
        fy: 0,
        fz: 0,
      },

      ...affectedModules.map(
        (module, index) => {
          const position =
            modulePositions[
              index %
                modulePositions.length
            ]

          return {
            id: `module-${module.module}`,

            label:
              module.module.toUpperCase(),

            subtitle:
              module.status.toUpperCase(),

            type: 'module',

            module: module.module,

            status: module.status,

            reason: module.reason,

            evidence: module.evidence,

            color: moduleColor(
              module.status
            ),

            size:
              module.status ===
              'affected'
                ? 5.8
                : 4.8,

            fx: 0,

            fy: position.y,

            fz: position.z,
          }
        }
      ),

      ...routing.map(
        (route, index) => {
          const reason =
            route.reason?.toLowerCase() ??
            ''

          const matchedModuleIndex =
            affectedModules.findIndex(
              (module) =>
                reason.includes(
                  module.module.toLowerCase()
                )
            )

          const fallbackIndex =
            index %
            Math.max(
              affectedModules.length,
              1
            )

          const moduleIndex =
            matchedModuleIndex >= 0
              ? matchedModuleIndex
              : fallbackIndex

          const modulePosition =
            modulePositions[
              moduleIndex %
                modulePositions.length
            ]

          const localYOffset =
            (index % 3 - 1) * 30

          const depthOffset =
            developerDepths[
              index %
                developerDepths.length
            ]

          return {
            id: `developer-${route.developer_id}`,

            label: formatDeveloperName(
              route.developer_id
            ),

            subtitle: route.decision,

            type: 'developer',

            developerId:
              route.developer_id,

            decision: route.decision,

            reason: route.reason,

            recommendedAction:
              route.recommended_action,

            color: decisionColor(
              route.decision
            ),

            size:
              route.decision === 'SILENT'
                ? 2.8
                : 5,

            fx: 150,

            fy:
              modulePosition.y +
              localYOffset,

            fz:
              modulePosition.z +
              depthOffset,
          }
        }
      ),
    ]

    const links = [
      ...affectedModules.map(
        (module) => ({
          source: 'project',

          target: `module-${module.module}`,

          type: 'module',

          status: module.status,

          color:
            module.status ===
            'affected'
              ? '#f97316'
              : '#285846',
        })
      ),

      ...routing.map((route) => {
        const reason =
          route.reason?.toLowerCase() ??
          ''

        const matchedModule =
          affectedModules.find(
            (module) =>
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

          color: decisionColor(
            route.decision
          ),
        }
      }),
    ]

    return {
      nodes,
      links,
    }
  }, [impactReport])

  function resetCamera(duration = 900) {
    const graph = graphRef.current

    if (!graph) {
      return
    }

     graph.cameraPosition(
    {
      x: 330,
      y: 190,
      z: 430,
    },
    {
      x: 0,
      y: 0,
      z: 0,
    },
    duration
  )

  setTimeout(() => {
    graph.zoomToFit(500, 85)
  }, duration + 80)
}

  useEffect(() => {
  const timer = setTimeout(() => {
    resetCamera(650)
  }, 300)

  return () => clearTimeout(timer)
}, [graphData, size.width, size.height])

  function handleNodeClick(node) {
    setSelectedNode(node)

    const graph = graphRef.current

    if (
      !graph ||
      node.x === undefined ||
      node.y === undefined ||
      node.z === undefined
    ) {
      return
    }

    /*
      Node'a yaklaşır ama düz karşıdan
      bakmaz.

      Sağ + üst + önden offset vererek
      3D açıyı koruyoruz.
    */

    graph.cameraPosition(
      {
        x: node.x + 130,
        y: node.y + 85,
        z: node.z + 185,
      },
      {
        x: node.x,
        y: node.y,
        z: node.z,
      },
      700
    )
  }

  function createNodeObject(node) {
    const group =
      new THREE.Group()

    const isSilent =
      node.type === 'developer' &&
      node.decision === 'SILENT'

    const isImportant =
      isPriorityNode(node)

    const isHovered =
      hoveredNode?.id === node.id

    const isSelected =
      selectedNode?.id === node.id

    const sphereGeometry =
      new THREE.SphereGeometry(
        node.size * 0.72,
        24,
        24
      )

    const sphereMaterial =
      new THREE.MeshStandardMaterial({
        color: node.color,

        emissive: node.color,

        emissiveIntensity: isSilent
          ? isHovered || isSelected
            ? 0.16
            : 0.04
          : isSelected
          ? 0.6
          : 0.28,

        roughness: 0.38,

        metalness: 0.1,

        transparent: true,

        opacity: isSilent
          ? isHovered || isSelected
            ? 0.85
            : 0.32
          : 0.98,
      })

    const sphere =
      new THREE.Mesh(
        sphereGeometry,
        sphereMaterial
      )

    group.add(sphere)

    /*
      Priority node'larda hafif outer glow.
    */

    if (
      !isSilent &&
      node.type !== 'project'
    ) {
      const glowGeometry =
        new THREE.SphereGeometry(
          node.size * 0.9,
          20,
          20
        )

      const glowMaterial =
        new THREE.MeshBasicMaterial({
          color: node.color,
          transparent: true,
          opacity: isSelected
            ? 0.15
            : 0.055,
          side: THREE.BackSide,
        })

      const glow = new THREE.Mesh(
        glowGeometry,
        glowMaterial
      )

      group.add(glow)
    }

    /*
      Selected node halkası.
    */

    if (isSelected) {
      const ringGeometry =
        new THREE.RingGeometry(
          node.size * 1.02,
          node.size * 1.25,
          40
        )

      const ringMaterial =
        new THREE.MeshBasicMaterial({
          color: node.color,
          transparent: true,
          opacity: 0.72,
          side: THREE.DoubleSide,
        })

      const ring = new THREE.Mesh(
        ringGeometry,
        ringMaterial
      )

      ring.rotation.x =
        Math.PI / 2

      group.add(ring)
    }

    /*
      Silent developer label'larını sürekli
      göstermiyoruz.

      Böylece network kirlenmiyor.
    */

    const shouldShowLabel =
      isImportant ||
      isHovered ||
      isSelected

    if (shouldShowLabel) {
      const label =
        new SpriteText(
          node.label
        )

      label.color = isSilent
        ? '#8b96a8'
        : '#f3f6fb'

      label.textHeight =
        node.type === 'project'
          ? 4
          : isSilent
          ? 2.5
          : 3.2

      label.fontWeight = 600

      label.position.set(
        0,
        node.size + 5.5,
        0
      )

      group.add(label)
    }

    /*
      Status subtitle.
    */

    const shouldShowSubtitle =
      !isSilent &&
      (isImportant ||
        isHovered ||
        isSelected)

    if (
      shouldShowSubtitle &&
      node.subtitle
    ) {
      const subtitle =
        new SpriteText(
          node.subtitle
        )

      subtitle.color =
        node.color

      subtitle.textHeight = 1.8

      subtitle.position.set(
        0,
        node.size + 2,
        0
      )

      group.add(subtitle)
    }

    return group
  }

  return (
    <div
      ref={containerRef}
      className="network3d-root"
      style={{
        width: '100%',
        height: '100%',
        position: 'relative',
        overflow: 'hidden',
        background:
          'radial-gradient(circle at 45% 45%, #101722 0%, #080c11 55%, #06090d 100%)',
      }}
    >
      <div className="network3d-toolbar">
        <div>
          <strong>
            3D Network
          </strong>

          <span>
            Spatial attention map
          </span>

          <code>
            {graphData.nodes.length}{' '}
            nodes ·{' '}
            {graphData.links.length}{' '}
            edges
          </code>
        </div>

        <div className="network3d-legend">
          <span>
            <i className="legend-dot action" />
            Action
          </span>

          <span>
            <i className="legend-dot review" />
            Review required
          </span>

          <span>
            <i className="legend-dot silent" />
            Silent
          </span>

          <span>
            <i className="legend-dot safe" />
            Safe module
          </span>
        </div>
      </div>

      <div
        className="network3d-canvas"
        style={{
          width: '100%',
          height: '100%',
        }}
      >
        <ForceGraph3D
          ref={graphRef}

          width={size.width}

          height={Math.max(
            260,
            size.height - 42
          )}

          graphData={graphData}

          backgroundColor="#080c11"

          showNavInfo={false}

          cooldownTicks={0}

          enableNodeDrag={false}

          nodeRelSize={4}

          nodeVal={(node) =>
            node.size
          }

          nodeColor={(node) =>
            node.color
          }

          nodeOpacity={0.96}

          linkColor={(link) =>
            link.color
          }

          linkOpacity={(link) => {
            if (
              link.decision ===
              'SILENT'
            ) {
              return 0.1
            }

            if (
              link.status === 'safe'
            ) {
              return 0.22
            }

            return 0.58
          }}

          linkWidth={(link) => {
            if (
              link.decision ===
                'ACTION' ||
              link.decision ===
                'REVIEW_REQUIRED'
            ) {
              return 2.2
            }

            if (
              link.status ===
              'affected'
            ) {
              return 1.6
            }

            return 0.7
          }}

          linkDirectionalParticles={(
            link
          ) => {
            if (
              link.decision ===
                'ACTION' ||
              link.decision ===
                'REVIEW_REQUIRED'
            ) {
              return 4
            }

            if (
              link.status ===
              'affected'
            ) {
              return 2
            }

            return 0
          }}

          linkDirectionalParticleWidth={
            1.8
          }

          linkDirectionalParticleSpeed={
            0.0055
          }

          onNodeClick={
            handleNodeClick
          }

          onNodeHover={(node) => {
            setHoveredNode(
              node ?? null
            )

            if (
              containerRef.current
            ) {
              containerRef.current.style.cursor =
                node
                  ? 'pointer'
                  : 'default'
            }
          }}

          nodeLabel={() => ''}

          nodeThreeObject={
            createNodeObject
          }
        />
      </div>

      <div
        className="network3d-hint"
      >
        Drag to rotate · Scroll to
        zoom · Click a node
      </div>

      <button
        type="button"
        onClick={() =>
          resetCamera(650)
        }
        style={{
          position: 'absolute',
          right: '18px',
          bottom: '18px',
          height: '34px',
          padding: '0 13px',
          borderRadius: '7px',
          border:
            '1px solid #2a3545',
          background:
            'rgba(12, 18, 27, 0.9)',
          color: '#aeb9c8',
          fontSize: '11px',
          fontWeight: 600,
          cursor: 'pointer',
          backdropFilter:
            'blur(10px)',
          zIndex: 8,
        }}
      >
        Reset view
      </button>

      {selectedNode && (
        <aside className="network3d-inspector">
          <button
            type="button"
            onClick={() =>
              setSelectedNode(null)
            }
            aria-label="Close"
          >
            ×
          </button>

          <span>
            {selectedNode.type ===
            'developer'
              ? 'Developer'
              : selectedNode.type ===
                'module'
              ? 'Module'
              : 'Code change'}
          </span>

          <h4>
            {selectedNode.label}
          </h4>

          {selectedNode.subtitle && (
            <code>
              {selectedNode.subtitle}
            </code>
          )}

          {selectedNode.reason && (
            <p>
              {selectedNode.reason}
            </p>
          )}

          {selectedNode.evidence && (
            <small>
              {
                selectedNode.evidence
              }
            </small>
          )}

          {selectedNode.recommendedAction && (
            <div>
              <strong>
                Recommended action
              </strong>

              <p>
                {
                  selectedNode.recommendedAction
                }
              </p>
            </div>
          )}
        </aside>
      )}
    </div>
  )
}