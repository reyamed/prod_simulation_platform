import React, { useState, useEffect } from 'react';

const TicketItem = ({ ticket, handleValidate }) => {
    const [hintIndex, setHintIndex] = useState(0);

    let hints = [];
    try {
        if (ticket.hints && ticket.hints !== "[]") {
            hints = JSON.parse(ticket.hints);
        }
    } catch (e) {
        console.error("Error parsing hints:", e);
    }

    const handleRevealHint = () => {
        if (hintIndex < hints.length) {
            setHintIndex(hintIndex + 1);
        }
    };

    return (
        <div style={{
            border: '1px solid #ddd',
            borderLeft: '5px solid #d93f3c',
            borderRadius: '8px',
            padding: '1.5rem',
            marginBottom: '1rem',
            backgroundColor: 'white',
            boxShadow: '0 4px 6px rgba(0,0,0,0.05)'
        }}>
            <h3 style={{ marginTop: 0 }}>{ticket.subject}</h3>
            <p><strong>From:</strong> {ticket.sender_name}</p>
            <p style={{ fontStyle: 'italic', backgroundColor: '#f9f9f9', padding: '1rem', borderRadius: '4px', border: '1px solid #eee' }}>
                "{ticket.body}"
            </p>

            <div style={{ marginTop: '1.5rem', borderTop: '1px solid #eee', paddingTop: '1rem' }}>
                {hints && hints.length > 0 && (
                    <div style={{ marginBottom: '1.5rem' }}>
                        {hintIndex === 0 ? (
                            <button onClick={handleRevealHint} style={{ background: '#f0ad4e', color: 'white', border: 'none', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9rem', fontWeight: 'bold' }}>
                                💡 Need a hint?
                            </button>
                        ) : (
                            <>
                                <h4 style={{ margin: '0 0 0.5rem 0', color: '#666' }}>Hints ({Math.min(hintIndex, hints.length)} / {hints.length})</h4>
                                {hints.slice(0, hintIndex).map((hint, idx) => {
                                    // Parse markdown link [text](url) format simply for hints
                                    const linkMatch = hint.match(/\[(.*?)\]\((.*?)\)/);
                                    if (linkMatch) {
                                        return (
                                            <div key={idx} style={{ padding: '0.75rem', backgroundColor: '#fffbe6', border: '1px solid #ffe58f', borderRadius: '4px', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                                                💡 <a href={linkMatch[2]} target="_blank" rel="noreferrer" style={{ color: '#005571', fontWeight: 'bold' }}>{linkMatch[1]}</a>
                                            </div>
                                        )
                                    }
                                    return (
                                        <div key={idx} style={{ padding: '0.75rem', backgroundColor: '#fffbe6', border: '1px solid #ffe58f', borderRadius: '4px', marginBottom: '0.5rem', fontSize: '0.9rem' }}>
                                            💡 {hint}
                                        </div>
                                    )
                                })}
                                {hintIndex < hints.length && (
                                    <button onClick={handleRevealHint} style={{ background: 'transparent', border: '1px dashed #ccc', color: '#666', padding: '0.5rem 1rem', borderRadius: '4px', cursor: 'pointer', fontSize: '0.9rem', marginTop: '0.5rem' }}>
                                        Reveal Next Hint
                                    </button>
                                )}
                            </>
                        )}
                    </div>
                )}

                <button
                    onClick={() => handleValidate()}
                    style={{
                        backgroundColor: '#005571',
                        color: 'white',
                        border: 'none',
                        padding: '0.75rem 1.5rem',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontWeight: 'bold'
                    }}>
                    Verify Resolution
                </button>
            </div>
        </div>
    );
};

function App() {
    const [token, setToken] = useState(localStorage.getItem('token') || null);
    const [isRegistering, setIsRegistering] = useState(false);
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [authError, setAuthError] = useState('');

    const [tickets, setTickets] = useState([]);
    const [loading, setLoading] = useState(false);
    const [currentView, setCurrentView] = useState('dashboard'); // 'dashboard' | 'admin'
    const [adminStats, setAdminStats] = useState(null);

    useEffect(() => {
        if (token) {
            startGameAndFetchTickets();
        }
    }, [token]);

    const startGameAndFetchTickets = () => {
        setLoading(true);
        fetch('http://localhost:8000/game/start', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => {
                if (!res.ok) {
                    if (res.status === 401) {
                        handleLogout();
                        throw new Error("Unauthorized");
                    }
                    throw res;
                }
                return res.json();
            })
            .then(data => {
                fetchTickets();
            })
            .catch(err => {
                console.error("Error starting game:", err);
                setLoading(false);
            });
    };

    const fetchTickets = () => {
        fetch('http://localhost:8000/tickets', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => res.json())
            .then(data => {
                setTickets(Array.isArray(data) ? data : []);
                setLoading(false);
            })
            .catch(err => {
                console.error("Error fetching tickets:", err);
                setTickets([]);
                setLoading(false);
            });
    };

    const fetchAdminStats = () => {
        fetch('http://localhost:8000/admin/stats', {
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => res.json())
            .then(data => setAdminStats(data))
            .catch(err => console.error("Error fetching admin stats:", err));
    };

    const handleAuth = (e) => {
        e.preventDefault();
        setAuthError('');

        if (isRegistering) {
            fetch('http://localhost:8000/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, email, password })
            })
                .then(res => {
                    if (!res.ok) throw res;
                    return res.json();
                })
                .then(() => {
                    // Auto-login after successful registration
                    login(email, password);
                })
                .catch(async (err) => {
                    const text = await err.text();
                    setAuthError("Registration failed: " + text);
                });
        } else {
            login(email, password);
        }
    };

    const login = (email, password) => {
        const formData = new URLSearchParams();
        formData.append('username', email); // OAuth2 expects 'username' field
        formData.append('password', password);

        fetch('http://localhost:8000/token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: formData
        })
            .then(res => {
                if (!res.ok) throw res;
                return res.json();
            })
            .then(data => {
                setToken(data.access_token);
                localStorage.setItem('token', data.access_token);
            })
            .catch(() => {
                setAuthError("Login failed. Check your credentials.");
            });
    };

    const handleLogout = () => {
        setToken(null);
        localStorage.removeItem('token');
        setTickets([]);
    };

    const handleValidate = () => {
        fetch('http://localhost:8000/game/validate', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` }
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    alert("Awesome! " + data.message);
                    fetchTickets();
                } else {
                    alert("Validation Failed: " + data.message);
                }
            })
            .catch(err => {
                console.error("Validation error:", err);
                alert("An error occurred during validation.");
            });
    };

    if (!token) {
        return (
            <div style={{ padding: '2rem', maxWidth: '400px', margin: '4rem auto', fontFamily: 'sans-serif', textAlign: 'center', border: '1px solid #ddd', borderRadius: '8px', backgroundColor: '#f9f9f9' }}>
                <h1 style={{ color: '#005571', marginBottom: '0.5rem' }}>Elastic Simulator</h1>
                <h2 style={{ fontSize: '1.2rem', marginBottom: '2rem', color: '#555' }}>{isRegistering ? "Register Account" : "Player Login"}</h2>
                {authError && <p style={{ color: 'red', backgroundColor: '#fee', padding: '0.5rem', borderRadius: '4px' }}>{authError}</p>}
                <form onSubmit={handleAuth} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                    {isRegistering && (
                        <input type="text" placeholder="Username" value={username} onChange={e => setUsername(e.target.value)} required style={{ padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc' }} />
                    )}
                    <input type="email" placeholder="Email Address" value={email} onChange={e => setEmail(e.target.value)} required style={{ padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc' }} />
                    <input type="password" placeholder="Password" value={password} onChange={e => setPassword(e.target.value)} required style={{ padding: '0.75rem', borderRadius: '4px', border: '1px solid #ccc' }} />
                    <button type="submit" style={{ padding: '0.75rem', backgroundColor: '#00bfb3', color: 'white', border: 'none', cursor: 'pointer', fontWeight: 'bold', borderRadius: '4px', fontSize: '1rem', marginTop: '0.5rem' }}>
                        {isRegistering ? "Sign Up" : "Login"}
                    </button>
                </form>
                <p style={{ marginTop: '1.5rem', cursor: 'pointer', color: '#005571', fontWeight: 'bold' }} onClick={() => setIsRegistering(!isRegistering)}>
                    {isRegistering ? "Already have an account? Login here." : "Need an account? Register here."}
                </p>
            </div>
        );
    }

    return (
        <div style={{ padding: '2rem', maxWidth: '800px', margin: '0 auto', fontFamily: 'sans-serif' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h1 style={{ color: '#005571' }}>Elastic Simulator Dashboard</h1>
                <div>
                    <button onClick={() => window.open('http://localhost:5601', '_blank')} style={{ padding: '0.5rem 1rem', background: '#e83e8c', color: 'white', border: 'none', cursor: 'pointer', borderRadius: '4px', fontWeight: 'bold', marginRight: '1rem' }}>
                        Open Kibana ↗
                    </button>
                    <button onClick={() => {
                        if (currentView === 'dashboard') {
                            setCurrentView('admin');
                            fetchAdminStats();
                        } else {
                            setCurrentView('dashboard');
                        }
                    }} style={{ padding: '0.5rem 1rem', background: '#00bfb3', color: 'white', border: 'none', cursor: 'pointer', borderRadius: '4px', fontWeight: 'bold', marginRight: '1rem' }}>
                        {currentView === 'dashboard' ? 'Leaderboard' : 'Back to Game'}
                    </button>
                    <button onClick={handleLogout} style={{ padding: '0.5rem 1rem', background: '#ccc', border: 'none', cursor: 'pointer', borderRadius: '4px', fontWeight: 'bold' }}>Logout</button>
                </div>
            </div>

            {currentView === 'admin' ? (
                <div style={{ marginTop: '2rem' }}>
                    <h2>Global Statistics</h2>
                    {adminStats ? (
                        <div>
                            <div style={{ display: 'flex', gap: '2rem', marginBottom: '2rem' }}>
                                <div style={{ padding: '1rem', background: '#f0f4f8', borderRadius: '8px', minWidth: '150px', textAlign: 'center' }}>
                                    <h3>Total Players</h3>
                                    <p style={{ fontSize: '2rem', margin: '0', color: '#005571', fontWeight: 'bold' }}>{adminStats.total_players}</p>
                                </div>
                            </div>
                            <h3>Top 10 Leaderboard</h3>
                            <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '1rem' }}>
                                <thead>
                                    <tr style={{ background: '#005571', color: 'white' }}>
                                        <th style={{ padding: '0.75rem', textAlign: 'left' }}>Rank</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'left' }}>Username</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'left' }}>Stage</th>
                                        <th style={{ padding: '0.75rem', textAlign: 'left' }}>Score</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {adminStats.top_players.map((p, idx) => (
                                        <tr key={idx} style={{ borderBottom: '1px solid #ddd' }}>
                                            <td style={{ padding: '0.75rem' }}>#{idx + 1}</td>
                                            <td style={{ padding: '0.75rem', fontWeight: 'bold' }}>{p.username}</td>
                                            <td style={{ padding: '0.75rem' }}>{p.stage}</td>
                                            <td style={{ padding: '0.75rem', color: '#00bfb3', fontWeight: 'bold' }}>{p.score}</td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <p>Loading stats...</p>
                    )}
                </div>
            ) : (
                <>
                    <p style={{ color: '#666' }}>Welcome to the simulation. Respond to incoming tickets and fix the ELK cluster to advance.</p>

                    <div style={{ marginTop: '2rem' }}>
                        <h2>Incident Queue</h2>
                        {loading && <p>Loading tickets...</p>}
                        {!loading && tickets.length === 0 && <p>Hooray! No open incidents right now.</p>}

                        {tickets.filter(t => t.status === 'open').map(ticket => (
                            <TicketItem key={ticket.id} ticket={ticket} handleValidate={handleValidate} />
                        ))}

                        {tickets.filter(t => t.status !== 'open').length > 0 && (
                            <div style={{ marginTop: '2rem' }}>
                                <h3>Resolved Tickets</h3>
                                {tickets.filter(t => t.status !== 'open').map(ticket => (
                                    <div key={ticket.id} style={{
                                        border: '1px solid #ddd',
                                        borderLeft: '5px solid #00bfb3',
                                        borderRadius: '8px',
                                        padding: '1rem',
                                        marginBottom: '1rem',
                                        backgroundColor: '#f9f9f9',
                                        color: '#666'
                                    }}>
                                        <h4 style={{ margin: 0 }}>{ticket.subject} (Resolved)</h4>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </>
            )}
        </div>
    );
}

export default App;
