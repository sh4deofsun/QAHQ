import React from 'react';
import { Outlet, Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { LayoutDashboard, Users, LogOut } from 'lucide-react';

const Layout = () => {
    const { logout, user } = useAuth();
    const navigate = useNavigate();

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    return (
        <div style={{ display: 'flex', minHeight: '100vh' }}>
            {/* Sidebar */}
            <aside style={{ width: '250px', backgroundColor: 'var(--bg-secondary)', borderRight: '1px solid var(--border)', padding: '1.5rem' }}>
                <h1 style={{ fontSize: '1.5rem', fontWeight: 'bold', marginBottom: '2rem', color: 'var(--accent)' }}>QAHQ</h1>
                <nav style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <Link to="/" className="btn" style={{ justifyContent: 'flex-start', backgroundColor: 'transparent', color: 'var(--text-primary)' }}>
                        <LayoutDashboard size={18} style={{ marginRight: '0.75rem' }} /> Dashboard
                    </Link>
                    <Link to="/workers" className="btn" style={{ justifyContent: 'flex-start', backgroundColor: 'transparent', color: 'var(--text-primary)' }}>
                        <Users size={18} style={{ marginRight: '0.75rem' }} /> Workers
                    </Link>
                </nav>
                <div style={{ marginTop: 'auto', paddingTop: '2rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem', padding: '0.5rem' }}>
                        <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                            {user?.username?.[0]?.toUpperCase()}
                        </div>
                        <span>{user?.username}</span>
                    </div>
                    <button onClick={handleLogout} className="btn" style={{ width: '100%', justifyContent: 'flex-start', color: 'var(--text-secondary)' }}>
                        <LogOut size={18} style={{ marginRight: '0.75rem' }} /> Logout
                    </button>
                </div>
            </aside>

            {/* Main Content */}
            <main style={{ flex: 1, padding: '2rem', overflowY: 'auto' }}>
                <Outlet />
            </main>
        </div>
    );
};

export default Layout;
