import { useCallback, useEffect, useState } from 'react'
import { api, Task, TestResult, Worker } from '../api'
import { useAuth } from '../auth'
import { useUIEvents } from '../ws'

export default function Dashboard() {
  const { hasPerm } = useAuth()
  const [workers, setWorkers] = useState<Worker[]>([])
  const [tasks, setTasks] = useState<Task[]>([])
  const [results, setResults] = useState<TestResult[]>([])

  const reload = useCallback(() => {
    if (hasPerm('worker:view')) api.workers().then(setWorkers).catch(() => {})
    if (hasPerm('task:view')) api.tasks({ limit: 10 }).then((r) => setTasks(r.tasks)).catch(() => {})
    if (hasPerm('result:view')) api.results().then((r) => setResults(r.results.slice(0, 5))).catch(() => {})
  }, [hasPerm])

  useEffect(reload, [reload])
  useUIEvents(
    useCallback(
      (event) => {
        if (event.event === 'worker_status' || event.event === 'task_update' || event.event === 'result_created') reload()
      },
      [reload],
    ),
  )

  const online = workers.filter((w) => w.status !== 'offline').length
  const running = tasks.filter((t) => t.status === 'running' || t.status === 'assigned').length
  const lastResult = results[0]

  return (
    <div>
      <h2>Dashboard</h2>
      <div className="cards">
        <div className="card">
          <div className="stat-value">{online} / {workers.length}</div>
          <div className="stat-label">Workers online</div>
        </div>
        <div className="card">
          <div className="stat-value">{running}</div>
          <div className="stat-label">Tasks in progress</div>
        </div>
        <div className="card">
          <div className="stat-value">
            {lastResult ? `${lastResult.passed}/${lastResult.total}` : '—'}
          </div>
          <div className="stat-label">Last run passed</div>
        </div>
      </div>

      {hasPerm('worker:view') && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Workers</h3>
          {workers.length === 0 ? (
            <div className="dim">No workers registered.</div>
          ) : (
            <table>
              <thead>
                <tr><th>Client ID</th><th>Status</th><th>Capabilities</th></tr>
              </thead>
              <tbody>
                {workers.map((w) => (
                  <tr key={w.id}>
                    <td>{w.client_id}</td>
                    <td><span className={`badge ${w.status}`}>{w.status}</span></td>
                    <td className="dim">{w.capabilities.join(', ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {hasPerm('result:view') && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Recent test results</h3>
          {results.length === 0 ? (
            <div className="dim">No results yet.</div>
          ) : (
            <table>
              <thead>
                <tr><th>Suite</th><th>Total</th><th>Passed</th><th>Failed</th><th>Skipped</th><th>When</th></tr>
              </thead>
              <tbody>
                {results.map((r) => (
                  <tr key={r.id}>
                    <td>{r.suite_name}</td>
                    <td>{r.total}</td>
                    <td style={{ color: 'var(--success)' }}>{r.passed}</td>
                    <td style={{ color: r.failed ? 'var(--danger)' : undefined }}>{r.failed}</td>
                    <td>{r.skipped}</td>
                    <td className="dim">{new Date(r.created_at + 'Z').toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
