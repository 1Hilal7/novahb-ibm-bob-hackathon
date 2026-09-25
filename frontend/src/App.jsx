import { ReactFlow, Background, Controls } from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import './App.css'

const nodes = [
  {
    id: 'project',
    position: { x: 350, y: 150 },
    data: { label: 'novaHB Project' },
  },
  {
    id: 'billing',
    position: { x: 650, y: 150 },
    data: { label: 'Billing Module' },
  },
 {
  id: 'batuhan',
  position: { x: 950, y: 150 },
  data: { label: 'Batuhan — ACTION' },
  style: {
    border: '2px solid #f59e0b',
    background: '#2a1f0f',
    color: '#fbbf24',
    fontWeight: '600',
  },
},
{
  id: 'db-expert',
  position: { x: 950, y: 300 },
  data: { label: 'Database Expert — REVIEW_REQUIRED' },
  style: {
    border: '2px solid #ef4444',
    background: '#2a1111',
    color: '#f87171',
    fontWeight: '600',
  },
},
{
  id: 'notification-dev',
  position: { x: 950, y: 450 },
  data: { label: 'Notification Developer — SILENT' },
  style: {
    border: '2px solid #64748b',
    background: '#111827',
    color: '#94a3b8',
    fontWeight: '600',
    opacity: 0.45,
  },
},

]

const edges = [
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

function App() {
  return (
    <div style={{ width: '100vw', height: '100vh', position: 'relative' }}>
      <div
        style={{
          position: 'absolute',
          top: 20,
          left: 24,
          zIndex: 10,
          color: 'white',
        }}
      >
        <h2 style={{ margin: 0 }}>novaHB</h2>
        <p style={{ margin: '4px 0 0', color: '#94a3b8' }}>
          Route attention, not notifications.
        </p>
      </div>
      <div
  style={{
    position: 'absolute',
    top: 90,
    left: 24,
    zIndex: 10,
    display: 'flex',
    gap: '8px',
  }}
>
  <button
  style={{
    background: '#2563eb',
    color: 'white',
    border: 'none',
    padding: '6px 10px',
    borderRadius: '6px',
    fontWeight: '600',
  }}
>
  Project Focus
</button>

<button
  style={{
    background: '#1f2937',
    color: '#94a3b8',
    border: '1px solid #374151',
    padding: '6px 10px',
    borderRadius: '6px',
  }}
>
  Full Network
</button>

<button
  style={{
    background: '#1f2937',
    color: '#94a3b8',
    border: '1px solid #374151',
    padding: '6px 10px',
    borderRadius: '6px',
  }}
>
  3D
</button>
</div>
      

      <ReactFlow nodes={nodes} edges={edges}>
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  )
}

export default App