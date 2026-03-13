import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Home, Sparkles, Gift, Layers, Database, 
  Settings, TrendingUp, Users, Trophy, Trash2, Plus, Save, Download, RefreshCw, Bell, Info, Mail, CreditCard, BookOpen, MessageCircle, Send
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
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [stats, setStats] = useState({ total_users: 0, total_xp: 0 });
  const [settings, setSettings] = useState({});
  const [pendingSettings, setPendingSettings] = useState({});
  const [hasPending, setHasPending] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMsg, setSaveMsg] = useState('');
  const [rewards, setRewards] = useState([]);
  const [multipliers, setMultipliers] = useState([]);
  const [leaderboard, setLeaderboard] = useState([]);
  const [roles, setRoles] = useState({});
  const [channels, setChannels] = useState({});
  const [loading, setLoading] = useState(true);
  const [pruneThreshold, setPruneThreshold] = useState('100');
  const [importOptions, setImportOptions] = useState({ importXP: true, importSettings: false });
  const [importFile, setImportFile] = useState(null);
  const [quoteDrops, setQuoteDrops] = useState([]);
  const [quoteDropsPerDay, setQuoteDropsPerDay] = useState(0);
  const [newQuoteDrop, setNewQuoteDrop] = useState('');
  const [dailyQuotes, setDailyQuotes] = useState([]);
  const [newDailyQuote, setNewDailyQuote] = useState('');
  const [channelConfig, setChannelConfig] = useState({});
  const [commandRestrictions, setCommandRestrictions] = useState({});
  const [botCommands, setBotCommands] = useState([]);

  // Form states for new entries
  const [newReward, setNewReward] = useState({ level: '', role_id: '', stack_role: true });
  const [newMultiplier, setNewMultiplier] = useState({ target_id: '', multiplier: '1.5' });

  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (activeTab === 'quotes') {
      Promise.all([
        axios.get(`${API_BASE}/quote-drops`),
        axios.get(`${API_BASE}/quote-drops/settings`),
      ]).then(([qRes, sRes]) => {
        setQuoteDrops(qRes.data);
        setQuoteDropsPerDay(sRes.data.quote_drops_per_day);
      }).catch(err => console.error('Failed to fetch quote drops:', err));
    }
    if (activeTab === 'daily_quotes') {
      axios.get(`${API_BASE}/quotes`).then(res => {
        setDailyQuotes(res.data);
      }).catch(err => console.error('Failed to fetch daily quotes:', err));
    }
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sRes, setRes, rRes, mRes, lRes, rlRes, chRes, ccRes, crRes, cmdsRes] = await Promise.all([
        axios.get(`${API_BASE}/stats`),
        axios.get(`${API_BASE}/settings`),
        axios.get(`${API_BASE}/rewards`),
        axios.get(`${API_BASE}/multipliers`),
        axios.get(`${API_BASE}/leaderboard`),
        axios.get(`${API_BASE}/roles`),
        axios.get(`${API_BASE}/channels`),
        axios.get(`${API_BASE}/channel-config`),
        axios.get(`${API_BASE}/command-restrictions`),
        axios.get(`${API_BASE}/commands`)
      ]);
      setStats(sRes.data);
      setSettings(setRes.data);
      setPendingSettings(setRes.data);
      setHasPending(false);
      setRewards(rRes.data);
      setMultipliers(mRes.data);
      setLeaderboard(lRes.data);
      setRoles(rlRes.data);
      setChannels(chRes.data);
      setChannelConfig(ccRes.data);
      setCommandRestrictions(crRes.data);
      setBotCommands(cmdsRes.data);
    } catch (err) {
      console.error("Failed to fetch data:", err);
    }
    setLoading(false);
  };

  // --- Pending-save model: all setting changes go here first ---
  const updateSetting = (key, value) => {
    setPendingSettings(prev => ({ ...prev, [key]: value }));
    setHasPending(true);
  };

  const saveAllSettings = async () => {
    setSaving(true);
    setSaveMsg('');
    try {
      await axios.post(`${API_BASE}/settings/batch`, { settings: pendingSettings });
      setSettings(pendingSettings);
      setHasPending(false);
      setSaveMsg('✅ Saved!');
      setTimeout(() => setSaveMsg(''), 2500);
    } catch (err) {
      setSaveMsg('❌ Save failed');
    }
    setSaving(false);
  };

  const discardChanges = () => {
    setPendingSettings(settings);
    setHasPending(false);
  };

  // Detect which preset is currently active
  const activePreset = CURVE_PRESETS.find(
    p => String(p.c3) === String(pendingSettings.c3) &&
         String(p.c2) === String(pendingSettings.c2) &&
         String(p.c1) === String(pendingSettings.c1) &&
         String(p.rounding) === String(pendingSettings.rounding)
  );


  const applyPreset = (preset) => {
    const keys = ['c3', 'c2', 'c1', 'rounding'];
    const updates = {};
    keys.forEach(k => { updates[k] = String(preset[k]); });
    setPendingSettings(prev => ({ ...prev, ...updates }));
    setHasPending(true);
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
    { id: 'quotes', icon: BookOpen, label: 'Quotes' },
    { id: 'daily_quotes', icon: MessageCircle, label: 'Daily Quotes' },
    { id: 'misc', icon: Settings, label: 'Misc' },
    { id: 'data', icon: Database, label: 'Data Management' },
  ];

  const closeSidebar = () => setSidebarOpen(false);

  return (
    <div className="dashboard-container">
      {/* Mobile topbar */}
      <div className="mobile-topbar">
        <button className="hamburger" onClick={() => setSidebarOpen(o => !o)} aria-label="Toggle menu">
          <span /><span /><span />
        </button>
        <span className="mobile-topbar-title">APEIRON</span>
      </div>

      {/* Sidebar overlay (closes nav on tap outside) */}
      <div className={`sidebar-overlay ${sidebarOpen ? 'open' : ''}`} onClick={closeSidebar} />

      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'open' : ''}`}>
        <div className="sidebar-logo">
          <TrendingUp size={28} color="#6366f1" />
          <span>APEIRON</span>
        </div>
        <nav>
          {navItems.map(item => (
            <div
            key={item.id}
            className={`nav-item ${activeTab === item.id ? 'active' : ''}`}
            onClick={() => { setActiveTab(item.id); closeSidebar(); }}
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

      {/* Floating Save Bar */}
      {hasPending && (
        <div className="save-bar" style={{
          position: 'fixed', bottom: '2rem', left: '50%', transform: 'translateX(-50%)',
          background: 'rgba(20, 20, 35, 0.98)', border: '1px solid rgba(99,102,241,0.4)',
          borderRadius: '1rem', padding: '0.75rem 1.5rem',
          display: 'flex', alignItems: 'center', gap: '1rem',
          boxShadow: '0 8px 32px rgba(0,0,0,0.6)', zIndex: 1000,
          backdropFilter: 'blur(12px)'
        }}>
          <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>All done?</span>
          <button
            className="btn btn-primary"
            onClick={saveAllSettings}
            disabled={saving}
            style={{ padding: '0.5rem 1.5rem', fontWeight: '700' }}
          >
            {saving ? '⏳ Saving...' : '💾 SAVE'}
          </button>
          <button
            className="btn"
            onClick={discardChanges}
            style={{ padding: '0.5rem 1rem', fontSize: '0.8rem', opacity: 0.7 }}
          >
            Discard
          </button>
          {saveMsg && <span style={{ fontSize: '0.85rem', color: saveMsg.startsWith('✅') ? 'var(--success)' : 'var(--danger)' }}>{saveMsg}</span>}
        </div>
      )}

      {/* Main Content */}
      <div className="main-content">
        <header className="header">
          <h1>{navItems.find(i => i.id === activeTab).label}</h1>
          <p>{{
            home: "Server stats and leaderboard at a glance.",
            xp: "Configure how members earn XP.",
            notifications: "Customize level-up messages and delivery.",
            rewards: "Assign roles automatically at level milestones.",
            rank: "Personalize rank card appearance and behavior.",
            multipliers: "Boost XP rates for specific roles or channels.",
            quotes: "Manage the quote drop bank and frequency.",
            daily_quotes: "Manage quotes for the .quote command and daily posts.",
            misc: "Configure global channel boundaries and command whitelists.",
            data: "Export, import, reset, and prune server data.",
          }[activeTab]}</p>
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
                  value={pendingSettings.c3 || 1} 
                  onChange={(e) => updateSetting('c3', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="label">Coefficient C2 (Quadratic)</label>
                <input 
                  className="input" type="number" step="1"
                  value={pendingSettings.c2 || 50} 
                  onChange={(e) => updateSetting('c2', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="label">Coefficient C1 (Linear)</label>
                <input 
                  className="input" type="number" step="1"
                  value={pendingSettings.c1 || 100} 
                  onChange={(e) => updateSetting('c1', e.target.value)}
                />
              </div>
              <div className="form-group">
                <label className="label">Rounding (Step)</label>
                <input 
                  className="input" type="number"
                  value={pendingSettings.rounding || 100} 
                  onChange={(e) => updateSetting('rounding', e.target.value)}
                />
              </div>
              <h3 style={{ margin: '2rem 0 1rem 0' }}>XP Gain Configuration</h3>
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="form-group">
                  <label className="label">Min XP per message</label>
                  <input 
                    className="input" type="number"
                    value={pendingSettings.xp_min || 15} 
                    onChange={(e) => updateSetting('xp_min', e.target.value)}
                  />
                </div>
                <div className="form-group">
                  <label className="label">Max XP per message</label>
                  <input 
                    className="input" type="number"
                    value={pendingSettings.xp_max || 25} 
                    onChange={(e) => updateSetting('xp_max', e.target.value)}
                  />
                </div>
              </div>
              <div className="form-group">
                <label className="label">Cooldown (seconds)</label>
                <input 
                  className="input" type="number"
                  value={pendingSettings.cooldown || 60} 
                  onChange={(e) => updateSetting('cooldown', e.target.value)}
                />
              </div>
            </div>

            <div className="card" style={{ height: 'fit-content' }}>
              <h3 style={{ marginBottom: '1.5rem' }}>Curve Presets</h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                {CURVE_PRESETS.map(p => {
                  const isActive = activePreset?.name === p.name;
                  return (
                    <button 
                      key={p.name}
                      className="btn"
                      style={{
                        background: isActive ? 'rgba(99,102,241,0.2)' : 'rgba(255,255,255,0.05)',
                        textAlign: 'left', color: 'var(--text-primary)', fontSize: '0.9rem',
                        border: isActive ? '1px solid rgba(99,102,241,0.5)' : '1px solid transparent',
                        display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                      }}
                      onClick={() => applyPreset(p)}
                    >
                      <span>{p.name}</span>
                      {isActive && <span style={{ color: 'var(--accent)', fontWeight: 'bold', fontSize: '1rem' }}>✓</span>}
                    </button>
                  );
                })}
              </div>
              <div style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(99, 102, 241, 0.1)', borderRadius: '0.75rem' }}>
                <p style={{ fontSize: '0.8rem', color: 'var(--accent)', fontWeight: '600', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Sparkles size={14} /> ACTIVE CURVE
                </p>
                <p style={{ fontSize: '1.2rem', fontWeight: 'bold' }}>
                    {pendingSettings.c3}x³ + {pendingSettings.c2}x² + {pendingSettings.c1}x
                </p>
              </div>
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
                  className={`toggle ${pendingSettings.lvl_msg_enabled === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('lvl_msg_enabled', pendingSettings.lvl_msg_enabled === '1' ? '0' : '1')}
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
                value={pendingSettings.lvl_msg_template || ''}
                onChange={(e) => setPendingSettings({ ...pendingSettings, lvl_msg_template: e.target.value })}
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
                    value={pendingSettings.lvl_msg_channel || 'dm'}
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
                  className={`toggle ${pendingSettings.lvl_msg_embed === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('lvl_msg_embed', pendingSettings.lvl_msg_embed === '1' ? '0' : '1')}
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
                      value={pendingSettings.lvl_msg_interval || 1}
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
                      value={pendingSettings.lvl_msg_interval_stop || 0}
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
                  className={`toggle ${pendingSettings.lvl_msg_reward_only === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('lvl_msg_reward_only', pendingSettings.lvl_msg_reward_only === '1' ? '0' : '1')}
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
                    value={pendingSettings.reward_sync_mode || 'levelup'}
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
                    className={`toggle ${pendingSettings.reward_manual_sync === '1' ? 'active' : ''}`}
                    onClick={() => updateSetting('reward_manual_sync', pendingSettings.reward_manual_sync === '1' ? '0' : '1')}
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
                    className={`toggle ${pendingSettings.reward_sync_warning !== '0' ? 'active' : ''}`}
                    onClick={() => updateSetting('reward_sync_warning', pendingSettings.reward_sync_warning === '0' ? '1' : '0')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
                <div>
                  <h4 style={{ marginBottom: '0.25rem' }}>Advanced: Exclude roles</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>Prevent certain roles from being re-added or removed when syncing.</p>
                  <div
                    className={`toggle ${pendingSettings.reward_exclude_enabled === '1' ? 'active' : ''}`}
                    onClick={() => updateSetting('reward_exclude_enabled', pendingSettings.reward_exclude_enabled === '1' ? '0' : '1')}
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
                  className={`toggle ${pendingSettings.rank_enabled !== '0' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_enabled', pendingSettings.rank_enabled === '0' ? '1' : '0')}
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
                  className={`toggle ${pendingSettings.rank_hide_cooldown === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_hide_cooldown', pendingSettings.rank_hide_cooldown === '1' ? '0' : '1')}
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
                  className={`toggle ${pendingSettings.rank_hide_multipliers === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_hide_multipliers', pendingSettings.rank_hide_multipliers === '1' ? '0' : '1')}
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
                  className={`toggle ${pendingSettings.rank_force_hidden === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_force_hidden', pendingSettings.rank_force_hidden === '1' ? '0' : '1')}
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
                  className={`toggle ${pendingSettings.rank_relative_xp !== '0' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_relative_xp', pendingSettings.rank_relative_xp === '0' ? '1' : '0')}
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
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {/* Header */}
            <div className="card">
              <h2 style={{ marginBottom: '0.35rem' }}>Data</h2>
              <p style={{ color: 'var(--text-secondary)' }}>Settings related to the server's data.</p>
            </div>

            {/* Download section */}
            <div className="card">
              <h3 style={{ marginBottom: '0.35rem' }}>Download XP</h3>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '0.25rem' }}>Exports everyone's XP into a single file (only contains user ID and XP)</p>
              <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1.25rem' }}>Download all data if you wish to import your settings into an open-source fork of Stardust.</p>
              <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button className="btn btn-primary" onClick={handleExport}>
                  <Download size={16} style={{ marginRight: '0.4rem' }} /> Download all data
                </button>
                <button className="btn" style={{ background: 'rgba(255,255,255,0.07)' }} onClick={() => {
                  window.open(`${API_BASE}/export`, '_blank');
                }}>Download as .json</button>
                <button className="btn" style={{ background: 'rgba(255,255,255,0.07)' }} onClick={() => {
                  window.open(`${API_BASE}/export/csv`, '_blank');
                }}>Download as .csv</button>
                <button className="btn" style={{ background: 'rgba(255,255,255,0.07)' }} onClick={() => {
                  window.open(`${API_BASE}/export/txt`, '_blank');
                }}>Download as .txt</button>
              </div>
            </div>

            {/* Danger zone 2-col grid */}
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div className="card">
                <h3 style={{ marginBottom: '0.4rem', color: 'var(--danger)' }}>Clear all XP</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem', minHeight: '3.5rem' }}>
                  Delete everyone's XP and start fresh. All XP will be reset to 0, but reward roles will not be removed unless done manually. <strong>This cannot be undone!</strong>
                </p>
                <button
                  className="btn" style={{ background: 'var(--danger)', color: '#fff', fontWeight: '700' }}
                  onClick={async () => {
                    if (!window.confirm('Reset ALL user XP to 0? This cannot be undone!')) return;
                    await axios.post(`${API_BASE}/clear-xp`);
                    fetchData();
                    alert('All XP cleared!');
                  }}
                >
                  Reset!
                </button>
              </div>

              <div className="card">
                <h3 style={{ marginBottom: '0.4rem', color: 'var(--danger)' }}>Reset settings</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem', minHeight: '3.5rem' }}>
                  Restores the defaults for all configurable settings such as the curve, reward roles, multipliers, level up message, etc. XP will not be cleared. <strong>This cannot be undone!</strong>
                </p>
                <button
                  className="btn" style={{ background: 'var(--danger)', color: '#fff', fontWeight: '700' }}
                  onClick={async () => {
                    if (!window.confirm('Reset ALL settings, reward roles and multipliers to defaults? This cannot be undone!')) return;
                    await axios.post(`${API_BASE}/reset-settings`);
                    fetchData();
                    alert('Settings reset! Bot will reinitialize defaults on next startup.');
                  }}
                >
                  Reset!
                </button>
              </div>
            </div>

            {/* Prune */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem' }}>
              <div className="card">
                <h3 style={{ marginBottom: '0.4rem' }}>Prune Members</h3>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                  Deletes the data of everyone who has less than a certain amount of XP. Might speed up load times. <strong>This cannot be undone!</strong>
                </p>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                  <label style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>Less than:</label>
                  <input
                    className="input" type="number" style={{ width: '100px' }}
                    value={pruneThreshold}
                    onChange={(e) => setPruneThreshold(e.target.value)}
                  />
                  <button
                    className="btn" style={{ background: 'var(--danger)', color: '#fff', fontWeight: '700', whiteSpace: 'nowrap' }}
                    onClick={async () => {
                      if (!window.confirm(`Delete all users with less than ${pruneThreshold} XP? Cannot be undone!`)) return;
                      const res = await axios.post(`${API_BASE}/prune`, { threshold: parseInt(pruneThreshold) });
                      fetchData();
                      alert(`Pruned ${res.data.deleted} members.`);
                    }}
                  >
                    Prune!
                  </button>
                </div>
              </div>
            </div>

            {/* Import section */}
            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0 }}>Import settings and XP from</h3>
                <select className="input" style={{ width: 'auto' }}>
                  <option>.json file</option>
                </select>
              </div>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.25rem' }}>Copies XP and settings from another server using this bot. Requires server owner</p>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>The expected .json format is the same as when you press "download all data" at the top of this</p>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                <label style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', whiteSpace: 'nowrap' }}>Import from:</label>
                <input
                  type="file" accept=".json"
                  style={{ flex: 1, padding: '0.4rem', background: 'rgba(255,255,255,0.05)', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text-primary)' }}
                  onChange={(e) => setImportFile(e.target.files[0])}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.5rem', marginBottom: '0.75rem' }}>
                <div
                  className={`toggle ${importOptions.importXP ? 'active' : ''}`}
                  onClick={() => setImportOptions(prev => ({ ...prev, importXP: !prev.importXP }))}
                >
                  <div className="toggle-handle"></div>
                </div>
                <span style={{ fontSize: '0.9rem' }}>Import XP (overwrites existing members!)</span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.5rem', marginBottom: '1.25rem' }}>
                <div
                  className={`toggle ${importOptions.importSettings ? 'active' : ''}`}
                  onClick={() => setImportOptions(prev => ({ ...prev, importSettings: !prev.importSettings }))}
                >
                  <div className="toggle-handle"></div>
                </div>
                <span style={{ fontSize: '0.9rem' }}>Import settings (cooldown, curve, level up message, etc) [requires bot owner for security reasons]</span>
              </div>

              <button
                className="btn btn-primary"
                onClick={async () => {
                  if (!importFile) return alert('Please select a file first.');
                  const reader = new FileReader();
                  reader.onload = async (event) => {
                    try {
                      const jsonData = JSON.parse(event.target.result);
                      if (!importOptions.importSettings) delete jsonData.settings;
                      if (!importOptions.importXP) delete jsonData.users;
                      const res = await axios.post(`${API_BASE}/import`, jsonData);
                      alert(`Import Successful!\nDetails: ${res.data.details.join(', ')}`);
                      fetchData();
                    } catch (err) {
                      alert('Import failed: ' + (err.response?.data?.detail || 'Invalid JSON'));
                    }
                  };
                  reader.readAsText(importFile);
                }}
                style={{ fontWeight: '700' }}
              >
                Import!
              </button>
            </div>
          </div>
        )}

        {activeTab === 'quotes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Quote Drops</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>The bot randomly drops user-submitted quotes in #forum when chat is active. These are added via <code>=quote</code> (reply to a message) in Discord.</p>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
                <button 
                  className="btn btn-primary" 
                  onClick={async () => {
                    if (!confirm('Are you sure you want to drop a random quote into the #forum channel right now?')) return;
                    try {
                      const res = await axios.post(`${API_BASE}/quote-drops/send`, {});
                      alert(`\u2705 Random quote sent!\n\n"${res.data.sent_quote}"`);
                    } catch (err) { 
                      alert('Failed to send quote: ' + (err.response?.data?.detail || err.message)); 
                    }
                  }}
                >
                  <Send size={16} style={{ marginRight: '0.5rem' }} /> Send Random Quote
                </button>
              </div>

              <div style={{ padding: '0.75rem 1rem', background: 'rgba(99,102,241,0.08)', borderRadius: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
                <Info size={14} style={{ marginRight: '0.4rem', verticalAlign: '-2px' }} />
                Quotes are added when someone replies to a message with <code>=quote</code>. Text-only Hall of Fame entries (\u226425 chars) are auto-added. Pinging the bot has a 40% chance of triggering a random quote. Links and emojis are stripped.
              </div>
            </div>

            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0 }}>Quote Bank ({quoteDrops.length})</h3>
                <button className="btn" style={{ fontSize: '0.8rem' }} onClick={async () => {
                  try {
                    const [qRes, sRes] = await Promise.all([
                      axios.get(`${API_BASE}/quote-drops`),
                      axios.get(`${API_BASE}/quote-drops/settings`),
                    ]);
                    setQuoteDrops(qRes.data);
                    setQuoteDropsPerDay(sRes.data.quote_drops_per_day);
                  } catch (err) { console.error(err); }
                }}>
                  <RefreshCw size={14} style={{ marginRight: '0.3rem' }} /> Refresh
                </button>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <input 
                  className="input" style={{ flex: 1 }}
                  placeholder="Add a quote manually..."
                  value={newQuoteDrop}
                  onChange={(e) => setNewQuoteDrop(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newQuoteDrop.trim()) {
                      axios.post(`${API_BASE}/quote-drops`, { quote: newQuoteDrop.trim() }).then(() => {
                        setQuoteDrops(prev => [{ id: Date.now(), quote: newQuoteDrop.trim() }, ...prev]);
                        setNewQuoteDrop('');
                      }).catch(() => alert('Failed to add quote'));
                    }
                  }}
                />
                <button 
                  className="btn btn-primary"
                  onClick={async () => {
                    if (!newQuoteDrop.trim()) return;
                    try {
                      await axios.post(`${API_BASE}/quote-drops`, { quote: newQuoteDrop.trim() });
                      setQuoteDrops(prev => [{ id: Date.now(), quote: newQuoteDrop.trim() }, ...prev]);
                      setNewQuoteDrop('');
                    } catch (err) { alert('Failed to add quote'); }
                  }}
                >
                  <Plus size={16} />
                </button>
              </div>

              <div style={{ maxHeight: '500px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {quoteDrops.map(q => (
                  <div key={q.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <span style={{ flex: 1, fontSize: '0.9rem' }}>{q.quote}</span>
                    <div style={{ display: 'flex', gap: '0.25rem', flexShrink: 0 }}>
                      <button
                        className="btn"
                        title="Send this specific quote to #forum"
                        style={{ color: 'var(--primary)', background: 'transparent', padding: '0.25rem 0.5rem' }}
                        onClick={async () => {
                          if (!confirm(`Drop this quote into #forum now?\n\n"${q.quote}"`)) return;
                          try {
                            await axios.post(`${API_BASE}/quote-drops/send`, { drop_id: q.id });
                            alert('\u2705 Quote sent successfully!');
                          } catch (err) { 
                            alert('Send failed: ' + (err.response?.data?.detail || err.message)); 
                          }
                        }}
                      >
                        <Send size={14} />
                      </button>
                      <button
                        className="btn"
                        title="Delete quote"
                        style={{ color: 'var(--danger)', background: 'transparent', padding: '0.25rem 0.5rem' }}
                        onClick={async () => {
                          try {
                            await axios.delete(`${API_BASE}/quote-drops/${q.id}`);
                            setQuoteDrops(prev => prev.filter(x => x.id !== q.id));
                          } catch (err) { alert('Delete failed'); }
                        }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
                {quoteDrops.length === 0 && (
                  <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>No quotes yet. Use <code>=quote</code> in Discord to add some!</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'daily_quotes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Daily Quotes</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>These are the quotes used by the <code>.quote</code> command and the daily scheduled quote posts. This is a separate pool from the Quote Drops system.</p>
            </div>

            <div className="card">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                <h3 style={{ margin: 0 }}>All Daily Quotes ({dailyQuotes.length})</h3>
                <button className="btn" style={{ fontSize: '0.8rem' }} onClick={async () => {
                  try {
                    const res = await axios.get(`${API_BASE}/quotes`);
                    setDailyQuotes(res.data);
                  } catch (err) { console.error(err); }
                }}>
                  <RefreshCw size={14} style={{ marginRight: '0.3rem' }} /> Refresh
                </button>
              </div>

              <div style={{ display: 'flex', gap: '0.75rem', marginBottom: '1.25rem' }}>
                <input 
                  className="input" style={{ flex: 1 }}
                  placeholder="Add a daily quote..."
                  value={newDailyQuote}
                  onChange={(e) => setNewDailyQuote(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && newDailyQuote.trim()) {
                      axios.post(`${API_BASE}/quotes`, { quote: newDailyQuote.trim() }).then(() => {
                        setDailyQuotes(prev => [{ id: Date.now(), quote: newDailyQuote.trim() }, ...prev]);
                        setNewDailyQuote('');
                      }).catch(() => alert('Failed to add quote'));
                    }
                  }}
                />
                <button 
                  className="btn btn-primary"
                  onClick={async () => {
                    if (!newDailyQuote.trim()) return;
                    try {
                      await axios.post(`${API_BASE}/quotes`, { quote: newDailyQuote.trim() });
                      setDailyQuotes(prev => [{ id: Date.now(), quote: newDailyQuote.trim() }, ...prev]);
                      setNewDailyQuote('');
                    } catch (err) { alert('Failed to add quote'); }
                  }}
                >
                  <Plus size={16} />
                </button>
              </div>

              <div style={{ maxHeight: '500px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {dailyQuotes.map(q => (
                  <div key={q.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem 1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <span style={{ flex: 1, fontSize: '0.9rem' }}>{q.quote}</span>
                    <button
                      className="btn"
                      style={{ color: 'var(--danger)', background: 'transparent', padding: '0.25rem 0.5rem', flexShrink: 0 }}
                      onClick={async () => {
                        try {
                          await axios.delete(`${API_BASE}/quotes/${q.id}`);
                          setDailyQuotes(prev => prev.filter(x => x.id !== q.id));
                        } catch (err) { alert('Delete failed'); }
                      }}
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                ))}
                {dailyQuotes.length === 0 && (
                  <p style={{ textAlign: 'center', color: 'var(--text-secondary)', padding: '2rem' }}>No daily quotes yet. Add one above!</p>
                )}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'misc' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Channel Configuration</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Specify specific channels for roles like Main, Spam, Admin, and Error log routes.</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
                {['main', 'spam', 'admin', 'error'].map(role => (
                  <div key={role} style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <label className="label" style={{ textTransform: 'capitalize', fontWeight: 'bold' }}>{role} Channel</label>
                    <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                      <select
                        className="input"
                        style={{ flex: 1 }}
                        value={channelConfig[role] || ''}
                        onChange={(e) => setChannelConfig({ ...channelConfig, [role]: e.target.value })}
                      >
                        <option value="">-- Disabled --</option>
                        {Object.entries(channels).map(([id, channelObj]) => (
                          <option key={id} value={id}>#{channelObj.name}</option>
                        ))}
                      </select>
                      <button 
                        className="btn btn-primary"
                        title="Save Channel"
                        onClick={async (e) => {
                          const btn = e.currentTarget;
                          const parent = btn.parentElement;
                          try {
                            await axios.post(`${API_BASE}/channel-config`, { role, channel_id: channelConfig[role] || '' });
                            // Show inline checkmark
                            let indicator = parent.querySelector('.save-indicator');
                            if (!indicator) {
                              indicator = document.createElement('span');
                              indicator.className = 'save-indicator';
                              indicator.style.cssText = 'color: #22c55e; font-weight: bold; font-size: 1.1rem; transition: opacity 0.3s;';
                              parent.appendChild(indicator);
                            }
                            indicator.textContent = '✓';
                            indicator.style.opacity = '1';
                            setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
                          } catch (err) {
                            let indicator = parent.querySelector('.save-indicator');
                            if (!indicator) {
                              indicator = document.createElement('span');
                              indicator.className = 'save-indicator';
                              indicator.style.cssText = 'color: #ef4444; font-weight: bold; font-size: 0.85rem; transition: opacity 0.3s;';
                              parent.appendChild(indicator);
                            }
                            indicator.textContent = '✗';
                            indicator.style.opacity = '1';
                            setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
                          }
                        }}
                      >
                        <Save size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Command Restrictions</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Select which commands are allowed to be run in the <strong>Main</strong> or <strong>Spam</strong> channels. Admin channel bypasses all restrictions.</p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                {['main', 'spam'].map(role => (
                  <div key={role} style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <h3 style={{ textTransform: 'capitalize', borderBottom: '1px solid rgba(255,255,255,0.1)', paddingBottom: '0.5rem', marginBottom: '1rem' }}>{role} Whitelist</h3>
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '0.75rem' }}>
                      {botCommands.map(cmd => {
                        const isAllowed = commandRestrictions[role]?.[cmd] || false;
                        return (
                          <label key={cmd} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.9rem', cursor: 'pointer' }}>
                            <input
                              type="checkbox"
                              checked={isAllowed}
                              onChange={async (e) => {
                                const checked = e.target.checked;
                                // Optimistic UI update
                                setCommandRestrictions(prev => ({
                                  ...prev,
                                  [role]: { ...(prev[role] || {}), [cmd]: checked }
                                }));
                                try {
                                  await axios.post(`${API_BASE}/command-restrictions`, { command_name: cmd, role, is_allowed: checked });
                                } catch (err) {
                                  alert(`Failed to save restriction for ${cmd}`);
                                  // Revert optimistic update
                                  setCommandRestrictions(prev => ({
                                    ...prev,
                                    [role]: { ...(prev[role] || {}), [cmd]: isAllowed }
                                  }));
                                }
                              }}
                              style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                            />
                            <code>.{cmd}</code>
                          </label>
                        );
                      })}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
