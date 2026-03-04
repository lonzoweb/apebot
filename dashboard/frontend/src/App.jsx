import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Home, Sparkles, Gift, Layers, Database, 
  Settings, TrendingUp, Users, Trophy, Trash2, Plus, Save, Download, RefreshCw, Bell, Info, Mail, CreditCard
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
  const [roles, setRoles] = useState({});
  const [channels, setChannels] = useState({});
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  // Form states for new entries
  const [newReward, setNewReward] = useState({ level: '', role_id: '', stack_role: true });
  const [newMultiplier, setNewMultiplier] = useState({ target_id: '', multiplier: '1.5' });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sRes, setRes, rRes, mRes, lRes, rlRes, chRes] = await Promise.all([
        axios.get(`${API_BASE}/stats`),
        axios.get(`${API_BASE}/settings`),
        axios.get(`${API_BASE}/rewards`),
        axios.get(`${API_BASE}/multipliers`),
        axios.get(`${API_BASE}/leaderboard`),
        axios.get(`${API_BASE}/roles`),
        axios.get(`${API_BASE}/channels`),
      ]);
      setStats(sRes.data);
      setSettings(setRes.data);
      setRewards(rRes.data);
      setMultipliers(mRes.data);
      setLeaderboard(lRes.data);
      setRoles(rlRes.data);
      setChannels(chRes.data);
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
      const payload = { ...newReward, stack_role: newReward.stack_role ? 1 : 0 };
      await axios.post(`${API_BASE}/rewards`, payload);
      setRewards(prev => [...prev, { ...newReward }].sort((a,b) => a.level - b.level));
      setNewReward({ level: '', role_id: '', stack_role: true });
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

  const handleRecalculate = async () => {
    if (!window.confirm("This will sweep the database and recalculate levels for EVERYONE based on current settings. Proceed?")) return;
    setSyncing(true);
    try {
      const res = await axios.post(`${API_BASE}/recalculate`);
      alert(`Success! Recalculated levels for ${res.data.count} users.`);
      fetchData();
    } catch (err) { alert("Recalculate failed"); }
    setSyncing(false);
  };

  const navItems = [
    { id: 'home', icon: Home, label: 'Overview' },
    { id: 'xp', icon: Sparkles, label: 'XP Gain' },
    { id: 'notifications', icon: Bell, label: 'Notifications' },
    { id: 'rewards', icon: Gift, label: 'Reward Roles' },
    { id: 'rank', icon: CreditCard, label: 'Rank Card' },
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

            <h2 style={{ marginBottom: '1.5rem' }}>Global Leaderboard (Top 25)</h2>
            <div className="table-container">
              <table>
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>User</th>
                    <th>Level</th>
                    <th>Total XP</th>
                  </tr>
                </thead>
                <tbody>
                  {leaderboard.map((user, i) => (
                    <tr key={user.user_id}>
                      <td style={{ fontWeight: 'bold', color: i < 3 ? 'var(--accent)' : 'inherit' }}>
                        {i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : `#${i + 1}`}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <img 
                            src={user.avatar || 'https://cdn.discordapp.com/embed/avatars/0.png'} 
                            alt="" 
                            style={{ width: '32px', height: '32px', borderRadius: '50%', background: '#2d2d2d' }} 
                          />
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ fontWeight: '600' }}>{user.username}</span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{user.user_id}</span>
                          </div>
                        </div>
                      </td>
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

        {activeTab === 'notifications' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card">
              <h2 style={{ marginBottom: '0.5rem' }}>Level up message</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Send an automatic message in the chat when a member levels up. How fun!</p>
              
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem' }}>
                <div>
                  <h4 style={{ margin: 0 }}>Enable message</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>When enabled, a message or DM will be sent whenever anyone levels up.</p>
                </div>
                <div 
                  className={`toggle ${settings.lvl_msg_enabled === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('lvl_msg_enabled', settings.lvl_msg_enabled === '1' ? '0' : '1')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: '0.5rem' }}>Message</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1rem' }}>The message to send upon levelling up.</p>
              
              <textarea 
                className="input" 
                style={{ width: '100%', minHeight: '120px', fontFamily: 'monospace', fontSize: '0.9rem', padding: '1rem', marginBottom: '1.5rem' }}
                value={settings.lvl_msg_template || ''}
                onChange={(e) => setSettings({ ...settings, lvl_msg_template: e.target.value })}
                onBlur={(e) => updateSetting('lvl_msg_template', e.target.value)}
              />

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div>
                  <label className="label">Variables</label>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Spice up your message with dynamic variables!</p>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {['XP', 'Member', 'Server'].map(v => (
                      <span key={v} className="badge" style={{ background: 'rgba(255,255,255,0.05)', cursor: 'help' }} title={`[[${v.toUpperCase()}]]`}>{v}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="label">Channel</label>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Which channel should the message be sent in?</p>
                  <select 
                    className="input" 
                    value={settings.lvl_msg_channel || 'dm'}
                    onChange={(e) => updateSetting('lvl_msg_channel', e.target.value)}
                  >
                    <option value="dm">Send in DMs</option>
                    <option value="current">Current Channel</option>
                    <optgroup label="Server Channels">
                      {Object.keys(channels).map(id => (
                        <option key={id} value={id}>#{channels[id].name}</option>
                      ))}
                    </optgroup>
                  </select>
                </div>
              </div>

              <div style={{ marginTop: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ margin: 0 }}>Embed mode</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>Send a fancy embed instead of a normal message (advanced!)</p>
                </div>
                <div 
                  className={`toggle ${settings.lvl_msg_embed === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('lvl_msg_embed', settings.lvl_msg_embed === '1' ? '0' : '1')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: '0.5rem' }}>Interval</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>How often the message should be sent (e.g. every 3rd level)</p>

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="form-group">
                  <label className="label">Multiple</label>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Level up messages will only send when reaching a multiple of this number</p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span>Every</span>
                    <input 
                      className="input" type="number" style={{ width: '80px' }}
                      value={settings.lvl_msg_interval || 1}
                      onChange={(e) => updateSetting('lvl_msg_interval', e.target.value)}
                    />
                    <span>level(s)</span>
                  </div>
                </div>
                <div className="form-group">
                  <label className="label">Use multiple until</label>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>Once a member reaches this level, the multiple is no longer used (set to 0 to disable)</p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span>Level</span>
                    <input 
                      className="input" type="number" style={{ width: '80px' }}
                      value={settings.lvl_msg_interval_stop || 0}
                      onChange={(e) => updateSetting('lvl_msg_interval_stop', e.target.value)}
                    />
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '2rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ margin: 0 }}>Reward roles only</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>Only send the level up message when obtaining a new reward role</p>
                </div>
                <div 
                  className={`toggle ${settings.lvl_msg_reward_only === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('lvl_msg_reward_only', settings.lvl_msg_reward_only === '1' ? '0' : '1')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'rewards' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Reward Roles</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Automatically give roles to members when they reach certain levels. For free.</p>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.75rem', marginBottom: '1.5rem', fontStyle: 'italic' }}>Imagine if I tried to capitalize off a couple extra lines of code, haha that would be absolutely crazy</p>
              
              <div style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '0.75rem', padding: '1.25rem', marginBottom: '1.25rem' }}>
                <h4 style={{ marginBottom: '1rem', color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Add role</h4>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'flex-end', flexWrap: 'wrap' }}>
                  <div style={{ flex: 1, minWidth: '200px' }}>
                    <label className="label">Reward</label>
                    <select
                      className="input"
                      value={newReward.role_id}
                      onChange={(e) => setNewReward({ ...newReward, role_id: e.target.value })}
                    >
                      <option value="">(role)</option>
                      {Object.keys(roles).sort((a,b) => (roles[b].position||0) - (roles[a].position||0)).map(rid => (
                        <option key={rid} value={rid}>
                          {roles[rid].name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div style={{ width: '130px' }}>
                    <label className="label">at level</label>
                    <input
                      className="input" type="number" placeholder="1 - 1000"
                      value={newReward.level}
                      onChange={(e) => setNewReward({ ...newReward, level: e.target.value })}
                    />
                  </div>
                  <button className="btn btn-primary" onClick={addReward} style={{ whiteSpace: 'nowrap' }}>Add</button>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginTop: '1rem', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.5rem' }}>
                  <div
                    className={`toggle ${!newReward.stack_role ? 'active' : ''}`}
                    onClick={() => setNewReward({ ...newReward, stack_role: !newReward.stack_role })}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                  <span style={{ fontSize: '0.9rem' }}>Remove this role when a higher role is obtained</span>
                </div>
              </div>

              <h3 style={{ marginBottom: '0.75rem' }}>Current rewards ({rewards.length})</h3>
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Level</th>
                      <th>Role</th>
                      <th>Keep</th>
                      <th>Delete</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rewards.map(reward => {
                      const roleInfo = roles[reward.role_id] || { name: reward.role_id, color: null };
                      const hasColor = roleInfo.color && roleInfo.color !== 'inherit' && roleInfo.color !== '#000000';
                      return (
                        <tr key={reward.level}>
                          <td style={{ fontWeight: 'bold' }}>{reward.level}</td>
                          <td>
                            <span style={{
                              fontWeight: 'bold',
                              color: hasColor ? roleInfo.color : 'var(--text-primary)',
                            }}>
                              {roleInfo.name}
                            </span>
                          </td>
                          <td>
                            <span style={{ color: reward.stack_role ? 'var(--success)' : 'var(--danger)', fontWeight: 'bold' }}>
                              {reward.stack_role ? 'Yes' : 'No'}
                            </span>
                          </td>
                          <td>
                            <button
                              className="btn"
                              style={{ color: 'var(--danger)', background: 'transparent', padding: '0.25rem 0.5rem' }}
                              onClick={() => deleteReward(reward.level)}
                            >
                              <Trash2 size={16} />
                            </button>
                          </td>
                        </tr>
                      );
                    })}
                    {rewards.length === 0 && (
                      <tr><td colSpan="4" style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>No reward roles configured yet.</td></tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Reward Syncing</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>By default, the bot will automatically sync level roles by adding missing ones and removing incorrect ones. Feel free to tweak this behaviour a little.</p>
              
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                <div>
                  <h4 style={{ marginBottom: '0.25rem' }}>Automatic syncing</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>Choose when the bot should automatically sync level roles</p>
                  <select className="input" style={{ width: '100%' }}
                    value={settings.reward_sync_mode || 'levelup'}
                    onChange={(e) => updateSetting('reward_sync_mode', e.target.value)}
                  >
                    <option value="levelup">On level up</option>
                    <option value="always">On every message</option>
                    <option value="never">Never (manual only)</option>
                  </select>
                </div>
                <div>
                  <h4 style={{ marginBottom: '0.25rem' }}>Manual syncing</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>If members should be able to manually sync their roles whenever they want</p>
                  <div
                    className={`toggle ${settings.reward_manual_sync === '1' ? 'active' : ''}`}
                    onClick={() => updateSetting('reward_manual_sync', settings.reward_manual_sync === '1' ? '0' : '1')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
              </div>

              <div style={{ height: '1px', background: 'rgba(255,255,255,0.07)', margin: '1.5rem 0' }} />

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                <div>
                  <h4 style={{ marginBottom: '0.25rem' }}>Show sync warning</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>Displays a warning message in /rank if a member's roles aren't synced properly</p>
                  <div
                    className={`toggle ${settings.reward_sync_warning !== '0' ? 'active' : ''}`}
                    onClick={() => updateSetting('reward_sync_warning', settings.reward_sync_warning === '0' ? '1' : '0')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
                <div>
                  <h4 style={{ marginBottom: '0.25rem' }}>Advanced: Exclude roles</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>Prevent certain roles from being re-added or removed when syncing.</p>
                  <div
                    className={`toggle ${settings.reward_exclude_enabled === '1' ? 'active' : ''}`}
                    onClick={() => updateSetting('reward_exclude_enabled', settings.reward_exclude_enabled === '1' ? '0' : '1')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'rank' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Header Card */}
            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Rank Card</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Tweak the details shown on rank cards.</p>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Some settings may also apply to the online leaderboard.</p>
              <button className="btn btn-primary" style={{ width: 'fit-content', background: 'rgba(99,102,241,0.15)', border: '1px solid rgba(99,102,241,0.35)', color: 'var(--accent)' }} onClick={() => setActiveTab('home')}>
                Visit leaderboard
              </button>

              <div style={{ height: '1px', background: 'rgba(255,255,255,0.07)', margin: '1.5rem 0' }} />

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Enable rank cards</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.35rem 0 0 0' }}>
                    Allows members to check their XP with /rank. Disabling this will also hide most info in /calculate.
                  </p>
                </div>
                <div
                  className={`toggle ${settings.rank_enabled !== '0' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_enabled', settings.rank_enabled === '0' ? '1' : '0')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>
            </div>

            {/* 2-col grid of options */}
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div className="card">
                <h3 style={{ marginBottom: '0.4rem' }}>Hide cooldown</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', minHeight: '2.5rem' }}>
                  Prevents members from viewing the amount of time until they can gain XP again.
                </p>
                <div
                  className={`toggle ${settings.rank_hide_cooldown === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_hide_cooldown', settings.rank_hide_cooldown === '1' ? '0' : '1')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>

              <div className="card">
                <h3 style={{ marginBottom: '0.4rem' }}>Hide multipliers</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', minHeight: '2.5rem' }}>
                  Prevents members from viewing which roles have multipliers. (except 0x)
                </p>
                <div
                  className={`toggle ${settings.rank_hide_multipliers === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_hide_multipliers', settings.rank_hide_multipliers === '1' ? '0' : '1')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>

              <div className="card">
                <h3 style={{ marginBottom: '0.4rem' }}>Force hidden</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', minHeight: '2.5rem' }}>
                  Forces usages of /rank to always be hidden (ephemeral), meaning that only the member who typed the command can see the message.
                </p>
                <div
                  className={`toggle ${settings.rank_force_hidden === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_force_hidden', settings.rank_force_hidden === '1' ? '0' : '1')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>

              <div className="card">
                <h3 style={{ marginBottom: '0.4rem' }}>Relative XP</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem', minHeight: '2.5rem' }}>
                  Changes the 'next level' section of /rank to start at 0 and only include XP from that level. e.g. If level 10 requires 2000 XP and level 11 requires 3000, it will display "500/1000 XP until level 11" for a member with 2500 XP.
                </p>
                <div
                  className={`toggle ${settings.rank_relative_xp !== '0' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_relative_xp', settings.rank_relative_xp === '0' ? '1' : '0')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>
            </div>

            {/* Customization placeholder */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div className="card" style={{ opacity: 0.6 }}>
                <h3 style={{ marginBottom: '0.4rem' }}>Rank card customization</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Not my problem anymore lol</p>
              </div>
            </div>
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
                {multipliers.map(m => {
                  const targetInfo = roles[m.target_id] || channels[m.target_id] || { name: m.target_id, color: 'inherit' };
                  const isChannel = !!channels[m.target_id];
                  return (
                    <tr key={m.target_id}>
                      <td style={{ color: targetInfo.color && targetInfo.color !== '0' ? targetInfo.color : 'inherit', fontWeight: 'bold' }}>
                        {isChannel ? '#' : ''}{targetInfo.name}
                      </td>
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
                  );
                })}
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
            <div className="card">
              <h3 style={{ marginBottom: '1rem', color: 'var(--accent)' }}>Maintenance</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                Reconcile XP with Levels for all users based on current curve settings.
              </p>
              <button className="btn" style={{ width: '100%', background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent)', border: '1px solid rgba(99, 102, 241, 0.2)' }} onClick={handleRecalculate}>
                <RefreshCw size={18} style={{ marginRight: '0.5rem' }} /> Fix Levels
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
