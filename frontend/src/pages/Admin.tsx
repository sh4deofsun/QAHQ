import { Plus, Trash2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import { AdminUser, api, Role } from '../api'
import { useAuth } from '../auth'

export default function Admin() {
  const { hasPerm } = useAuth()
  return (
    <div>
      <h2>Admin</h2>
      {hasPerm('user:manage') && <UsersSection />}
      {hasPerm('role:manage') && <RolesSection />}
    </div>
  )
}

function UsersSection() {
  const [users, setUsers] = useState<AdminUser[]>([])
  const [roles, setRoles] = useState<Role[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [editUser, setEditUser] = useState<AdminUser | null>(null)

  const reload = useCallback(() => {
    api.users().then(setUsers).catch(() => {})
    api.roles().then(setRoles).catch(() => {})
  }, [])
  useEffect(reload, [reload])

  const remove = async (u: AdminUser) => {
    if (!confirm(`Delete user ${u.username}?`)) return
    await api.deleteUser(u.id)
    reload()
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>Users</h3>
        <button className="btn primary sm" onClick={() => setShowCreate(true)}>
          <Plus size={14} /> New user
        </button>
      </div>
      <table style={{ marginTop: '0.75rem' }}>
        <thead>
          <tr><th>Username</th><th>Source</th><th>Active</th><th>Roles</th><th></th></tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td>
              <td className="dim">{u.auth_source}</td>
              <td>{u.is_active ? 'yes' : <span style={{ color: 'var(--danger)' }}>no</span>}</td>
              <td className="dim">{u.roles.join(', ') || '—'}</td>
              <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                <button className="btn sm" onClick={() => setEditUser(u)}>Edit</button>{' '}
                <button className="btn sm danger" onClick={() => remove(u)}><Trash2 size={14} /></button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {showCreate && (
        <UserModal roles={roles} onClose={() => { setShowCreate(false); reload() }} />
      )}
      {editUser && (
        <UserModal user={editUser} roles={roles} onClose={() => { setEditUser(null); reload() }} />
      )}
    </div>
  )
}

function UserModal({ user, roles, onClose }: { user?: AdminUser; roles: Role[]; onClose: () => void }) {
  const [username, setUsername] = useState(user?.username ?? '')
  const [password, setPassword] = useState('')
  const [isActive, setIsActive] = useState(user?.is_active ?? true)
  const [selectedRoles, setSelectedRoles] = useState<string[]>(user?.roles ?? [])
  const [error, setError] = useState('')

  const toggleRole = (name: string) =>
    setSelectedRoles((prev) => (prev.includes(name) ? prev.filter((r) => r !== name) : [...prev, name]))

  const save = async () => {
    setError('')
    try {
      if (user) {
        await api.updateUser(user.id, {
          roles: selectedRoles,
          is_active: isActive,
          ...(password && user.auth_source === 'local' ? { password } : {}),
        })
      } else {
        await api.createUser({ username, password, roles: selectedRoles })
      }
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{user ? `Edit ${user.username}` : 'New local user'}</h3>
        {!user && (
          <div className="field">
            <label>Username</label>
            <input value={username} onChange={(e) => setUsername(e.target.value)} autoFocus />
          </div>
        )}
        {(!user || user.auth_source === 'local') && (
          <div className="field">
            <label>{user ? 'New password (leave blank to keep)' : 'Password'}</label>
            <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} />
          </div>
        )}
        {user && (
          <div className="field">
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <input type="checkbox" style={{ width: 'auto' }} checked={isActive} onChange={(e) => setIsActive(e.target.checked)} />
              Active
            </label>
          </div>
        )}
        <div className="field">
          <label>Roles</label>
          <div className="checkbox-grid">
            {roles.map((r) => (
              <label key={r.id}>
                <input type="checkbox" checked={selectedRoles.includes(r.name)} onChange={() => toggleRole(r.name)} />
                {r.name}
              </label>
            ))}
          </div>
        </div>
        {error && <div className="error">{error}</div>}
        <button className="btn primary" disabled={!user && (!username.trim() || !password)} onClick={save}>
          Save
        </button>
      </div>
    </div>
  )
}

function RolesSection() {
  const [roles, setRoles] = useState<Role[]>([])
  const [allPerms, setAllPerms] = useState<string[]>([])
  const [editRole, setEditRole] = useState<Role | null>(null)
  const [showCreate, setShowCreate] = useState(false)

  const reload = useCallback(() => {
    api.roles().then(setRoles).catch(() => {})
    api.permissions().then(setAllPerms).catch(() => {})
  }, [])
  useEffect(reload, [reload])

  const remove = async (r: Role) => {
    if (!confirm(`Delete role ${r.name}?`)) return
    await api.deleteRole(r.id)
    reload()
  }

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <h3 style={{ margin: 0 }}>Roles</h3>
        <button className="btn primary sm" onClick={() => setShowCreate(true)}>
          <Plus size={14} /> New role
        </button>
      </div>
      <table style={{ marginTop: '0.75rem' }}>
        <thead>
          <tr><th>Name</th><th>Description</th><th>Permissions</th><th></th></tr>
        </thead>
        <tbody>
          {roles.map((r) => (
            <tr key={r.id}>
              <td>{r.name}</td>
              <td className="dim">{r.description}</td>
              <td className="dim mono" style={{ fontSize: '0.78rem' }}>{r.permissions.join(', ')}</td>
              <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                {r.name !== 'admin' && (
                  <>
                    <button className="btn sm" onClick={() => setEditRole(r)}>Edit</button>{' '}
                    <button className="btn sm danger" onClick={() => remove(r)}><Trash2 size={14} /></button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {(showCreate || editRole) && (
        <RoleModal
          role={editRole ?? undefined}
          allPerms={allPerms}
          onClose={() => { setShowCreate(false); setEditRole(null); reload() }}
        />
      )}
    </div>
  )
}

function RoleModal({ role, allPerms, onClose }: { role?: Role; allPerms: string[]; onClose: () => void }) {
  const [name, setName] = useState(role?.name ?? '')
  const [description, setDescription] = useState(role?.description ?? '')
  const [perms, setPerms] = useState<string[]>(role?.permissions ?? [])
  const [error, setError] = useState('')

  const toggle = (p: string) =>
    setPerms((prev) => (prev.includes(p) ? prev.filter((x) => x !== p) : [...prev, p]))

  const save = async () => {
    setError('')
    try {
      if (role) await api.updateRole(role.id, { description, permissions: perms })
      else await api.createRole({ name, description, permissions: perms })
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed')
    }
  }

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <h3>{role ? `Edit role ${role.name}` : 'New role'}</h3>
        {!role && (
          <div className="field">
            <label>Name</label>
            <input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
        )}
        <div className="field">
          <label>Description</label>
          <input value={description} onChange={(e) => setDescription(e.target.value)} />
        </div>
        <div className="field">
          <label>Permissions</label>
          <div className="checkbox-grid">
            {allPerms.map((p) => (
              <label key={p}>
                <input type="checkbox" checked={perms.includes(p)} onChange={() => toggle(p)} />
                <span className="mono">{p}</span>
              </label>
            ))}
          </div>
        </div>
        {error && <div className="error">{error}</div>}
        <button className="btn primary" disabled={!role && !name.trim()} onClick={save}>Save</button>
      </div>
    </div>
  )
}
