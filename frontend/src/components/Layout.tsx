import { ClipboardList, LayoutDashboard, LogOut, Server, Shield } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'
import { useAuth } from '../auth'

export default function Layout() {
  const { user, logout, hasPerm } = useAuth()
  const showAdmin = hasPerm('user:manage') || hasPerm('role:manage')

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">QAHQ</div>
        <NavLink to="/" end className="nav-link">
          <LayoutDashboard size={17} /> Dashboard
        </NavLink>
        {hasPerm('worker:view') && (
          <NavLink to="/workers" className="nav-link">
            <Server size={17} /> Workers
          </NavLink>
        )}
        {hasPerm('task:view') && (
          <NavLink to="/tasks" className="nav-link">
            <ClipboardList size={17} /> Tasks
          </NavLink>
        )}
        {showAdmin && (
          <NavLink to="/admin" className="nav-link">
            <Shield size={17} /> Admin
          </NavLink>
        )}
        <div className="spacer" />
        <div className="nav-link dim" style={{ cursor: 'default' }}>
          {user?.username}
        </div>
        <button className="nav-link" style={{ background: 'none', border: 'none', cursor: 'pointer', font: 'inherit', textAlign: 'left', width: '100%' }} onClick={logout}>
          <LogOut size={17} /> Logout
        </button>
      </aside>
      <main className="main">
        <Outlet />
      </main>
    </div>
  )
}
