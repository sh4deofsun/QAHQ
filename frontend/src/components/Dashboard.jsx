import React, { useEffect, useState } from 'react';
import { getWorkerStatus, runCommand } from '../services/api';
import { Server, Terminal, Activity } from 'lucide-react';

const Dashboard = () => {
    const [workers, setWorkers] = useState([]);
    const [loading, setLoading] = useState(true);

    const fetchWorkers = async () => {
        try {
            const data = await getWorkerStatus();
            setWorkers(data.workers || []);
        } catch (error) {
            console.error("Failed to fetch workers", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchWorkers();
        const interval = setInterval(fetchWorkers, 5000); // Poll every 5s
        return () => clearInterval(interval);
    }, []);

    const handleRunCommand = async (clientId) => {
        const cmd = prompt("Enter command to run:");
        if (cmd) {
            try {
                await runCommand(clientId, cmd);
                alert("Command sent!");
            } catch (error) {
                alert("Failed to send command");
            }
        }
    };

    return (
        <div>
            <h2 style={{ marginBottom: '1.5rem' }}>Dashboard</h2>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
                <div className="card">
                    <div className="flex items-center gap-4">
                        <div style={{ padding: '1rem', borderRadius: '50%', backgroundColor: 'rgba(59, 130, 246, 0.1)', color: 'var(--accent)' }}>
                            <Server size={24} />
                        </div>
                        <div>
                            <div className="text-sm text-gray">Active Workers</div>
                            <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{workers.length}</div>
                        </div>
                    </div>
                </div>
                {/* Add more widgets here */}
            </div>

            <h3 style={{ marginBottom: '1rem' }}>Connected Workers</h3>
            <div style={{ display: 'grid', gap: '1rem' }}>
                {workers.length === 0 ? (
                    <div className="card" style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>No workers connected</div>
                ) : (
                    workers.map((worker) => (
                        <div key={worker.client_id} className="card flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <Activity size={20} color="var(--success)" />
                                <div>
                                    <div style={{ fontWeight: '500' }}>{worker.client_id}</div>
                                    <div className="text-sm text-gray">Capabilities: {worker.capabilities.join(', ')}</div>
                                </div>
                            </div>
                            <button className="btn btn-primary" onClick={() => handleRunCommand(worker.client_id)}>
                                <Terminal size={16} style={{ marginRight: '0.5rem' }} /> Run Command
                            </button>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default Dashboard;
