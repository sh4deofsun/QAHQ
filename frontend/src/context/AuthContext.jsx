import React, { createContext, useState, useContext, useEffect } from 'react';
import { login as apiLogin } from '../services/api';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const token = localStorage.getItem('token');
        if (token) {
            // Ideally verify token here or decode it
            setUser({ username: 'User' }); // Placeholder
        }
        setLoading(false);
    }, []);

    const login = async (username, password) => {
        try {
            const data = await apiLogin(username, password);
            localStorage.setItem('token', data.access_token);
            setUser({ username });
            return true;
        } catch (error) {
            console.error("Login failed", error);
            return false;
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{ user, login, logout, loading }}>
            {!loading && children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => useContext(AuthContext);
