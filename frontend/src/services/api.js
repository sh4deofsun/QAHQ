import axios from 'axios';

const API_URL = 'http://localhost:8000';

const api = axios.create({
    baseURL: API_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Add a request interceptor to add the auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        return Promise.reject(error);
    }
);

export const login = async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    const response = await api.post('/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    return response.data;
};

export const getWorkerStatus = async () => {
    // Using the MCP tool endpoint for now, or we could add a direct endpoint
    // Let's use the MCP tool endpoint as it's what we built
    const response = await api.post('/mcp/tools/get_worker_status');
    return response.data;
};

export const runCommand = async (clientId, command) => {
    const response = await api.post(`/worker/${clientId}/run_command`, { command });
    return response.data;
};

export default api;
