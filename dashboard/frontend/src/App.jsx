import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Home, Sparkles, Gift, Layers, Database, 
  Settings, TrendingUp, Users, Trophy, Trash2, Plus, Save, Download, RefreshCw, Bell, Info, Mail, CreditCard, BookOpen, MessageCircle, Send, Hash
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
  const [quoteDropsEnabled, setQuoteDropsEnabled] = useState(false);
  const [quoteDropsInterval, setQuoteDropsInterval] = useState(8);
  const [newQuoteDrop, setNewQuoteDrop] = useState('');
  const [dailyQuotes, setDailyQuotes] = useState([]);
  const [newDailyQuote, setNewDailyQuote] = useState('');
  const [channelConfig, setChannelConfig] = useState({});
  const [commandRestrictions, setCommandRestrictions] = useState({});
  const [botCommands, setBotCommands] = useState([]);
  const [commandStats, setCommandStats] = useState([]);
  const [hofSettings, setHofSettings] = useState({ channel_id: '', threshold: 3, emojis: ['⭐'], ignored_channels: [], blacklisted_users: [] });
  const [hofEmojiInput, setHofEmojiInput] = useState('');
  const [adminConfig, setAdminConfig] = useState({ tarot_deck: 'thoth', economy_enabled: true, yap_level: 'high' });
  const [adminSaving, setAdminSaving] = useState(false);
  const [adminSaveMsg, setAdminSaveMsg] = useState('');
  const [keySettings, setKeySettings] = useState({ active_url: '', images: [], send_count_user: 2, send_count_admin: 6 });
  const [keyImageInput, setKeyImageInput] = useState('');
  const [keyLabelInput, setKeyLabelInput] = useState('');
  const [keySendUser, setKeySendUser] = useState(2);
  const [keySendAdmin, setKeySendAdmin] = useState(6);
  const [keySaveMsg, setKeySaveMsg] = useState('');
  const [confirmSendRandom, setConfirmSendRandom] = useState(false);
  const [confirmSendId, setConfirmSendId] = useState(null);
  const [sendSuccess, setSendSuccess] = useState(null); // 'random' or id

  // Numerology state
  const [numerologySettings, setNumerologySettings] = useState({ morning_hour: 7, evening_hour: 22, channel_id: '' });
  const [numerologyNumbers, setNumerologyNumbers] = useState({}); // {num: description}
  const [numerologyCombos, setNumerologyCombos] = useState([]); // [{primary_num, secondary_num, combo_desc}]
  const [numerologyPreview, setNumerologyPreview] = useState(null);
  const [numerologyPreviewLoading, setNumerologyPreviewLoading] = useState(false);
  const [numerologySaveMsg, setNumerologySaveMsg] = useState('');
  const [numerologyEditNum, setNumerologyEditNum] = useState(null); // which number is being edited
  const [numerologyEditCombo, setNumerologyEditCombo] = useState(null); // {primary_num, secondary_num}
  const [numerologyEditText, setNumerologyEditText] = useState('');

  // Quote schedule state
  const [quoteSchedule, setQuoteSchedule] = useState({ morning_hour: 10, evening_hour: 18 });
  const [quoteScheduleSaveMsg, setQuoteScheduleSaveMsg] = useState('');

  // Form states for new entries
  const [newReward, setNewReward] = useState({ level: '', role_id: '', stack_role: true });
  const [newMultiplier, setNewMultiplier] = useState({ target_id: '', multiplier: '1.5' });

  // Shop state
  const [shopItems, setShopItems] = useState([]);
  const [shopSaveMsg, setShopSaveMsg] = useState(null);
  const [depositInfo, setDepositInfo] = useState("");
  const [depositSaveMsg, setDepositSaveMsg] = useState(null);
  const [bulletinSettings, setBulletinSettings] = useState({ channel_id: '', weekly_purge_enabled: 0, daily_tc_time: '08:00' });
  const [bulletinSaveMsg, setBulletinSaveMsg] = useState(null);


  useEffect(() => {
    fetchData();
  }, []);

  useEffect(() => {
    if (confirmSendRandom) {
      const timer = setTimeout(() => setConfirmSendRandom(false), 3000);
      return () => clearTimeout(timer);
    }
  }, [confirmSendRandom]);

  useEffect(() => {
    if (confirmSendId) {
      const timer = setTimeout(() => setConfirmSendId(null), 3000);
      return () => clearTimeout(timer);
    }
  }, [confirmSendId]);

  useEffect(() => {
    if (sendSuccess) {
      const timer = setTimeout(() => setSendSuccess(null), 2000);
      return () => clearTimeout(timer);
    }
  }, [sendSuccess]);

  useEffect(() => {
    if (activeTab === 'quotes') {
      Promise.all([
        axios.get(`${API_BASE}/quote-drops`),
        axios.get(`${API_BASE}/quote-drops/settings`),
      ]).then(([qRes, sRes]) => {
        setQuoteDrops(qRes.data);
        setQuoteDropsEnabled(sRes.data.quote_drops_enabled);
        setQuoteDropsInterval(sRes.data.quote_drops_interval_hours);
      }).catch(err => console.error('Failed to fetch quote drops:', err));
    }
    if (activeTab === 'daily_quotes') {
      axios.get(`${API_BASE}/quotes`).then(res => {
        setDailyQuotes(res.data);
      }).catch(err => console.error('Failed to fetch daily quotes:', err));
      axios.get(`${API_BASE}/quote-schedule`).then(res => {
        setQuoteSchedule(res.data);
      }).catch(err => console.error('Failed to fetch quote schedule:', err));
    }
    if (activeTab === 'numerology') {
      Promise.all([
        axios.get(`${API_BASE}/numerology/settings`),
        axios.get(`${API_BASE}/numerology/numbers`),
        axios.get(`${API_BASE}/numerology/combos`),
      ]).then(([sRes, nRes, cRes]) => {
        setNumerologySettings(sRes.data);
        setNumerologyNumbers(nRes.data);
        setNumerologyCombos(cRes.data);
      }).catch(err => console.error('Failed to fetch numerology data:', err));
    }
    if (activeTab === 'shop') {
      axios.get(`${API_BASE}/shop/items`).then(res => {
        setShopItems(res.data);
      }).catch(err => console.error('Failed to fetch shop items:', err));
    }
    if (activeTab === 'misc') {
      Promise.all([
        axios.get(`${API_BASE}/deposit-info`),
        axios.get(`${API_BASE}/bulletin/settings`)
      ]).then(([dRes, bRes]) => {
        setDepositInfo(dRes.data.deposit_info);
        setBulletinSettings(bRes.data);
      }).catch(err => console.error('Failed to fetch misc data:', err));
    }
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sRes, setRes, rRes, mRes, lRes, rlRes, chRes, ccRes, crRes, cmdsRes, hofRes, adminRes] = await Promise.all([
        axios.get(`${API_BASE}/stats`),
        axios.get(`${API_BASE}/settings`),
        axios.get(`${API_BASE}/rewards`),
        axios.get(`${API_BASE}/multipliers`),
        axios.get(`${API_BASE}/leaderboard`),
        axios.get(`${API_BASE}/roles`),
        axios.get(`${API_BASE}/channels`),
        axios.get(`${API_BASE}/channel-config`),
        axios.get(`${API_BASE}/command-restrictions`),
        axios.get(`${API_BASE}/commands`),
        axios.get(`${API_BASE}/hof-settings`),
        axios.get(`${API_BASE}/admin-config`)
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
      setHofSettings(hofRes.data);
      setHofEmojiInput((hofRes.data.emojis || []).join(' '));
      setAdminConfig(adminRes.data);
      const [ks, cs] = await Promise.all([
        axios.get(`${API_BASE}/key-settings`),
        axios.get(`${API_BASE}/command-stats`)
      ]);
      setKeySettings(ks.data);
      setCommandStats(cs.data);
      setKeySendUser(ks.data.send_count_user);
      setKeySendAdmin(ks.data.send_count_admin);
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

  const saveDepositInfo = async () => {
    try {
      await axios.post(`${API_BASE}/deposit-info`, { deposit_info: depositInfo });
      setDepositSaveMsg('✅ Saved!');
      setTimeout(() => setDepositSaveMsg(null), 2000);
    } catch (err) {
      setDepositSaveMsg('❌ Failed');
    }
  };

  const handleSaveBulletinSettings = async () => {
    setSaving(true);
    try {
      await axios.post(`${API_BASE}/bulletin/settings`, bulletinSettings);
      setBulletinSaveMsg('✅ Bulletin settings saved!');
      setTimeout(() => setBulletinSaveMsg(null), 3000);
    } catch (err) {
      console.error('Failed to save bulletin settings:', err);
      setBulletinSaveMsg('❌ Error saving settings.');
      setTimeout(() => setBulletinSaveMsg(null), 3000);
    }
    setSaving(false);
  };

  const handleTriggerTarot = async () => {
    setSaving(true);
    try {
      await axios.post(`${API_BASE}/bulletin/trigger-tarot`);
      setBulletinSaveMsg('🎴 Tarot Draw Triggered!');
      setTimeout(() => setBulletinSaveMsg(null), 3000);
    } catch (err) {
      console.error('Failed to trigger tarot:', err);
      setBulletinSaveMsg('❌ Error triggering tarot.');
      setTimeout(() => setBulletinSaveMsg(null), 3000);
    }
    setSaving(false);
  };

  const navItems = [
    { id: 'home', icon: Home, label: 'Overview' },
    { id: 'xp', icon: Sparkles, label: 'XP Gain' },
    { id: 'notifications', icon: Bell, label: 'Notifications' },
    { id: 'rewards', icon: Gift, label: 'Reward Roles' },
    { id: 'rank', icon: CreditCard, label: 'Rank Card' },
    { id: 'multipliers', icon: Layers, label: 'Multipliers' },
    { id: 'quotes', icon: BookOpen, label: 'QUOTES DROP' },
    { id: 'daily_quotes', icon: MessageCircle, label: 'Daily Quotes' },
    { id: 'numerology', icon: Hash, label: 'Numerology' },
    { id: 'shop', icon: CreditCard, label: 'Shop' },
    { id: 'misc', icon: Settings, label: 'Misc' },
    { id: 'admin', icon: Users, label: 'Admin' },
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
            numerology: "Configure daily numerology readings and content.",
            misc: "Configure global channel boundaries and command whitelists.",
            admin: "Tarot deck, economy toggle, and yap level.",
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
              <h2 style={{ marginBottom: '0.25rem' }}>Automated Quote Drops</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Automatically send a quote from the bank at regular intervals when chat is active.</p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1.25rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.05)', marginBottom: '1.5rem' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <h4 style={{ margin: 0 }}>Enable Automated Cycle</h4>
                    <p style={{ margin: 0, fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Send a random quote from the bank every X hours.</p>
                  </div>
                  <div
                    className={`toggle ${quoteDropsEnabled ? 'active' : ''}`}
                    onClick={async () => {
                      const newState = !quoteDropsEnabled;
                      setQuoteDropsEnabled(newState);
                      try {
                        await axios.post(`${API_BASE}/quote-drops/settings`, { 
                          quote_drops_enabled: newState,
                          quote_drops_interval_hours: quoteDropsInterval
                        });
                      } catch (err) { alert('Failed to save settings'); setQuoteDropsEnabled(!newState); }
                    }}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>

                {quoteDropsEnabled && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', paddingTop: '0.5rem', borderTop: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ flex: 1 }}>
                      <p style={{ margin: 0, fontSize: '0.85rem' }}>Hours between turns:</p>
                      <p style={{ margin: 0, fontSize: '0.75rem', color: 'var(--text-secondary)' }}>If no chat activity in the last 30 minutes, the turn is skipped.</p>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <input 
                        type="number" className="input" style={{ width: '70px', textAlign: 'center' }}
                        value={quoteDropsInterval}
                        onChange={(e) => setQuoteDropsInterval(parseInt(e.target.value) || 1)}
                        onBlur={async () => {
                          try {
                            await axios.post(`${API_BASE}/quote-drops/settings`, { 
                              quote_drops_enabled: quoteDropsEnabled,
                              quote_drops_interval_hours: quoteDropsInterval
                            });
                          } catch (err) { alert('Failed to save settings'); }
                        }}
                      />
                      <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Hours</span>
                    </div>
                  </div>
                )}
              </div>

              <div style={{ height: '1px', background: 'rgba(255,255,255,0.07)', margin: '1.5rem 0' }} />

              <h3 style={{ marginBottom: '0.5rem' }}>Manual Quote Drop</h3>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Manually trigger a random drop or send a specific quote from the bank.</p>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.5rem' }}>
                {!confirmSendRandom && sendSuccess !== 'random' && (
                  <button
                    className="btn btn-primary"
                    onClick={() => setConfirmSendRandom(true)}
                  >
                    <Send size={16} style={{ marginRight: '0.5rem' }} /> Send Random Quote
                  </button>
                )}
                {confirmSendRandom && (
                  <button
                    className="btn"
                    style={{ background: '#f59e0b', color: '#fff', fontWeight: 'bold' }}
                    onClick={async () => {
                      setConfirmSendRandom(false);
                      try {
                        const res = await axios.post(`${API_BASE}/quote-drops/send`, {});
                        setSendSuccess('random');
                      } catch (err) {
                        alert('Failed to send quote: ' + (err.response?.data?.detail || err.message));
                      }
                    }}
                  >
                    Confirm Send?
                  </button>
                )}
                {sendSuccess === 'random' && (
                  <div style={{ color: '#22c55e', fontWeight: 'bold', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                    <Send size={16} /> Sent!
                  </div>
                )}
              </div>
              <div style={{ padding: '0.75rem 1rem', background: 'rgba(99,102,241,0.08)', borderRadius: '0.5rem', fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                <Info size={14} style={{ marginRight: '0.4rem', verticalAlign: '-2px' }} />
                Quotes are added when someone replies to a message with <code>=quote</code>. Text-only Hall of Fame entries (≤25 chars) are auto-added. Pinging the bot has a 40% chance of triggering a random quote. Links and emojis are stripped.
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
                      {confirmSendId !== q.id && sendSuccess !== q.id && (
                        <button
                          className="btn"
                          title="Send this specific quote to #forum"
                          style={{ color: 'var(--primary)', background: 'transparent', padding: '0.25rem 0.5rem' }}
                          onClick={() => setConfirmSendId(q.id)}
                        >
                          <Send size={14} />
                        </button>
                      )}
                      {confirmSendId === q.id && (
                        <button
                          className="btn"
                          style={{ color: '#f59e0b', background: 'transparent', padding: '0.25rem 0.5rem', fontWeight: 'bold', fontSize: '0.75rem' }}
                          onClick={async () => {
                            setConfirmSendId(null);
                            try {
                              await axios.post(`${API_BASE}/quote-drops/send`, { drop_id: q.id });
                              setSendSuccess(q.id);
                            } catch (err) { 
                              alert('Send failed: ' + (err.response?.data?.detail || err.message)); 
                            }
                          }}
                        >
                          Send?
                        </button>
                      )}
                      {sendSuccess === q.id && (
                        <span style={{ color: '#22c55e', fontSize: '0.75rem', fontWeight: 'bold', padding: '0.25rem 0.5rem' }}>✓</span>
                      )}
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

            {/* Schedule settings */}
            <div className="card">
              <h3 style={{ marginBottom: '1rem' }}>📅 Post Schedule (LA Time)</h3>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                <div className="form-group">
                  <label className="label">Morning Post (hour, 0-23)</label>
                  <input
                    className="input" type="number" min="0" max="23"
                    value={quoteSchedule.morning_hour}
                    onChange={e => setQuoteSchedule(prev => ({ ...prev, morning_hour: parseInt(e.target.value) || 0 }))}
                  />
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    Currently: {quoteSchedule.morning_hour}:00 LA ({quoteSchedule.morning_hour < 12 ? `${quoteSchedule.morning_hour || 12}am` : quoteSchedule.morning_hour === 12 ? '12pm' : `${quoteSchedule.morning_hour - 12}pm`})
                  </p>
                </div>
                <div className="form-group">
                  <label className="label">Evening Post (hour, 0-23)</label>
                  <input
                    className="input" type="number" min="0" max="23"
                    value={quoteSchedule.evening_hour}
                    onChange={e => setQuoteSchedule(prev => ({ ...prev, evening_hour: parseInt(e.target.value) || 0 }))}
                  />
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>
                    Currently: {quoteSchedule.evening_hour}:00 LA ({quoteSchedule.evening_hour < 12 ? `${quoteSchedule.evening_hour || 12}am` : quoteSchedule.evening_hour === 12 ? '12pm' : `${quoteSchedule.evening_hour - 12}pm`})
                  </p>
                </div>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <button
                  className="btn btn-primary"
                  onClick={async () => {
                    try {
                      await axios.post(`${API_BASE}/quote-schedule`, quoteSchedule);
                      setQuoteScheduleSaveMsg('✅ Saved!');
                      setTimeout(() => setQuoteScheduleSaveMsg(''), 2500);
                    } catch { setQuoteScheduleSaveMsg('❌ Failed'); }
                  }}
                >
                  <Save size={14} style={{ marginRight: '0.3rem' }} /> Save Schedule
                </button>
                {quoteScheduleSaveMsg && <span style={{ fontSize: '0.85rem', color: quoteScheduleSaveMsg.startsWith('✅') ? 'var(--success)' : 'var(--danger)' }}>{quoteScheduleSaveMsg}</span>}
              </div>
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

        {activeTab === 'numerology' && (() => {
          const NUM_LABELS = {1:'1',2:'2',3:'3',4:'4',5:'5',6:'6',7:'7',8:'8',9:'9',11:'11 (Master)',22:'22 (Master)',33:'33 (Master)'};
          const ALL_NUMS = [1,2,3,4,5,6,7,8,9,11,22,33];

          const saveNumDesc = async (num, text) => {
            try {
              await axios.post(`${API_BASE}/numerology/numbers`, { num, description: text });
              setNumerologyNumbers(prev => ({ ...prev, [num]: text }));
              setNumerologyEditNum(null);
              setNumerologySaveMsg('✅ Saved!');
              setTimeout(() => setNumerologySaveMsg(''), 2000);
            } catch { setNumerologySaveMsg('❌ Failed'); }
          };

          const saveCombo = async (primary_num, secondary_num, text) => {
            try {
              await axios.post(`${API_BASE}/numerology/combos`, { primary_num, secondary_num, combo_desc: text });
              setNumerologyCombos(prev => {
                const filtered = prev.filter(c => !(c.primary_num === primary_num && c.secondary_num === secondary_num));
                return [...filtered, { primary_num, secondary_num, combo_desc: text }];
              });
              setNumerologyEditCombo(null);
              setNumerologySaveMsg('✅ Saved!');
              setTimeout(() => setNumerologySaveMsg(''), 2000);
            } catch { setNumerologySaveMsg('❌ Failed'); }
          };

          const getCombo = (p, s) => {
            const entry = numerologyCombos.find(c => c.primary_num === p && c.secondary_num === s);
            return entry ? entry.combo_desc : '';
          };

          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

              {/* Settings Card */}
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ margin: 0 }}>⚙️ Schedule & Channel</h3>
                  <button 
                    className="button" 
                    style={{ padding: '0.4rem 0.8rem', fontSize: '0.8rem' }}
                    onClick={async () => {
                      if (window.confirm("Seed default numerology meanings into the database? This won't overwrite existing entries.")) {
                        try {
                          await axios.post(`${API_BASE}/numerology/seed`);
                          setNumerologySaveMsg('✅ Seeded!');
                          // Refresh data
                          const [nRes, cRes] = await Promise.all([
                            axios.get(`${API_BASE}/numerology/numbers`),
                            axios.get(`${API_BASE}/numerology/combos`),
                          ]);
                          setNumerologyNumbers(nRes.data);
                          setNumerologyCombos(cRes.data);
                          setTimeout(() => setNumerologySaveMsg(''), 2000);
                        } catch { setNumerologySaveMsg('❌ Seed Failed'); }
                      }
                    }}
                  >
                    🌱 Seed Defaults
                  </button>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 2fr', gap: '1rem', marginBottom: '1rem' }}>
                  <div className="form-group">
                    <label className="label">Morning Hour (LA, 0-23)</label>
                    <input className="input" type="number" min="0" max="23"
                      value={numerologySettings.morning_hour}
                      onChange={e => setNumerologySettings(p => ({ ...p, morning_hour: parseInt(e.target.value) || 0 }))}
                    />
                    <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>Posts today's reading (default 7 = 7am)</p>
                  </div>
                  <div className="form-group">
                    <label className="label">Evening Hour (LA, 0-23)</label>
                    <input className="input" type="number" min="0" max="23"
                      value={numerologySettings.evening_hour}
                      onChange={e => setNumerologySettings(p => ({ ...p, evening_hour: parseInt(e.target.value) || 0 }))}
                    />
                    <p style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.2rem' }}>Posts tomorrow's preview (default 22 = 10pm)</p>
                  </div>
                  <div className="form-group">
                    <label className="label">Channel ID</label>
                    <select className="input"
                      value={numerologySettings.channel_id}
                      onChange={e => setNumerologySettings(p => ({ ...p, channel_id: e.target.value }))}
                    >
                      <option value="">(fallback: #forum)</option>
                      {Object.keys(channels).map(id => (
                        <option key={id} value={id}>#{channels[id].name}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                  <button className="btn btn-primary" onClick={async () => {
                    try {
                      await axios.post(`${API_BASE}/numerology/settings`, numerologySettings);
                      setNumerologySaveMsg('✅ Saved!');
                      setTimeout(() => setNumerologySaveMsg(''), 2000);
                    } catch { setNumerologySaveMsg('❌ Failed'); }
                  }}>
                    <Save size={14} style={{ marginRight: '0.3rem' }} /> Save Settings
                  </button>
                  {numerologySaveMsg && <span style={{ color: numerologySaveMsg.startsWith('✅') ? 'var(--success)' : 'var(--danger)', fontSize: '0.85rem' }}>{numerologySaveMsg}</span>}
                </div>
              </div>

              {/* Preview Card */}
              <div className="card">
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '1rem' }}>
                  <h3 style={{ margin: 0 }}>🔮 Live Preview (Today)</h3>
                  <button className="btn btn-primary" style={{ fontSize: '0.85rem' }}
                    disabled={numerologyPreviewLoading}
                    onClick={async () => {
                      setNumerologyPreviewLoading(true);
                      try {
                        const res = await axios.get(`${API_BASE}/numerology/preview`);
                        setNumerologyPreview(res.data);
                      } catch { alert('Preview failed'); }
                      setNumerologyPreviewLoading(false);
                    }}
                  >
                    {numerologyPreviewLoading ? '⏳ Loading...' : '▶ Generate Preview'}
                  </button>
                </div>
                {numerologyPreview && (
                  <div style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: '0.75rem', padding: '1rem' }}>
                    <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '0.5rem' }}>
                      📅 {numerologyPreview.date} — Primary: <strong>{numerologyPreview.primary_label}</strong> · Secondary: <strong>{numerologyPreview.secondary_label}</strong>
                    </p>
                    <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.82rem', color: 'var(--text-primary)', margin: 0, fontFamily: 'monospace' }}>{numerologyPreview.reading}</pre>
                  </div>
                )}
              </div>

              {/* Number Descriptions */}
              <div className="card">
                <h3 style={{ marginBottom: '0.5rem' }}>🔢 Number Descriptions</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>Set the forecast text for each numerology number. Click a row to edit.</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                  {ALL_NUMS.map(num => (
                    <div key={num} style={{ border: '1px solid rgba(255,255,255,0.07)', borderRadius: '0.5rem', overflow: 'hidden' }}>
                      <div
                        style={{ display: 'flex', alignItems: 'center', gap: '1rem', padding: '0.75rem 1rem', cursor: 'pointer', background: numerologyEditNum === num ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.02)' }}
                        onClick={() => {
                          if (numerologyEditNum === num) { setNumerologyEditNum(null); }
                          else { setNumerologyEditNum(num); setNumerologyEditText(numerologyNumbers[num] || ''); }
                        }}
                      >
                        <span style={{ fontWeight: '700', color: 'var(--accent)', minWidth: '80px' }}>{NUM_LABELS[num]}</span>
                        <span style={{ flex: 1, fontSize: '0.85rem', color: numerologyNumbers[num] ? 'var(--text-primary)' : 'var(--text-secondary)', fontStyle: numerologyNumbers[num] ? 'normal' : 'italic' }}>
                          {numerologyNumbers[num] ? numerologyNumbers[num].slice(0, 120) + (numerologyNumbers[num].length > 120 ? '…' : '') : '(no description yet — click to add)'}
                        </span>
                        <span style={{ color: 'var(--text-secondary)', fontSize: '0.75rem' }}>{numerologyEditNum === num ? '▲ close' : '▼ edit'}</span>
                      </div>
                      {numerologyEditNum === num && (
                        <div style={{ padding: '0.75rem 1rem', background: 'rgba(0,0,0,0.2)' }}>
                          <textarea
                            className="input"
                            style={{ width: '100%', minHeight: '100px', fontFamily: 'monospace', fontSize: '0.85rem' }}
                            value={numerologyEditText}
                            onChange={e => setNumerologyEditText(e.target.value)}
                            placeholder={`Full forecast text for number ${num}...`}
                          />
                          <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.5rem' }}>
                            <button className="btn btn-primary" style={{ fontSize: '0.8rem' }}
                              onClick={() => saveNumDesc(num, numerologyEditText)}>
                              <Save size={12} style={{ marginRight: '0.25rem' }} /> Save
                            </button>
                            <button className="btn" style={{ fontSize: '0.8rem' }}
                              onClick={() => setNumerologyEditNum(null)}>Cancel</button>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Combination Readings */}
              <div className="card">
                <h3 style={{ marginBottom: '0.5rem' }}>✨ Combination Readings</h3>
                <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>Set the combined advice for each primary + secondary number pair. Click a cell to edit.</p>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.8rem' }}>
                    <thead>
                      <tr>
                        <th style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.15)', textAlign: 'center', color: 'var(--text-secondary)' }}>P \ S→</th>
                        {ALL_NUMS.map(s => (
                          <th key={s} style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.1)', textAlign: 'center', minWidth: '60px' }}>{s}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {ALL_NUMS.map(p => (
                        <tr key={p}>
                          <td style={{ padding: '0.5rem', background: 'rgba(99,102,241,0.1)', fontWeight: '700', textAlign: 'center', color: 'var(--accent)' }}>{p}</td>
                          {ALL_NUMS.map(s => {
                            const combo = getCombo(p, s);
                            const isEditing = numerologyEditCombo && numerologyEditCombo.primary_num === p && numerologyEditCombo.secondary_num === s;
                            return (
                              <td key={s} style={{ padding: '0.25rem', verticalAlign: 'top', background: isEditing ? 'rgba(99,102,241,0.15)' : combo ? 'rgba(255,255,255,0.02)' : 'transparent' }}>
                                {isEditing ? (
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', minWidth: '200px' }}>
                                    <textarea
                                      className="input"
                                      style={{ width: '100%', minHeight: '80px', fontSize: '0.75rem', fontFamily: 'monospace' }}
                                      value={numerologyEditText}
                                      onChange={e => setNumerologyEditText(e.target.value)}
                                      autoFocus
                                    />
                                    <div style={{ display: 'flex', gap: '0.25rem' }}>
                                      <button className="btn btn-primary" style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                                        onClick={() => saveCombo(p, s, numerologyEditText)}>✓ Save</button>
                                      <button className="btn" style={{ fontSize: '0.7rem', padding: '0.2rem 0.5rem' }}
                                        onClick={() => setNumerologyEditCombo(null)}>✗</button>
                                    </div>
                                  </div>
                                ) : (
                                  <div
                                    onClick={() => { setNumerologyEditCombo({ primary_num: p, secondary_num: s }); setNumerologyEditText(combo); }}
                                    style={{ cursor: 'pointer', minHeight: '32px', padding: '0.25rem', borderRadius: '0.25rem', color: combo ? 'var(--text-primary)' : 'rgba(255,255,255,0.2)', fontSize: '0.72rem', lineHeight: 1.3 }}
                                    title={combo || 'Click to add'}
                                  >
                                    {combo ? combo.slice(0, 40) + (combo.length > 40 ? '…' : '') : '+'}
                                  </div>
                                )}
                              </td>
                            );
                          })}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <p style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: '0.75rem' }}>P = Primary (universal day), S = Secondary (day digits). Click any cell to add/edit.</p>
              </div>

            </div>
          );
        })()}

        {activeTab === 'admin' && (() => {
          const saveAdmin = async (patch) => {
            setAdminSaving(true);
            setAdminSaveMsg('');
            try {
              await axios.post(`${API_BASE}/admin-config`, patch);
              setAdminConfig(prev => ({ ...prev, ...patch }));
              setAdminSaveMsg('✅ Saved!');
              setTimeout(() => setAdminSaveMsg(''), 2500);
            } catch (err) {
              setAdminSaveMsg('❌ Save failed');
            }
            setAdminSaving(false);
          };

          const decks = [
            { id: 'thoth', label: 'Thoth', subtitle: 'Aleister Crowley', emoji: '🌑' },
            { id: 'rws', label: 'Rider-Waite-Smith', subtitle: 'Classic', emoji: '🌟' },
            { id: 'manara', label: 'Manara', subtitle: 'Erotic / Adult', emoji: '🔞' },
          ];

          return (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

              {/* Tarot Deck */}
              <div className="card">
                <h2 style={{ marginBottom: '0.25rem' }}>🃏 Tarot Deck</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                  Select which deck is used when members run <code>.pull</code>. Replaces the old <code>/tarot config</code> slash command.
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem' }}>
                  {decks.map(deck => {
                    const isActive = adminConfig.tarot_deck === deck.id;
                    return (
                      <div
                        key={deck.id}
                        onClick={() => saveAdmin({ tarot_deck: deck.id })}
                        style={{
                          cursor: 'pointer',
                          padding: '1.25rem',
                          borderRadius: '0.75rem',
                          border: isActive ? '2px solid var(--accent)' : '2px solid rgba(255,255,255,0.1)',
                          background: isActive ? 'rgba(99,102,241,0.15)' : 'rgba(255,255,255,0.02)',
                          textAlign: 'center',
                          transition: 'all 0.2s',
                          userSelect: 'none',
                        }}
                      >
                        <div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>{deck.emoji}</div>
                        <div style={{ fontWeight: 'bold', fontSize: '0.95rem' }}>{deck.label}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.25rem' }}>{deck.subtitle}</div>
                        {isActive && <div style={{ marginTop: '0.5rem', fontSize: '0.75rem', color: 'var(--accent)', fontWeight: 'bold' }}>✓ ACTIVE</div>}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* Economy + Yap Level */}
              <div className="card">
                <h2 style={{ marginBottom: '1.5rem' }}>⚙️ Bot Config</h2>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                  {/* Economy Toggle */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div>
                        <h4 style={{ margin: 0 }}>Economy</h4>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
                          Enable or disable the global economy system.
                        </p>
                      </div>
                      <div
                        className={`toggle ${adminConfig.economy_enabled ? 'active' : ''}`}
                        onClick={() => saveAdmin({ economy_enabled: !adminConfig.economy_enabled })}
                      >
                        <div className="toggle-handle"></div>
                      </div>
                    </div>
                  </div>
                  {/* Yap Level Toggle */}
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div>
                        <h4 style={{ margin: 0 }}>Yap Level</h4>
                        <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>
                          <strong>{adminConfig.yap_level === 'high' ? 'High' : 'Low'}</strong> — {adminConfig.yap_level === 'high' ? 'Detailed responses.' : 'Concise responses.'}
                        </p>
                      </div>
                      <div
                        className={`toggle ${adminConfig.yap_level === 'high' ? 'active' : ''}`}
                        onClick={() => saveAdmin({ yap_level: adminConfig.yap_level === 'high' ? 'low' : 'high' })}
                      >
                        <div className="toggle-handle"></div>
                      </div>
                    </div>
                  </div>
                </div>
                {adminSaveMsg && (
                  <div style={{ marginTop: '1rem', color: adminSaveMsg.startsWith('✅') ? 'var(--success)' : 'var(--danger)', fontSize: '0.9rem', fontWeight: 'bold' }}>
                    {adminSaveMsg}
                  </div>
                )}
              </div>

              {/* .key Command */}
              <div className="card">
                <h2 style={{ marginBottom: '0.25rem' }}>🔑 .key Command</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
                  Manage the image gallery for <code>.key</code> and how many times it sends per use. You can now use <strong>Discord Sticker IDs</strong> as well as image URLs.
                </p>

                {/* Gallery */}
                <h4 style={{ marginBottom: '0.75rem' }}>Images & Stickers (click to activate, up to 10)</h4>
                {keySettings.images.length === 0 ? (
                  <p style={{ color: 'var(--text-secondary)', fontSize: '0.85rem', marginBottom: '1rem' }}>No images saved yet. Add one below.</p>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))', gap: '0.75rem', marginBottom: '1.5rem' }}>
                    {keySettings.images.map(img => (
                      <div key={img.id} style={{
                        position: 'relative',
                        borderRadius: '0.6rem',
                        border: img.is_active ? '2px solid var(--accent)' : '2px solid rgba(255,255,255,0.1)',
                        overflow: 'hidden',
                        cursor: 'pointer',
                        background: '#111',
                      }}>
                        {/* Click the whole card to activate */}
                        <div
                          onClick={async () => {
                            await axios.post(`${API_BASE}/key-settings/images/${img.id}/activate`);
                            const ks = (await axios.get(`${API_BASE}/key-settings`)).data;
                            setKeySettings(ks);
                          }}
                          style={{ display: 'block', width: '100%', minHeight: '100px' }}
                        >
                          {/^\d+$/.test(img.url.trim()) ? (
                            /* Sticker entry — show badge instead of broken img */
                            <div style={{ width: '100%', height: '100px', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', background: 'rgba(99,102,241,0.1)', gap: '0.4rem' }}>
                              <span style={{ fontSize: '1.8rem' }}>🎭</span>
                              <span style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', fontFamily: 'monospace' }}>ID: {img.url.trim()}</span>
                            </div>
                          ) : (
                            <img
                              src={img.url} alt={img.label || 'key image'}
                              style={{ width: '100%', height: '100px', objectFit: 'cover', display: 'block' }}
                              onError={e => { e.target.style.display='none'; }}
                            />
                          )}
                        </div>
                        {img.is_active && (
                          <div style={{ position: 'absolute', top: 4, left: 4, background: 'var(--accent)', borderRadius: '0.3rem', padding: '2px 6px', fontSize: '0.65rem', fontWeight: 'bold' }}>ACTIVE</div>
                        )}
                        <button
                          onClick={async (e) => {
                            e.stopPropagation();
                            await axios.delete(`${API_BASE}/key-settings/images/${img.id}`);
                            const ks = (await axios.get(`${API_BASE}/key-settings`)).data;
                            setKeySettings(ks);
                          }}
                          style={{ position: 'absolute', top: 4, right: 4, background: 'rgba(200,50,50,0.85)', border: 'none', color: '#fff', borderRadius: '50%', width: 22, height: 22, cursor: 'pointer', fontSize: '0.7rem', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
                        >✕</button>
                        {img.label && <div style={{ padding: '4px 6px', fontSize: '0.7rem', color: 'var(--text-secondary)', background: 'rgba(0,0,0,0.6)' }}>{img.label}</div>}
                      </div>
                    ))}
                  </div>
                )}

                {/* Add Image / Sticker */}
                <h4 style={{ marginBottom: '0.5rem' }}>Add Image or Sticker</h4>
                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
                  <input
                    className="input"
                    placeholder="Image URL (https://...) or Sticker ID (numeric)"
                    value={keyImageInput}
                    onChange={e => setKeyImageInput(e.target.value)}
                    style={{ flex: '2 1 200px' }}
                  />
                  <input
                    className="input"
                    placeholder="Label (optional)"
                    value={keyLabelInput}
                    onChange={e => setKeyLabelInput(e.target.value)}
                    style={{ flex: '1 1 120px' }}
                  />
                  <button className="btn btn-primary" style={{ padding: '0.5rem 1.2rem' }} onClick={async () => {
                    if (!keyImageInput.trim()) return;
                    await axios.post(`${API_BASE}/key-settings/images`, { url: keyImageInput.trim(), label: keyLabelInput.trim() });
                    setKeyImageInput(''); setKeyLabelInput('');
                    const ks = (await axios.get(`${API_BASE}/key-settings`)).data;
                    setKeySettings(ks);
                  }}>Add</button>
                </div>

                {/* Send Counts */}
                <h4 style={{ marginBottom: '0.75rem' }}>Send Count Per Use</h4>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1rem' }}>
                  <div>
                    <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.3rem' }}>Users & Capos</label>
                    <input className="input" type="number" min="1" max="20" value={keySendUser} onChange={e => setKeySendUser(parseInt(e.target.value) || 1)} style={{ width: '100%' }} />
                  </div>
                  <div>
                    <label style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', display: 'block', marginBottom: '0.3rem' }}>Admins</label>
                    <input className="input" type="number" min="1" max="20" value={keySendAdmin} onChange={e => setKeySendAdmin(parseInt(e.target.value) || 1)} style={{ width: '100%' }} />
                  </div>
                </div>
                <button className="btn btn-primary" style={{ padding: '0.5rem 1.5rem' }} onClick={async () => {
                  await axios.post(`${API_BASE}/key-settings/config`, { send_count_user: keySendUser, send_count_admin: keySendAdmin });
                  setKeySaveMsg('✅ Saved!');
                  setTimeout(() => setKeySaveMsg(''), 2500);
                }}>Save Send Counts</button>
                {keySaveMsg && <span style={{ marginLeft: '1rem', color: 'var(--success)', fontWeight: 'bold', fontSize: '0.9rem' }}>{keySaveMsg}</span>}
              </div>

            </div>
          );
        })()}

        {activeTab === 'shop' && (() => {
          const savePrice = async (item_key, price) => {
            try {
              await axios.post(`${API_BASE}/shop/items`, { item_key, price: parseInt(price) });
              setShopItems(prev => prev.map(item => item.key === item_key ? { ...item, current_price: parseInt(price) } : item));
              setShopSaveMsg('✅ Saved!');
              setTimeout(() => setShopSaveMsg(''), 2000);
            } catch { setShopSaveMsg('❌ Error'); }
          };

          return (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h2 style={{ margin: 0 }}>🛒 Shop Pricing</h2>
                {shopSaveMsg && <span style={{ color: 'var(--accent-color)', fontWeight: 'bold' }}>{shopSaveMsg}</span>}
              </div>
              
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left' }}>Item</th>
                      <th style={{ textAlign: 'left' }}>Description</th>
                      <th style={{ textAlign: 'center', width: '120px' }}>Base Price</th>
                      <th style={{ textAlign: 'center', width: '150px' }}>Current Price</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shopItems.map(item => (
                      <tr key={item.key}>
                        <td style={{ fontWeight: '600', color: 'var(--accent-color)' }}>{item.name}</td>
                        <td style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{item.description}</td>
                        <td style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>{item.base_price}</td>
                        <td style={{ textAlign: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                            <input 
                              className="input"
                              type="number"
                              style={{ width: '100px', textAlign: 'center' }}
                              defaultValue={item.current_price}
                              onBlur={(e) => {
                                if (parseInt(e.target.value) !== item.current_price) {
                                  savePrice(item.key, e.target.value);
                                }
                              }}
                            />
                            <span style={{ color: 'var(--accent-color)' }}>💎</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p style={{ marginTop: '1rem', fontSize: '0.85rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
                * Prices are auto-saved when you click out of the field.
              </p>
            </div>
          );
        })()}

        {activeTab === 'misc' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            <div className="card animate-in" style={{ borderColor: 'var(--accent)', borderStyle: 'dashed' }}>
              <h2 style={{ marginBottom: '0.25rem' }}>🏦 Deposit Settings</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>Configure the address and instructions users receive via DM when they type <code>.deposit</code> in Discord.</p>
              
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <textarea
                  className="input"
                  style={{ minHeight: '100px', fontFamily: 'monospace', fontSize: '0.9rem' }}
                  placeholder="e.g. BTC: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa ..."
                  value={depositInfo}
                  onChange={(e) => setDepositInfo(e.target.value)}
                  onBlur={saveDepositInfo}
                />
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Auto-saves on blur</span>
                  {depositSaveMsg && (
                    <span style={{ 
                      color: depositSaveMsg.includes('✅') ? '#22c55e' : '#ef4444',
                      fontSize: '0.85rem',
                      fontWeight: 'bold'
                    }}>
                      {depositSaveMsg}
                    </span>
                  )}
                </div>
              </div>
            </div>

            <div className="card animate-in" style={{ borderColor: 'var(--accent)', borderStyle: 'solid' }}>
              <h2 style={{ marginBottom: '0.25rem' }}>📢 Bulletin Configuration</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>Configure the automated daily channel and maintenance tasks.</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem' }}>
                <div>
                  <label className="label">Bulletin Channel</label>
                  <select
                    className="input"
                    value={bulletinSettings.channel_id || ''}
                    onChange={(e) => setBulletinSettings({ ...bulletinSettings, channel_id: e.target.value })}
                  >
                    <option value="">-- Disabled --</option>
                    {Object.entries(channels).map(([id, ch]) => (
                      <option key={id} value={id}>#{ch.name}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="label">Manual Action</label>
                  <button 
                    className="btn btn-secondary" 
                    onClick={handleTriggerTarot} 
                    disabled={saving}
                    style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                  >
                    <Wind size={16} /> Draw Daily Tarot
                  </button>
                </div>

                <div>
                  <label className="label">Purge Schedule</label>
                  <select
                    className="input"
                    value={bulletinSettings.weekly_purge_enabled === 0 ? 'disabled' : (bulletinSettings.purge_interval || 'weekly')}
                    onChange={(e) => {
                      const val = e.target.value;
                      if (val === 'disabled') {
                        setBulletinSettings({ ...bulletinSettings, weekly_purge_enabled: 0 });
                      } else {
                        setBulletinSettings({ ...bulletinSettings, weekly_purge_enabled: 1, purge_interval: val });
                      }
                    }}
                  >
                    <option value="disabled">-- Disabled --</option>
                    <option value="daily">Daily (Midnight PT)</option>
                    <option value="weekly">Weekly (Sun 11:59PM PT)</option>
                  </select>
                </div>
              </div>

              <div style={{ marginTop: '1.5rem', display: 'flex', justifyContent: 'flex-end', alignItems: 'center', gap: '1rem' }}>
                {bulletinSaveMsg && (
                  <span style={{ color: bulletinSaveMsg.includes('Error') ? '#ef4444' : '#22c55e', fontSize: '0.85rem' }}>
                    {bulletinSaveMsg}
                  </span>
                )}
                <button className="btn btn-primary" onClick={handleSaveBulletinSettings} disabled={saving}>
                  <Save size={16} /> Save Bulletin Settings
                </button>
              </div>
            </div>

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

            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>📊 Command Usage Statistics</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Most used commands in the bot (prefix and slash).</p>
              
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
                {commandStats.length > 0 ? (
                  commandStats.map((stat, i) => (
                    <div key={stat.name} style={{ 
                      background: 'rgba(255,255,255,0.02)', 
                      padding: '0.875rem', 
                      borderRadius: '0.75rem', 
                      border: '1px solid rgba(255,255,255,0.05)',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center'
                    }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <span style={{ color: i < 3 ? 'var(--accent)' : 'var(--text-muted)', fontWeight: 'bold', fontSize: '0.8rem' }}>#{i+1}</span>
                        <code style={{ fontSize: '0.9rem' }}>{stat.name.startsWith('/') ? stat.name : `.${stat.name}`}</code>
                      </div>
                      <span style={{ fontWeight: '700', color: 'var(--text-primary)' }}>{stat.count.toLocaleString()}</span>
                    </div>
                  ))
                ) : (
                  <p style={{ color: 'var(--text-muted)', gridColumn: '1 / -1' }}>No command data recorded yet.</p>
                )}
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>🏆 Hall of Fame</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Configure the starboard system — which channel, how many reactions, and which emojis to track.</p>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '1.5rem' }}>
                {/* HOF Channel */}
                <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <label className="label" style={{ fontWeight: 'bold' }}>HOF Channel</label>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <select
                      className="input"
                      style={{ flex: 1 }}
                      value={hofSettings.channel_id || ''}
                      onChange={(e) => setHofSettings({ ...hofSettings, channel_id: e.target.value })}
                    >
                      <option value="">-- Not Set --</option>
                      {Object.entries(channels).map(([id, channelObj]) => (
                        <option key={id} value={id}>#{channelObj.name}</option>
                      ))}
                    </select>
                    <button
                      className="btn btn-primary"
                      title="Save HOF Channel"
                      onClick={async (e) => {
                        const parent = e.currentTarget.parentElement;
                        try {
                          await axios.post(`${API_BASE}/hof-settings`, { channel_id: hofSettings.channel_id || '' });
                          let indicator = parent.querySelector('.save-indicator');
                          if (!indicator) { indicator = document.createElement('span'); indicator.className = 'save-indicator'; indicator.style.cssText = 'color: #22c55e; font-weight: bold; font-size: 1.1rem; transition: opacity 0.3s;'; parent.appendChild(indicator); }
                          indicator.textContent = '✓'; indicator.style.opacity = '1';
                          setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
                        } catch (err) {
                          let indicator = parent.querySelector('.save-indicator');
                          if (!indicator) { indicator = document.createElement('span'); indicator.className = 'save-indicator'; indicator.style.cssText = 'color: #ef4444; font-weight: bold; transition: opacity 0.3s;'; parent.appendChild(indicator); }
                          indicator.textContent = '✗'; indicator.style.opacity = '1';
                          setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
                        }
                      }}
                    >
                      <Save size={14} />
                    </button>
                  </div>
                </div>

                {/* Threshold */}
                <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                  <label className="label" style={{ fontWeight: 'bold' }}>Reaction Threshold</label>
                  <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                    <input
                      className="input"
                      type="number"
                      min="1"
                      style={{ flex: 1 }}
                      value={hofSettings.threshold}
                      onChange={(e) => setHofSettings({ ...hofSettings, threshold: parseInt(e.target.value) || 1 })}
                    />
                    <button
                      className="btn btn-primary"
                      title="Save Threshold"
                      onClick={async (e) => {
                        const parent = e.currentTarget.parentElement;
                        try {
                          await axios.post(`${API_BASE}/hof-settings`, { threshold: hofSettings.threshold });
                          let indicator = parent.querySelector('.save-indicator');
                          if (!indicator) { indicator = document.createElement('span'); indicator.className = 'save-indicator'; indicator.style.cssText = 'color: #22c55e; font-weight: bold; font-size: 1.1rem; transition: opacity 0.3s;'; parent.appendChild(indicator); }
                          indicator.textContent = '✓'; indicator.style.opacity = '1';
                          setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
                        } catch (err) {
                          let indicator = parent.querySelector('.save-indicator');
                          if (!indicator) { indicator = document.createElement('span'); indicator.className = 'save-indicator'; indicator.style.cssText = 'color: #ef4444; font-weight: bold; transition: opacity 0.3s;'; parent.appendChild(indicator); }
                          indicator.textContent = '✗'; indicator.style.opacity = '1';
                          setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
                        }
                      }}
                    >
                      <Save size={14} />
                    </button>
                  </div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>Reactions needed to enter the Hall of Fame</p>
                </div>
              </div>

              {/* Tracked Emojis */}
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.05)', marginBottom: '1.5rem' }}>
                <label className="label" style={{ fontWeight: 'bold' }}>Tracked Emojis</label>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>Space-separated. Supports unicode emojis (⭐ 🔥) and custom Discord emojis (paste the full format like <code>&lt;:name:123456&gt;</code>).</p>
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <input
                    className="input"
                    style={{ flex: 1, fontFamily: 'monospace' }}
                    value={hofEmojiInput}
                    onChange={(e) => setHofEmojiInput(e.target.value)}
                    placeholder="⭐ 🔥 💯 <:custom:123456789>"
                  />
                  <button
                    className="btn btn-primary"
                    title="Save Emojis"
                    onClick={async (e) => {
                      const parent = e.currentTarget.parentElement;
                      const parsed = hofEmojiInput.trim().split(/\s+/).filter(Boolean);
                      if (parsed.length === 0) { alert('Enter at least one emoji.'); return; }
                      try {
                        await axios.post(`${API_BASE}/hof-settings`, { emojis: parsed });
                        setHofSettings(prev => ({ ...prev, emojis: parsed }));
                        let indicator = parent.querySelector('.save-indicator');
                        if (!indicator) { indicator = document.createElement('span'); indicator.className = 'save-indicator'; indicator.style.cssText = 'color: #22c55e; font-weight: bold; font-size: 1.1rem; transition: opacity 0.3s;'; parent.appendChild(indicator); }
                        indicator.textContent = '✓'; indicator.style.opacity = '1';
                        setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
                      } catch (err) {
                        let indicator = parent.querySelector('.save-indicator');
                        if (!indicator) { indicator = document.createElement('span'); indicator.className = 'save-indicator'; indicator.style.cssText = 'color: #ef4444; font-weight: bold; transition: opacity 0.3s;'; parent.appendChild(indicator); }
                        indicator.textContent = '✗'; indicator.style.opacity = '1';
                        setTimeout(() => { indicator.style.opacity = '0'; }, 2000);
                      }
                    }}
                  >
                    <Save size={14} />
                  </button>
                </div>
                {hofSettings.emojis && hofSettings.emojis.length > 0 && (
                  <div style={{ marginTop: '0.75rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {hofSettings.emojis.map((e, i) => (
                      <span key={i} style={{ padding: '0.25rem 0.6rem', background: 'rgba(99,102,241,0.15)', borderRadius: '0.5rem', fontSize: '0.9rem' }}>{e}</span>
                    ))}
                  </div>
                )}
              </div>

              {/* Ignored Channels */}
              <div style={{ background: 'rgba(255,255,255,0.02)', padding: '1rem', borderRadius: '0.5rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                <label className="label" style={{ fontWeight: 'bold' }}>Ignored Channels</label>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>Reactions in these channels will NOT count toward HOF.</p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem' }}>
                  {Object.entries(channels).map(([id, channelObj]) => {
                    const isIgnored = (hofSettings.ignored_channels || []).includes(id);
                    return (
                      <label key={id} style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer' }}>
                        <input
                          type="checkbox"
                          checked={isIgnored}
                          onChange={async (e) => {
                            const newList = e.target.checked
                              ? [...(hofSettings.ignored_channels || []), id]
                              : (hofSettings.ignored_channels || []).filter(c => c !== id);
                            setHofSettings(prev => ({ ...prev, ignored_channels: newList }));
                            try { await axios.post(`${API_BASE}/hof-settings`, { ignored_channels: newList }); } catch (err) { alert('Save failed'); }
                          }}
                          style={{ width: '14px', height: '14px' }}
                        />
                        #{channelObj.name}
                      </label>
                    );
                  })}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
