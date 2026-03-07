import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

// --- Framer Motion Animation Variants ---
const fadeIn = {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
    transition: { duration: 0.2 },
};

const slideUp = {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
    transition: { duration: 0.3, ease: 'easeOut' },
};

const scaleOnHover = {
    whileHover: { scale: 1.02 },
    whileTap: { scale: 0.98 },
    transition: { type: 'spring', stiffness: 400, damping: 17 },
};

const ToastNotification = ({ notification }) => {
    if (!notification) return null;

    return (
        <motion.div
            initial={{ opacity: 0, y: -50, scale: 0.9 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -20, scale: 0.9 }}
            className={`fixed top-6 left-1/2 -translate-x-1/2 z-50 px-6 py-4 rounded-xl shadow-2xl backdrop-blur-md border ${notification.type === 'success'
                ? 'bg-status-success/20 border-status-success text-status-success'
                : 'bg-status-error/20 border-status-error text-status-error'
                }`}
        >
            <div className="flex items-center gap-3">
                <span className="text-xl">{notification.type === 'success' ? '🏆' : '⚠️'}</span>
                <span className="font-semibold">{notification.message}</span>
            </div>
        </motion.div>
    );
};

export const TicketItem = React.forwardRef(({ ticket, handleValidate, handleSkip, isSkipping }, ref) => {
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
        <motion.div
            ref={ref}
            className="glass-panel p-6 mb-6 rounded-xl border-l-4 border-l-status-error shadow-lg"
            variants={slideUp}
            initial="initial"
            animate="animate"
            exit="exit"
            layout
        >
            <h3 className="mt-0 mb-2 text-xl font-semibold text-text-primary">{ticket.subject}</h3>
            <p className="text-text-secondary text-sm mb-4"><strong>From:</strong> {ticket.sender_name}</p>
            <div className="italic bg-neutral-bg3/50 p-4 rounded-md border border-border text-text-primary/90">
                "{ticket.body}"
            </div>

            <div className="mt-6 border-t border-border pt-4">
                {hints && hints.length > 0 && (
                    <div className="mb-6">
                        {hintIndex === 0 ? (
                            <motion.button
                                {...scaleOnHover}
                                onClick={handleRevealHint}
                                className="bg-status-warning/90 hover:bg-status-warning text-white border-none py-2 px-4 rounded-md cursor-pointer text-sm font-bold shadow-lg transition-colors"
                            >
                                💡 Need a hint?
                            </motion.button>
                        ) : (
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-3">
                                <h4 className="m-0 text-text-muted text-sm uppercase tracking-wider font-semibold">
                                    Hints ({Math.min(hintIndex, hints.length)} / {hints.length})
                                </h4>
                                <AnimatePresence>
                                    {hints.slice(0, hintIndex).map((hint, idx) => {
                                        const linkMatch = hint.match(/\[(.*?)\]\((.*?)\)/);
                                        return (
                                            <motion.div
                                                key={idx}
                                                variants={fadeIn}
                                                initial="initial"
                                                animate="animate"
                                                className="p-3 bg-brand-subtle border border-brand/30 rounded-md text-sm text-text-primary"
                                            >
                                                💡 {linkMatch ? (
                                                    <a href={linkMatch[2]} target="_blank" rel="noreferrer" className="text-brand-light font-bold hover:underline">{linkMatch[1]}</a>
                                                ) : hint}
                                            </motion.div>
                                        );
                                    })}
                                </AnimatePresence>
                                {hintIndex < hints.length && (
                                    <motion.button
                                        {...scaleOnHover}
                                        onClick={handleRevealHint}
                                        className="bg-transparent border border-dashed border-text-muted text-text-secondary py-2 px-4 rounded-md cursor-pointer text-sm mt-3 hover:bg-white/5 hover:text-text-primary transition-colors"
                                    >
                                        Reveal Next Hint
                                    </motion.button>
                                )}
                            </motion.div>
                        )}
                    </div>
                )}

                <div className="flex flex-col sm:flex-row gap-3 w-full sm:w-auto mt-6">
                    <motion.button
                        {...scaleOnHover}
                        onClick={() => handleValidate()}
                        className="bg-brand hover:bg-brand-hover text-white border-none py-3 px-6 rounded-md cursor-pointer font-bold transition-colors shadow-glow flex-1 sm:flex-none"
                    >
                        Verify Resolution
                    </motion.button>
                    {ticket.status === 'open' && (
                        <motion.button
                            {...scaleOnHover}
                            onClick={() => handleSkip()}
                            disabled={isSkipping}
                            className={`bg-transparent border border-text-muted hover:border-text-primary text-text-secondary hover:text-text-primary py-3 px-6 rounded-md cursor-pointer font-bold transition-colors flex-1 sm:flex-none ${isSkipping ? 'opacity-50 cursor-not-allowed' : ''}`}
                        >
                            {isSkipping ? 'Skipping...' : 'Skip Stage ⏭️'}
                        </motion.button>
                    )}
                </div>
            </div>
        </motion.div>
    );
});
TicketItem.displayName = 'TicketItem';

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
    const [notification, setNotification] = useState(null);
    const [selectedTicketId, setSelectedTicketId] = useState(null);
    const [isSkipping, setIsSkipping] = useState(false);

    const showNotification = (type, message) => {
        setNotification({ type, message });
        setTimeout(() => setNotification(null), 5000);
    };

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
        setCurrentView('dashboard');
    };

    const handleValidate = () => {
        if (!activeTicket) return;
        fetch('http://localhost:8000/game/validate', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ticket_id: activeTicket.id })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showNotification('success', "Awesome! " + data.message);
                    fetchTickets();
                } else {
                    showNotification('error', "Validation Failed: " + data.message);
                }
            })
            .catch(err => {
                console.error("Validation error:", err);
                showNotification('error', "An error occurred during validation.");
            });
    };

    const handleSkip = () => {
        if (!activeTicket) return;
        if (!window.confirm("Are you sure you want to skip this stage? You won't receive points for it.")) return;
        setIsSkipping(true);
        fetch('http://localhost:8000/game/skip', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ ticket_id: activeTicket.id })
        })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    showNotification('success', data.message);
                    setTickets([]); // forcefully clear to trigger animation out
                    fetchTickets();
                } else {
                    showNotification('error', "Skip Failed: " + data.message);
                }
            })
            .catch(err => {
                console.error("Skip error:", err);
                showNotification('error', "An error occurred during skip.");
            })
            .finally(() => {
                setIsSkipping(false);
            });
    };

    const openTickets = tickets.filter(t => t.status === 'open');
    const resolvedTickets = tickets.filter(t => t.status !== 'open');
    const activeTicket = tickets.find(t => t.id === selectedTicketId) || (openTickets.length > 0 ? openTickets[0] : (resolvedTickets.length > 0 ? resolvedTickets[0] : null));

    // --- RENDER LOGIN FLOW ---
    if (!token) {
        return (
            <div className="flex items-center justify-center min-h-screen p-4 inset-0 fixed relative overflow-hidden">
                <div className="absolute w-[800px] h-[800px] bg-brand-light/10 blur-[100px] rounded-full -top-40 -left-20 mix-blend-screen pointer-events-none"></div>
                <div className="absolute w-[600px] h-[600px] bg-blue-500/10 blur-[100px] rounded-full bottom-0 right-0 mix-blend-screen pointer-events-none"></div>

                <motion.div
                    variants={slideUp}
                    initial="initial"
                    animate="animate"
                    className="glass-card p-10 max-w-md w-full relative z-10"
                >
                    <div className="text-center mb-8">
                        <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-light to-brand m-0 mb-2">
                            Elastic Simulator
                        </h1>
                        <h2 className="text-lg font-medium text-text-secondary m-0">
                            {isRegistering ? "Register Account" : "Player Login"}
                        </h2>
                    </div>

                    <AnimatePresence mode="wait">
                        {authError && (
                            <motion.div
                                key="error"
                                variants={fadeIn}
                                initial="initial"
                                animate="animate"
                                exit="exit"
                                className="bg-status-error/10 border border-status-error/20 text-status-error p-3 rounded-md mb-6 text-sm text-center font-medium"
                            >
                                {authError}
                            </motion.div>
                        )}
                    </AnimatePresence>

                    <form onSubmit={handleAuth} className="flex flex-col gap-5">
                        <AnimatePresence>
                            {isRegistering && (
                                <motion.div
                                    key="register-fields"
                                    variants={slideUp}
                                    initial="initial"
                                    animate="animate"
                                    exit="exit"
                                >
                                    <input
                                        type="text"
                                        placeholder="Username"
                                        value={username}
                                        onChange={e => setUsername(e.target.value)}
                                        required
                                        className="glass-input p-3 w-full rounded-md text-text-primary placeholder:text-text-muted outline-none transition-all box-border"
                                    />
                                </motion.div>
                            )}
                        </AnimatePresence>
                        <input
                            type="email"
                            placeholder="Email Address"
                            value={email}
                            onChange={e => setEmail(e.target.value)}
                            required
                            className="glass-input p-3 rounded-md text-text-primary placeholder:text-text-muted outline-none transition-all w-full box-border"
                        />
                        <input
                            type="password"
                            placeholder="Password"
                            value={password}
                            onChange={e => setPassword(e.target.value)}
                            required
                            className="glass-input p-3 rounded-md text-text-primary placeholder:text-text-muted outline-none transition-all w-full box-border"
                        />

                        <motion.button
                            {...scaleOnHover}
                            type="submit"
                            className="p-3 bg-brand hover:bg-brand-hover text-white border-none cursor-pointer font-bold rounded-md text-base mt-2 shadow-glow transition-colors"
                        >
                            {isRegistering ? "Sign Up" : "Login"}
                        </motion.button>
                    </form>

                    <p
                        className="mt-6 text-center cursor-pointer text-brand-light text-sm font-medium hover:text-brand-hover hover:underline transition-colors"
                        onClick={() => {
                            setIsRegistering(!isRegistering);
                            setAuthError('');
                        }}
                    >
                        {isRegistering ? "Already have an account? Login here." : "Need an account? Register here."}
                    </p>
                </motion.div>
            </div>
        );
    }

    // --- RENDER MAIN GAME DASHBOARD ---
    return (
        <div className="p-4 sm:p-8 max-w-6xl mx-auto pb-20 relative">
            <AnimatePresence>
                {notification && <ToastNotification key="toast" notification={notification} />}
            </AnimatePresence>

            <motion.div
                className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-10 gap-4"
                initial={{ opacity: 0, y: -20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.4 }}
            >
                <div>
                    <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-brand-light to-brand m-0 leading-tight">Elastic Simulator</h1>
                    <p className="text-text-secondary m-0 mt-1">Production Diagnostics Training</p>
                </div>
                <div className="flex gap-3 flex-wrap">
                    <motion.button
                        {...scaleOnHover}
                        onClick={() => window.open('http://localhost:5601', '_blank')}
                        className="px-4 py-2 bg-pink-500 hover:bg-pink-600 text-white border-none cursor-pointer rounded-md font-bold shadow-lg shadow-pink-500/20"
                    >
                        Open Kibana ↗
                    </motion.button>
                    <motion.button
                        {...scaleOnHover}
                        onClick={() => {
                            if (currentView === 'dashboard') {
                                setCurrentView('admin');
                                fetchAdminStats();
                            } else {
                                setCurrentView('dashboard');
                            }
                        }}
                        className="px-4 py-2 bg-neutral-bg3 hover:bg-neutral-bg4 border border-border text-white cursor-pointer rounded-md font-medium transition-colors"
                    >
                        {currentView === 'dashboard' ? 'Leaderboard' : 'Back to Game'}
                    </motion.button>
                    <motion.button
                        {...scaleOnHover}
                        onClick={handleLogout}
                        className="px-4 py-2 bg-transparent hover:bg-white/10 border border-text-muted text-text-primary cursor-pointer rounded-md font-medium transition-colors"
                    >
                        Logout
                    </motion.button>
                </div>
            </motion.div>

            <AnimatePresence mode="wait">
                {currentView === 'admin' ? (
                    <motion.div
                        key="admin"
                        variants={slideUp}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                        className="mt-8"
                    >
                        <h2 className="text-2xl font-semibold mb-6">Global Statistics</h2>
                        {adminStats ? (
                            <div>
                                <div className="flex flex-wrap gap-6 mb-8">
                                    <div className="glass-card p-6 min-w-[200px] text-center border-t-4 border-t-brand flex-1 sm:flex-none">
                                        <h3 className="text-text-secondary font-medium m-0 uppercase text-xs tracking-wider">Total Players</h3>
                                        <p className="text-4xl m-0 mt-2 text-brand-light font-bold drop-shadow-md">{adminStats.total_players}</p>
                                    </div>
                                </div>

                                <h3 className="text-xl font-medium mb-4 text-text-primary">Top 10 Leaderboard</h3>
                                <div className="glass-card overflow-hidden">
                                    <table className="w-full border-collapse text-left">
                                        <thead>
                                            <tr className="bg-neutral-bg3 border-b border-border text-sm">
                                                <th className="p-4 font-semibold text-text-secondary">Rank</th>
                                                <th className="p-4 font-semibold text-text-secondary">Username</th>
                                                <th className="p-4 font-semibold text-text-secondary">Stage</th>
                                                <th className="p-4 font-semibold text-text-secondary text-right">Score</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {adminStats.top_players.map((p, idx) => (
                                                <motion.tr
                                                    initial={{ opacity: 0, x: -10 }}
                                                    animate={{ opacity: 1, x: 0 }}
                                                    transition={{ delay: idx * 0.05 }}
                                                    key={idx}
                                                    className="border-b border-border-subtle hover:bg-white/5 transition-colors group"
                                                >
                                                    <td className="p-4 text-text-muted">
                                                        {idx === 0 ? '🏆 #1' : `#${idx + 1}`}
                                                    </td>
                                                    <td className="p-4 font-bold text-text-primary group-hover:text-brand-light transition-colors">{p.username}</td>
                                                    <td className="p-4 text-text-secondary">Level {p.stage}</td>
                                                    <td className="p-4 text-brand-light font-bold text-right">{p.score}</td>
                                                </motion.tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        ) : (
                            <div className="glass-card p-12 text-center text-text-muted animate-pulse">
                                Loading latest leaderboard statistics...
                            </div>
                        )}
                    </motion.div>
                ) : (
                    <motion.div
                        key="dashboard"
                        variants={slideUp}
                        initial="initial"
                        animate="animate"
                        exit="exit"
                    >
                        <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            transition={{ delay: 0.1 }}
                            className="glass-card p-6 mb-8 bg-brand-subtle border-brand/20 flex flex-col sm:flex-row items-center justify-between gap-4"
                        >
                            <p className="text-text-primary text-lg font-medium m-0">Welcome to the active simulation floor.</p>
                            <span className="bg-status-success/20 text-status-success border border-status-success/30 px-3 py-1 rounded-full text-sm font-semibold flex items-center gap-2">
                                <span className="w-2 h-2 rounded-full bg-status-success animate-pulse inline-block"></span>
                                System Online
                            </span>
                        </motion.div>

                        <div className="mt-8 grid grid-cols-1 lg:grid-cols-12 gap-8">
                            <div className="lg:col-span-4 space-y-6">
                                <h2 className="text-2xl font-semibold flex items-center gap-3 text-text-primary m-0">
                                    <span className="text-brand-light">📋</span>
                                    Incident Board
                                </h2>

                                {loading && (
                                    <div className="glass-card p-6 text-center text-text-muted animate-pulse text-sm">
                                        Syncing queue...
                                    </div>
                                )}

                                <div className="space-y-3">
                                    <h3 className="text-sm font-bold text-text-secondary uppercase tracking-wider">To Do ({openTickets.length})</h3>
                                    {openTickets.map(ticket => (
                                        <motion.div
                                            key={ticket.id}
                                            onClick={() => setSelectedTicketId(ticket.id)}
                                            className={`p-4 rounded-xl cursor-pointer border-l-4 transition-all ${activeTicket?.id === ticket.id ? 'glass-panel border-brand shadow-glow' : 'glass-card border-status-error/50 hover:bg-white/5 opacity-80 hover:opacity-100'}`}
                                            whileHover={{ scale: 1.02 }}
                                            whileTap={{ scale: 0.98 }}
                                        >
                                            <h4 className="m-0 text-text-primary text-md">{ticket.subject}</h4>
                                            <p className="text-xs text-text-muted m-0 mt-2 truncate">Stage Level {ticket.scenario_id}</p>
                                        </motion.div>
                                    ))}
                                    {openTickets.length === 0 && !loading && (
                                        <div className="text-sm text-status-success font-medium italic p-3 border border-dashed border-status-success/30 rounded-md">Queue is empty!</div>
                                    )}
                                </div>

                                <div className="space-y-3 mt-6">
                                    <h3 className="text-sm font-bold text-text-secondary uppercase tracking-wider">Done ({resolvedTickets.length})</h3>
                                    <div className="max-h-64 overflow-y-auto space-y-3 pr-2 custom-scrollbar">
                                        {resolvedTickets.map(ticket => (
                                            <motion.div
                                                key={ticket.id}
                                                onClick={() => setSelectedTicketId(ticket.id)}
                                                className={`p-3 rounded-lg cursor-pointer border-l-4 transition-all ${activeTicket?.id === ticket.id ? 'glass-panel border-status-success bg-white/5' : 'bg-neutral-bg3 border-status-success/30 hover:bg-neutral-bg4 opacity-60 hover:opacity-100'}`}
                                            >
                                                <h4 className="m-0 text-text-secondary text-sm font-medium flex items-center gap-2">
                                                    <span className="text-status-success">✓</span>
                                                    <span className="truncate">{ticket.subject}</span>
                                                </h4>
                                            </motion.div>
                                        ))}
                                    </div>
                                </div>
                            </div>

                            <div className="lg:col-span-8">
                                <AnimatePresence mode="wait">
                                    {activeTicket ? (
                                        <motion.div
                                            key={activeTicket.id}
                                            initial={{ opacity: 0, x: 20 }}
                                            animate={{ opacity: 1, x: 0 }}
                                            exit={{ opacity: 0, x: -20 }}
                                            transition={{ duration: 0.3 }}
                                        >
                                            <h2 className="text-2xl font-semibold mb-6 flex items-center gap-3 text-text-primary">
                                                Active Ticket View
                                                {activeTicket.status === 'open' ? (
                                                    <span className="ml-auto text-xs px-3 py-1 bg-status-error/20 border border-status-error/30 text-status-error rounded-full animate-pulse">Action Required</span>
                                                ) : (
                                                    <span className="ml-auto text-xs px-3 py-1 bg-status-success/20 border border-status-success/30 text-status-success rounded-full">Resolved</span>
                                                )}
                                            </h2>
                                            <TicketItem key={activeTicket.id} ticket={activeTicket} handleValidate={handleValidate} handleSkip={handleSkip} isSkipping={isSkipping} />
                                        </motion.div>
                                    ) : (
                                        <motion.div variants={fadeIn} initial="initial" animate="animate" className="glass-card p-12 text-center text-text-muted mt-[4.5rem]">
                                            Select an incident from the board to view and treat it.
                                        </motion.div>
                                    )}
                                </AnimatePresence>
                            </div>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}

export default App;
