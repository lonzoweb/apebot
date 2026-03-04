import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Home, Sparkles, Gift, Layers, Database, 
  Settings, TrendingUp, Users, Trophy, Trash2, Plus, Save, Download, RefreshCw
} from 'lucide-react';

const API_BASE = window.location.origin;

const CURVE_PRESETS = [
  { name: "Polaris (Default)", c3: 1, c2: 50, c1: 100, rounding: 100 },
  { name: "RoboTop", c3: 5, c2: 100, c1: 150, rounding: 100 },
  { name: "Generous", c3: 0.5, c2: 20, c1: 50, rounding: 50 },
  { name: "Minecraft", c3: 0, c2: 2, c1: 7, rounding: 0 },
  { name: "Linear", c3: 0, c2: 0, c1: 100, rounding: 0 },
  { name: "Definitely not Mee6", c3: 1.6666666667, c2: 22.5, c1: 75.8333333333, rounding: 5 }
];

function App() {
  const [activeTab, setActiveTab] = useState('home');
  const [stats, setStats] = useState({ total_users: 0, total_xp: 0 });
  const [settings, setSettings] = useState({});
  const [rewards, setRewards] = useState([]);
  const [multipliers, setMultipliers] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Form states for new entries
  const [newReward, setNewReward] = useState({ level: '', role_id: '' });
  const [newMultiplier, setNewMultiplier] = useState({ target_id: '', multiplier: '1.5' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sRes, setRes, rRes, mRes, lRes] = await Promise.all([
        axios.get(`${API_BASE}/stats`),
        axios.get(`${API_BASE}/settings`),
        axios.get(`${API_BASE}/rewards`),
        axios.get(`${API_BASE}/multipliers`),
        axios.get(`${API_BASE}/leaderboard`),
      ]);
      setStats(sRes.data);
      setSettings(setRes.data);
      setRewards(rRes.data);
      setMultipliers(mRes.data);
      setLeaderboard(lRes.data);
    } catch (err) {
      console.error("Failed to fetch data:", err);
    }
    setLoading(false);
  };

  const updateSetting = async (key, value) => {
    setSyncing(true);
    try {
      await axios.post(`${API_BASE}/settings`, { key, value: String(value) });
      setSettings(prev => ({ ...prev, [key]: value }));
    } catch (err) { alert("Update failed"); }
    setTimeout(() => setSyncing(false), 500);
  };

  const applyPreset = async (preset) => {
    setSyncing(true);
    try {
      const keys = ['c3', 'c2', 'c1', 'rounding'];
      await Promise.all(keys.map(k => axios.post(`${API_BASE}/settings`, { key: k, value: String(preset[k]) })));
      setSettings(prev => ({ ...prev, ...preset }));
    } catch (err) { alert("Preset failed"); }
    setTimeout(() => setSyncing(false), 500);
  };

  const addReward = async () => {
    if (!newReward.level || !newReward.role_id) return;
    try {
      await axios.post(`${API_BASE}/rewards`, newReward);
      setRewards(prev => [...prev, newReward].sort((a,b) => a.level - b.level));
      setNewReward({ level: '', role_id: '' });
    } catch (err) { alert("Failed to add reward"); }
  };

  const deleteReward = async (level) => {
    try {
      await axios.delete(`${API_BASE}/rewards/${level}`);
      setRewards(prev => prev.filter(r => r.level !== level));
    } catch (err) { alert("Delete failed"); }
  };

  const addMultiplier = async () => {
    if (!newMultiplier.target_id || !newMultiplier.multiplier) return;
    try {
      await axios.post(`${API_BASE}/multipliers`, newMultiplier);
      setMultipliers(prev => [...prev, newMultiplier]);
      setNewMultiplier({ target_id: '', multiplier: '1.5' });
    } catch (err) { alert("Failed to add multiplier"); }
  };

  const deleteMultiplier = async (id) => {
    try {
      await axios.delete(`${API_BASE}/multipliers/${id}`);
      setMultipliers(prev => prev.filter(m => m.target_id !== id));
    } catch (err) { alert("Delete failed"); }
  };

  const handleExport = async () => {
    try {
      const res = await axios.get(`${API_BASE}/export`);
      const blob = new Blob([JSON.stringify(res.data, null, 4)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `apeiron_export_${new Date().getTime()}.json`;
      a.click();
    } catch (err) { alert("Export failed"); }
  };

  const handleImport = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const jsonData = JSON.parse(event.target.result);
        const res = await axios.post(`${API_BASE}/import`, jsonData);
        alert(`Import Successful!\nAdded: ${res.data.details.join(', ')}`);
        fetchData();
      } catch (err) {
        alert("Import failed: " + (err.response?.data?.detail || "Invalid JSON"));
      }
    };
    reader.readAsText(file);
  };

  const navItems = [
    { id: 'home', icon: Home, label: 'Overview' },
    { id: 'xp', icon: Sparkles, label: 'XP Gain' },
    { id: 'rewards', icon: Gift, label: 'Reward Roles' },
    { id: 'multipliers', icon: Layers, label: 'Multipliers' },
    { id: 'data', icon: Database, label: 'Data Management' },
  ];

  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-logo">
          <TrendingUp size={28} color="#6366f1" />
          <span>APEIRON</span>
        </div>
        <nav>
          {navItems.map(item => (
            <div 
              key={item.id}
              className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <item.icon size={20} />
              <span>{item.label}</span>
            </div>
          ))}
        </nav>
        <div style={{ marginTop: 'auto' }}>
          <div className="nav-item">
            <Settings size={20} />
            <span>Settings</span>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <header className="header">
          <h1>{navItems.find(i => i.id === activeTab).label}</h1>
          <p>Manage your server's leveling ecosystem.</p>
        </header>

        {activeTab === 'home' && (
          <>
            <div className="grid">
              <div className="card">
                <div className="card-title"><Users size={16} /> Total Members</div>
                <div className="card-value">{stats.total_users.toLocaleString()}</div>
              </div>
              <div className="card">
                <div className="card-title"><TrendingUp size={16} /> Total XP Generated</div>
                <div className="card-value">{stats.total_xp.toLocaleString()}</div>
              </div>
              <div className="card">
                <div className="card-title"><Trophy size={16} /> Top Level</div>
                <div className="card-value">{leaderboard[0]?.level || 0}</div>
              </div>
            </div>

            <h2 style={{ marginBottom: '1.5rem' }}>Global Leaderboard</h2>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>User ID</th>
                    <th>Level</th>
                    <th>Total XP</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((user, i) => (
                    <tr key={user.user_id}>
                      <td>#{i + 1}</td>
                      <td><code>{user.user_id}</code></td>
                      <td><span className="badge badge-success">Level {user.level}</span></td>
                      <td>{user.xp.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}

        {activeTab === 'xp' && (
          <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
            <div className="card">
              <h3 style={{ marginBottom: '1.5rem' }}>Polaris Cubic Curve</h3>
              <div className="form-group">
                <label className="label">Coefficient C3 (Cubic)</label>
                <input 
                  className="input" type="number" step="0.1"
                  value={settings.c3 || 1} 
                  onChange={(e) => updateSetting('c3', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="label">Coefficient C2 (Quadratic)</label>
                <input 
                  className="input" type="number" step="1"
                  value={settings.c2 || 50} 
                  onChange={(e) => updateSetting('c2', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="label">Coefficient C1 (Linear)</label>
                <input 
                  className="input" type="number" step="1"
                  value={settings.c1 || 100} 
                  onChange={(e) => updateSetting('c1', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="label">Rounding (Step)</label>
                <input 
                  className="input" type="number"
                  value={settings.rounding || 100} 
                  onChange={(e) => updateSetting('rounding', e.target.value)}
                />
              </div>
              <h3 style={{ margin: '2rem 0 1rem 0' }}>XP Gain Configuration</h3>
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="form-group">
                  <label className="label">Min XP per message</label>
                  <input 
                    className="input" type="number"
                    value={settings.xp_min || 15} 
                    onChange={(e) => updateSetting('xp_min', e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="label">Max XP per message</label>
                  <input 
                    className="input" type="number"
                    value={settings.xp_max || 25} 
                    onChange={(e) => updateSetting('xp_max', e.target.value)}
                  />
                </div>
              </div>
              <div className="form-group">
                <label className="label">Cooldown (seconds)</label>
                <input 
                  className="input" type="number"
                  value={settings.cooldown || 60} 
                  onChange={(e) => updateSetting('cooldown', e.target.value)}
                />
              </div>
            </div>

            <div className="card" style={{ height: 'fit-content' }}>
              <h3 style={{ marginBottom: '1.5rem' }}>Curve Presets</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {CURVE_PRESETS.map(p => (
                  <button 
                    key={p.name}
                    className="btn"
                    style={{ background: 'rgba(255,255,255,0.05)', textAlign: 'left', color: 'var(--text-primary)', fontSize: '0.9rem' }}
                    onClick={() => applyPreset(p)}
                  >
                    {p.name}
                  </button>
                ))}
              </div>
              <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(99, 102, 241, 0.1)', borderRadius: '0.75rem' }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--accent)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Sparkles size={14} /> ACTIVE CURVE
                </p>
                <p style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                    {settings.c3}x³ + {settings.c2}x² + {settings.c1}x
                </p>
              </div>
              {syncing && (
                <div style={{ marginTop: '1rem', fontSize: '0.8rem', color: 'var(--success)', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <RefreshCw size={14} className="spin" /> Syncing changes...
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'rewards' && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Level</th>
                  <th>Role ID</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {rewards.map(reward => (
                  <tr key={reward.level}>
                    <td>Level {reward.level}</td>
                    <td><code>{reward.role_id}</code></td>
                    <td>
                      <button 
                        className="btn" 
                        style={{ color: 'var(--danger)', background: 'transparent' }}
                        onClick={() => deleteReward(reward.level)}
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
                <tr>
                  <td>
                    <input 
                      className="input" placeholder="Lvl" style={{ width: '80px' }} 
                      value={newReward.level}
                      onChange={(e) => setNewReward({ ...newReward, level: e.target.value })}
                    />
                  </td>
                  <td>
                    <input 
                      className="input" placeholder="Role ID" 
                      value={newReward.role_id}
                      onChange={(e) => setNewReward({ ...newReward, role_id: e.target.value })}
                    />
                  </td>
                  <td>
                    <button className="btn btn-primary" onClick={addReward}>
                      <Plus size={18} />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'multipliers' && (
          <div className="table-container">
            <table>
              <thead>
                <tr>
                  <th>Role/Channel ID</th>
                  <th>Multiplier</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {multipliers.map(m => (
                  <tr key={m.target_id}>
                    <td><code>{m.target_id}</code></td>
                    <td><span className="badge badge-success">{m.multiplier}x</span></td>
                    <td>
                      <button 
                        className="btn" 
                        style={{ color: 'var(--danger)', background: 'transparent' }}
                        onClick={() => deleteMultiplier(m.target_id)}
                      >
                        <Trash2 size={18} />
                      </button>
                    </td>
                  </tr>
                ))}
                <tr>
                  <td>
                    <input 
                      className="input" placeholder="Role or Channel ID" 
                      value={newMultiplier.target_id}
                      onChange={(e) => setNewMultiplier({ ...newMultiplier, target_id: e.target.value })}
                    />
                  </td>
                  <td>
                    <input 
                      className="input" placeholder="1.5" style={{ width: '100px' }}
                      value={newMultiplier.multiplier}
                      onChange={(e) => setNewMultiplier({ ...newMultiplier, multiplier: e.target.value })}
                    />
                  </td>
                  <td>
                    <button className="btn btn-primary" onClick={addMultiplier}>
                      <Plus size={18} />
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        )}

        {activeTab === 'data' && (
          <div className="grid">
            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Download XP</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                Export everyone's XP and server settings into a Polaris-compliant file.
              </p>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button className="btn btn-primary" style={{ flex: 1 }} onClick={handleExport}>
                   <Download size={18} style={{ marginRight: '0.5rem' }} /> Export JSON
                </button>
              </div>
            </div>
            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>Import Data</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                Upload a Polaris-compatible JSON file to migrate users and settings.
              </p>
              <label className="btn btn-primary" style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                <RefreshCw size={18} /> Select & Import
                <input type="file" accept=".json" onChange={handleImport} style={{ display: 'none' }} />
              </label>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
