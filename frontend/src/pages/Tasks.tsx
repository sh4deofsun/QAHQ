import { Play, XCircle } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { api, artifactUrl, Task, TestResult, Worker } from '../api'
import { useAuth } from '../auth'
import { useUIEvents } from '../ws'

export default function Tasks() {
  const { hasPerm } = useAuth()
  const [tasks, setTasks] = useState<Task[]>([])
  const [results, setResults] = useState<TestResult[]>([])
  const [selected, setSelected] = useState<Task | null>(null)

  const reload = useCallback(() => {
    api.tasks({ limit: 50 }).then((r) => setTasks(r.tasks)).catch(() => {})
    if (hasPerm('result:view')) api.results().then((r) => setResults(r.results)).catch(() => {})
  }, [hasPerm])

  useEffect(reload, [reload])
  useUIEvents(
    useCallback(
      (e) => {
        if (e.event === 'task_update' || e.event === 'result_created') reload()
      },
      [reload],
    ),
  )

  const cancel = async (task: Task) => {
    if (!confirm(`Cancel task #${task.id}?`)) return
    await api.cancelTask(task.id)
    reload()
  }

  return (
    <div>
      <h2>Tasks</h2>

      {hasPerm('task:create_robot') && <RobotRunForm onCreated={reload} />}

      <div className="card">
        <h3 style={{ marginTop: 0 }}>History</h3>
        {tasks.length === 0 ? (
          <div className="dim">No tasks yet.</div>
        ) : (
          <table>
            <thead>
              <tr><th>#</th><th>Type</th><th>Status</th><th>Worker</th><th>Created</th><th>Exit</th><th></th></tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <tr key={t.id} className="clickable" onClick={() => api.task(t.id).then(setSelected)}>
                  <td>{t.id}</td>
                  <td className="mono">{t.type}</td>
                  <td><span className={`badge ${t.status}`}>{t.status}</span></td>
                  <td className="dim">{t.worker_client_id ?? '—'}</td>
                  <td className="dim">{new Date(t.created_at + 'Z').toLocaleString()}</td>
                  <td className="dim">{t.returncode ?? '—'}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    {['pending', 'assigned', 'running'].includes(t.status) && (
                      <button className="btn sm danger" onClick={() => cancel(t)}>
                        <XCircle size={14} /> Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {hasPerm('result:view') && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Test results</h3>
          {results.length === 0 ? (
            <div className="dim">No results yet.</div>
          ) : (
            <table>
              <thead>
                <tr><th>Suite</th><th>Task</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>Reports</th><th>When</th></tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.id}>
                    <td>{r.suite_name}</td>
                    <td className="dim">{r.task_id ? `#${r.task_id}` : 'upload'}</td>
                    <td>{r.total}</td>
                    <td style={{ color: 'var(--success)' }}>{r.passed}</td>
                    <td style={{ color: r.failed ? 'var(--danger)' : undefined }}>{r.failed}</td>
                    <td>{r.skipped}</td>
                    <td>
                      {r.has_artifacts ? <ArtifactLinks result={r} /> : <span className="dim">—</span>}
                    </td>
                    <td className="dim">{new Date(r.created_at + 'Z').toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {selected && <TaskDetail task={selected} onClose={() => setSelected(null)} />}
    </div>
  )
}

function RobotRunForm({ onCreated }: { onCreated: () => void }) {
  const [workers, setWorkers] = useState<Worker[]>([])
  const [sourceMode, setSourceMode] = useState<'git' | 'path'>('git')
  const [gitUrl, setGitUrl] = useState('')
  const [gitRef, setGitRef] = useState('')
  const [path, setPath] = useState('')
  const [includeTags, setIncludeTags] = useState('')
  const [excludeTags, setExcludeTags] = useState('')
  const [workerId, setWorkerId] = useState<string>('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.workers().then(setWorkers).catch(() => {})
  }, [])

  const submit = async () => {
    setBusy(true)
    setError('')
    try {
      await api.createTask({
        type: 'robot_run',
        worker_id: workerId ? Number(workerId) : null,
        source: {
          git_url: sourceMode === 'git' ? gitUrl : '',
          git_ref: sourceMode === 'git' ? gitRef : '',
          path,
        },
        options: {
          include_tags: includeTags.split(',').map((s) => s.trim()).filter(Boolean),
          exclude_tags: excludeTags.split(',').map((s) => s.trim()).filter(Boolean),
          variables: {},
        },
      })
      onCreated()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    } finally {
      setBusy(false)
    }
  }

  const valid = sourceMode === 'git' ? gitUrl.trim() : path.trim()

  return (
    <div className="card">
      <h3 style={{ marginTop: 0 }}>Run robot suite</h3>
      <div className="row" style={{ marginBottom: '0.85rem' }}>
        <div className="field" style={{ flex: '0 0 140px' }}>
          <label>Source</label>
          <select value={sourceMode} onChange={(e) => setSourceMode(e.target.value as 'git' | 'path')}>
            <option value="git">Git repository</option>
            <option value="path">Path on worker</option>
          </select>
        </div>
        {sourceMode === 'git' && (
          <>
            <div className="field" style={{ flex: 2 }}>
              <label>Git URL</label>
              <input value={gitUrl} onChange={(e) => setGitUrl(e.target.value)} placeholder="https://git.example.com/qa/tests.git" />
            </div>
            <div className="field" style={{ flex: '0 0 120px' }}>
              <label>Branch / ref</label>
              <input value={gitRef} onChange={(e) => setGitRef(e.target.value)} placeholder="main" />
            </div>
          </>
        )}
        <div className="field" style={{ flex: 1 }}>
          <label>{sourceMode === 'git' ? 'Suite path in repo' : 'Suite path on worker'}</label>
          <input value={path} onChange={(e) => setPath(e.target.value)} placeholder={sourceMode === 'git' ? 'suites/smoke' : '/opt/qa/suites'} />
        </div>
      </div>
      <div className="row" style={{ marginBottom: '0.85rem' }}>
        <div className="field">
          <label>Include tags (comma-separated)</label>
          <input value={includeTags} onChange={(e) => setIncludeTags(e.target.value)} placeholder="smoke" />
        </div>
        <div className="field">
          <label>Exclude tags</label>
          <input value={excludeTags} onChange={(e) => setExcludeTags(e.target.value)} placeholder="wip" />
        </div>
        <div className="field">
          <label>Worker</label>
          <select value={workerId} onChange={(e) => setWorkerId(e.target.value)}>
            <option value="">Auto (any capable worker)</option>
            {workers.map((w) => (
              <option key={w.id} value={w.id}>
                {w.client_id} ({w.status})
              </option>
            ))}
          </select>
        </div>
        <button className="btn primary" disabled={!valid || busy} onClick={submit}>
          <Play size={16} /> Run
        </button>
      </div>
      {error && <div className="error">{error}</div>}
    </div>
  )
}

function ArtifactLinks({ result }: { result: TestResult }) {
  const [files, setFiles] = useState<string[]>([])
  useEffect(() => {
    api.artifacts(result.id).then((r) => setFiles(r.artifacts)).catch(() => {})
  }, [result.id])
  // fetch with auth header, then open — artifact endpoints require a bearer token
  const open = async (name: string) => {
    const res = await fetch(artifactUrl(result.id, name), {
      headers: { Authorization: `Bearer ${localStorage.getItem('qahq_token')}` },
    })
    const blob = await res.blob()
    window.open(URL.createObjectURL(blob), '_blank')
  }
  return (
    <span>
      {files.map((f) => (
        <button key={f} className="btn sm" style={{ marginRight: 4 }} onClick={() => open(f)}>
          {f.replace('.html', '').replace('.xml', '')}
        </button>
      ))}
    </span>
  )
}

function TaskDetail({ task, onClose }: { task: Task; onClose: () => void }) {
  const [output, setOutput] = useState(task.output ?? '')
  const [status, setStatus] = useState(task.status)

  useUIEvents(
    useCallback(
      (e) => {
        if (e.event === 'task_output' && e.task_id === task.id) setOutput((prev) => prev + e.data)
        if (e.event === 'task_update' && e.task.id === task.id) setStatus(e.task.status as Task['status'])
      },
      [task.id],
    ),
  )

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" style={{ width: 'min(760px, 92vw)' }} onClick={(e) => e.stopPropagation()}>
        <h3>
          Task #{task.id} <span className={`badge ${status}`}>{status}</span>
        </h3>
        <p className="dim mono" style={{ wordBreak: 'break-all' }}>{JSON.stringify(task.payload)}</p>
        {task.error && <div className="error">{task.error}</div>}
        <div className="terminal">{output || '(no output)'}</div>
      </div>
    </div>
  )
}
