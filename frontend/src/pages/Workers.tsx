import { KeyRound, Plus, Terminal, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { api, Worker } from '../api'
import { useAuth } from '../auth'
import { useUIEvents } from '../ws'

export default function Workers() {
  const { hasPerm } = useAuth()
  const [workers, setWorkers] = useState<Worker[]>([])
  const [showRegister, setShowRegister] = useState(false)
  const [newClientId, setNewClientId] = useState('')
  const [issuedToken, setIssuedToken] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [commandTarget, setCommandTarget] = useState<Worker | null>(null)

  const reload = useCallback(() => {
    api.workers().then(setWorkers).catch(() => {})
  }, [])
  useEffect(reload, [reload])
  useUIEvents(
    useCallback((e) => { if (e.event === 'worker_status' || e.event === 'task_update') reload() }, [reload]),
  )

  const register = async () => {
    setError('')
    try {
      const res = await api.registerWorker(newClientId.trim())
      setIssuedToken(res.token)
      reload()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    }
  }

  const regenerate = async (w: Worker) => {
    if (!confirm(`Regenerate token for ${w.client_id}? The current token stops working immediately.`)) return
    const res = await api.regenerateToken(w.id)
    setNewClientId(w.client_id)
    setIssuedToken(res.token)
    setShowRegister(true)
  }

  const remove = async (w: Worker) => {
    if (!confirm(`Delete worker ${w.client_id}? Its token is revoked permanently.`)) return
    await api.deleteWorker(w.id)
    reload()
  }

  const closeModal = () => {
    setShowRegister(false)
    setIssuedToken(null)
    setNewClientId('')
    setError('')
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h2>Workers</h2>
        {hasPerm('worker:manage') && (
          <button className="btn primary" onClick={() => setShowRegister(true)}>
            <Plus size={16} /> Register worker
          </button>
        )}
      </div>

      <div className="card">
        {workers.length === 0 ? (
          <div className="dim">No workers registered yet.</div>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Client ID</th><th>Status</th><th>Host</th><th>OS</th><th>Capabilities</th><th>Last heartbeat</th><th></th>
              </tr>
            </thead>
            <tbody>
              {workers.map((w) => (
                <tr key={w.id}>
                  <td>{w.client_id}</td>
                  <td><span className={`badge ${w.status}`}>{w.status}</span></td>
                  <td className="dim">{w.hostname || '—'}</td>
                  <td className="dim">{w.os || '—'}</td>
                  <td className="dim">{w.capabilities.join(', ') || '—'}</td>
                  <td className="dim">{w.last_heartbeat ? new Date(w.last_heartbeat + 'Z').toLocaleString() : '—'}</td>
                  <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                    {hasPerm('task:create_command') && w.status === 'online' && (
                      <button className="btn sm" title="Run command" onClick={() => setCommandTarget(w)}>
                        <Terminal size={14} />
                      </button>
                    )}{' '}
                    {hasPerm('worker:manage') && (
                      <>
                        <button className="btn sm" title="Regenerate token" onClick={() => regenerate(w)}>
                          <KeyRound size={14} />
                        </button>{' '}
                        <button className="btn sm danger" title="Delete" onClick={() => remove(w)}>
                          <Trash2 size={14} />
                        </button>
                      </>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showRegister && (
        <div className="modal-backdrop" onClick={closeModal}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>{issuedToken ? 'Worker token' : 'Register worker'}</h3>
            {issuedToken ? (
              <>
                <p className="dim">
                  Copy this token now — it is shown only once and stored hashed.
                </p>
                <div className="token-reveal">{issuedToken}</div>
                <p className="dim mono">
                  QAHQ_URL=wss://&lt;hq-host&gt; QAHQ_CLIENT_ID={newClientId} QAHQ_TOKEN=&lt;token&gt; qahq-worker
                </p>
                <button className="btn primary" onClick={closeModal}>Done</button>
              </>
            ) : (
              <>
                <div className="field">
                  <label>Client ID</label>
                  <input value={newClientId} onChange={(e) => setNewClientId(e.target.value)} placeholder="e.g. qa-runner-01" autoFocus />
                </div>
                {error && <div className="error">{error}</div>}
                <button className="btn primary" disabled={!newClientId.trim()} onClick={register}>Create</button>
              </>
            )}
          </div>
        </div>
      )}

      {commandTarget && <CommandPanel worker={commandTarget} onClose={() => setCommandTarget(null)} />}
    </div>
  )
}

function CommandPanel({ worker, onClose }: { worker: Worker; onClose: () => void }) {
  const [command, setCommand] = useState('')
  const [taskId, setTaskId] = useState<number | null>(null)
  const [output, setOutput] = useState('')
  const [status, setStatus] = useState('')
  const terminalRef = useRef<HTMLDivElement>(null)

  useUIEvents(
    useCallback(
      (e) => {
        if (e.event === 'task_output' && e.task_id === taskId) {
          setOutput((prev) => prev + e.data)
        } else if (e.event === 'task_update' && e.task.id === taskId) {
          setStatus(e.task.status)
        }
      },
      [taskId],
    ),
  )

  useEffect(() => {
    terminalRef.current?.scrollTo(0, terminalRef.current.scrollHeight)
  }, [output])

  const run = async () => {
    setOutput('')
    setStatus('')
    const task = await api.createTask({ type: 'run_command', command, worker_id: worker.id })
    setTaskId(task.id)
    setStatus(task.status)
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" style={{ width: 'min(720px, 92vw)' }} onClick={(e) => e.stopPropagation()}>
        <h3>Run command on {worker.client_id}</h3>
        <div className="row">
          <div className="field">
            <input
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && command.trim() && run()}
              placeholder="e.g. robot --version"
              className="mono"
              autoFocus
            />
          </div>
          <button className="btn primary" disabled={!command.trim()} onClick={run}>Run</button>
        </div>
        {taskId && (
          <>
            <p className="dim" style={{ marginBottom: '0.4rem' }}>
              Task #{taskId} {status && <span className={`badge ${status}`}>{status}</span>}
            </p>
            <div className="terminal" ref={terminalRef}>{output || '…'}</div>
          </>
        )}
      </div>
    </div>
  )
}
