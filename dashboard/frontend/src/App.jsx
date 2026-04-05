import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Home, Sparkles, Gift, Layers, Database, 
  Settings, TrendingUp, Users, Trophy, Trash2, Plus, Save, Download, RefreshCw, Bell, Info, Mail, CreditCard, BookOpen, MessageCircle, Send, Hash, Wind, Palette, Shield, Zap, CircleDollarSign, Terminal, ShoppingBag, Cpu, Key
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

const ALL_NUMS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 22, 33];
const NUM_LABELS = {
  1: '1 (Sun)', 2: '2 (Moon)', 3: '3 (Jupiter)', 4: '4 (Rahu)', 5: '5 (Mercury)',
  6: '6 (Venus)', 7: '7 (Ketu)', 8: '8 (Saturn)', 9: '9 (Mars)',
  11: '11 (Master)', 22: '22 (Master)', 33: '33 (Master)'
};

function App() {
  const [activeTab, setActiveTab] = useState('overview');
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
  const [colorRoles, setColorRoles] = useState([]);
  const [colorRoleSaveMsg, setColorRoleSaveMsg] = useState(null);
  const [newColorRole, setNewColorRole] = useState({ name: '', role_id: '', vote_threshold: 7, duration_days: 2 });
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
  const [syncing, setSyncing] = useState(false);


  useEffect(() => {
    console.log('[Dashboard] API_BASE identified as:', API_BASE);
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

  // --- GLOBAL FETCHING logic ---
  const fetchColorRoles = async () => {
    try {
      const response = await axios.get(`${API_BASE}/bulletin/color-roles`);
      console.log('[Dashboard] Color Roles fetched:', response.data);
      setColorRoles(Array.isArray(response.data) ? response.data : []);
    } catch (err) {
      console.error('Failed to fetch color roles:', err);
    }
  };

  const fetchContentData = async () => {
    try {
      const [bRes, qdRes, qdsRes, qRes, qsRes, nsRes, nnRes, ncRes] = await Promise.all([
        axios.get(`${API_BASE}/bulletin/settings`),
        axios.get(`${API_BASE}/quote-drops`),
        axios.get(`${API_BASE}/quote-drops/settings`),
        axios.get(`${API_BASE}/quotes`),
        axios.get(`${API_BASE}/quotes/schedule`),
        axios.get(`${API_BASE}/numerology/settings`),
        axios.get(`${API_BASE}/numerology/numbers`),
        axios.get(`${API_BASE}/numerology/combos`),
      ]);
      setBulletinSettings(bRes.data);
      setQuoteDrops(qdRes.data);
      setQuoteDropsEnabled(qdsRes.data.enabled);
      setQuoteDropsInterval(qdsRes.data.interval_hours);
      setDailyQuotes(qRes.data);
      setQuoteSchedule(qsRes.data);
      setNumerologySettings(nsRes.data);
      setNumerologyNumbers(nnRes.data);
      setNumerologyCombos(ncRes.data);
    } catch (err) {
      console.error('Failed to fetch content data:', err);
    }
  };

  useEffect(() => {
    if (['bulletins', 'quotedrops', 'quotes'].includes(activeTab)) {
      fetchContentData();
    }
    if (activeTab === 'roles') {
      fetchColorRoles();
    }
    if (activeTab === 'economy') {
      Promise.all([
        axios.get(`${API_BASE}/shop/items`),
        axios.get(`${API_BASE}/deposit-info`),
      ]).then(([sRes, dRes]) => {
        setShopItems(sRes.data);
        setDepositInfo(dRes.data.deposit_info);
      }).catch(err => console.error('Failed to fetch economy data:', err));
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

  // --- RESTORED MISSING HELPER FUNCTIONS ---
  const savePrice = async (key, price) => {
    try {
      await axios.post(`${API_BASE}/shop/items`, { item_key: key, price: parseInt(price) });
      setShopSaveMsg('✅ Price updated!');
      setTimeout(() => setShopSaveMsg(null), 3000);
    } catch { 
      setShopSaveMsg('❌ Error saving price');
      setTimeout(() => setShopSaveMsg(null), 3000);
    }
  };

  const saveNumDesc = async (num, description) => {
    try {
      await axios.post(`${API_BASE}/numerology/numbers`, { num: parseInt(num), description });
      setNumerologyNumbers(prev => ({ ...prev, [num]: description }));
      alert('Forecast saved!');
    } catch { alert('Failed to save forecast'); }
  };

  const addQuoteDrop = async () => {
    if (!newQuoteDrop.trim()) return;
    try {
      await axios.post(`${API_BASE}/quote-drops`, { quote: newQuoteDrop, added_by: 'Dashboard' });
      setNewQuoteDrop('');
      fetchContentData();
    } catch { alert('Failed to add quote'); }
  };

  const deleteQuoteDrop = async (id) => {
    try {
      await axios.delete(`${API_BASE}/quote-drops/${id}`);
      fetchContentData();
    } catch { alert('Delete failed'); }
  };

  const triggerQuoteDrop = async () => {
    try {
      await axios.post(`${API_BASE}/quote-drops/trigger`);
      setSendSuccess('quote-drop');
      setTimeout(() => setSendSuccess(null), 3000);
    } catch { alert('Trigger failed'); }
  };

  const sendQuoteDrop = async (id) => {
    try {
      await axios.post(`${API_BASE}/quote-drops/${id}/send`);
      setBulletinSaveMsg('🚀 Quote drop triggered!');
      setTimeout(() => setBulletinSaveMsg(''), 3000);
    } catch (err) {
      console.error('Failed to send quote:', err);
      setBulletinSaveMsg('❌ Error sending quote.');
    }
  };

  const addDailyQuote = async () => {
    if (!newDailyQuote.trim()) return;
    try {
      await axios.post(`${API_BASE}/quotes`, { quote: newDailyQuote });
      setNewDailyQuote('');
      fetchContentData();
    } catch { alert('Failed to add quote'); }
  };

  const deleteDailyQuote = async (id) => {
    try {
      await axios.delete(`${API_BASE}/quotes/${id}`);
      fetchContentData();
    } catch { alert('Delete failed'); }
  };

  const triggerDailyQuote = async () => {
    try {
      await axios.post(`${API_BASE}/quotes/trigger-daily`);
      setSendSuccess('daily-quote');
      setTimeout(() => setSendSuccess(null), 3000);
    } catch { alert('Trigger failed'); }
  };

  const saveQuoteSchedule = async () => {
    try {
      await axios.post(`${API_BASE}/quotes/schedule`, quoteSchedule);
      setQuoteScheduleSaveMsg('✅ Schedule saved!');
      setTimeout(() => setQuoteScheduleSaveMsg(''), 3000);
    } catch { alert('Failed to save schedule'); }
  };

  const saveQuoteDropConfig = async () => {
    try {
      await axios.post(`${API_BASE}/quote-drops/config`, {
        enabled: quoteDropsEnabled,
        interval_hours: quoteDropsInterval
      });
      alert('Quote drop configuration saved!');
    } catch { alert('Failed to save configuration'); }
  };

  const saveAdmin = async (updates) => {
    try {
      await axios.post(`${API_BASE}/admin-config`, updates);
      setAdminConfig(prev => ({ ...prev, ...updates }));
    } catch { alert('Failed to save admin config'); }
  };

  const saveBulletinSettings = async () => {
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
    { id: 'overview', label: 'Overview', icon: Home, category: 'General' },
    { id: 'progression', label: 'Progression & XP', icon: TrendingUp, category: 'Community' },
    { id: 'roles', label: 'Colour Roles', icon: Palette, category: 'Community' },
    { id: 'social', label: 'Social & HoF', icon: Users, category: 'Community' },
    { id: 'keygallery', label: 'Key Gallery', icon: Key, category: 'Community' },
    { id: 'bulletins', label: 'Bulletins & Numerology', icon: Bell, category: 'Content' },
    { id: 'quotedrops', label: 'Quote Drops', icon: Zap, category: 'Content' },
    { id: 'quotes', label: 'Daily Quotes', icon: Sparkles, category: 'Content' },
    { id: 'moderation', label: 'Moderation & Access', icon: Shield, category: 'Management' },
    { id: 'economy', label: 'Economy & Shop', icon: CircleDollarSign, category: 'Management' },
    { id: 'system', label: 'System & Technical', icon: Cpu, category: 'Management' },
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
          <h1>{navItems.find(i => i.id === activeTab)?.label || 'Apeiron'}</h1>
          <p>{{
            overview: "Server stats and leaderboard at a glance.",
            progression: "Configure XP curves, rewards, and multipliers.",
            social: "Customize level-up messages and rank cards.",
            roles: "Manage server-funded vanity color roles.",
            bulletins: "Daily automated TC posts and purge schedules.",
            quotedrops: "Configure automated random quote drops.",
            quotes: "Philosophical quotes posted at sunrise and sunset.",
            moderation: "Access control, starboards, and color roles.",
            economy: "Shop items, deposit info, and currency.",
            system: "Bot persona and database maintenance."
          }[activeTab] || 'Configuration and management dashboard.'}</p>
        </header>

        {activeTab === 'overview' && (
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

            <div className="grid" style={{ gridTemplateColumns: '1.5fr 1fr', gap: '2rem', marginBottom: '2rem' }}>
              <div className="card">
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
              </div>

              <div className="card">
                <h2 style={{ marginBottom: '1.5rem' }}>📊 Most Used Commands</h2>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {commandStats.length > 0 ? (
                    commandStats.slice(0, 10).map((stat, i) => (
                      <div key={stat.name} style={{ 
                        background: 'rgba(255,255,255,0.02)', 
                        padding: '0.75rem 1rem', 
                        borderRadius: '0.75rem', 
                        border: '1px solid rgba(255,255,255,0.05)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                          <span style={{ color: i < 3 ? 'var(--accent)' : 'var(--text-muted)', fontWeight: 'bold', fontSize: '0.8rem' }}>#{i+1}</span>
                          <code style={{ fontSize: '0.85rem' }}>{stat.name.startsWith('/') ? stat.name : `.${stat.name}`}</code>
                        </div>
                        <span style={{ fontWeight: '700', color: 'var(--text-primary)', fontSize: '0.9rem' }}>{stat.count.toLocaleString()}</span>
                      </div>
                    ))
                  ) : (
                    <p style={{ color: 'var(--text-muted)' }}>No command data recorded yet.</p>
                  )}
                </div>
              </div>
            </div>
          </>
        )}

        {activeTab === 'progression' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* XP Gain Section */}
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

            {/* Reward Roles Section */}
            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Level Rewards</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Automatically give roles to members when they reach certain levels.</p>

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
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Configure how the bot syncs member roles.</p>

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
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>If members should be able to manually sync their roles</p>
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
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>Displays a warning in /rank if roles aren't synced</p>
                  <div
                    className={`toggle ${pendingSettings.reward_sync_warning !== '0' ? 'active' : ''}`}
                    onClick={() => updateSetting('reward_sync_warning', pendingSettings.reward_sync_warning === '0' ? '1' : '0')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
                <div>
                  <h4 style={{ marginBottom: '0.25rem' }}>Advanced: Exclude roles</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>Prevent certain roles from being managed by the bot.</p>
                  <div
                    className={`toggle ${pendingSettings.reward_exclude_enabled === '1' ? 'active' : ''}`}
                    onClick={() => updateSetting('reward_exclude_enabled', pendingSettings.reward_exclude_enabled === '1' ? '0' : '1')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
              </div>
            </div>

            {/* Multipliers Section */}
            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>XP Multipliers</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Boost XP rates for specific roles or channels.</p>
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
            </div>
          </div>
        )}

        {activeTab === 'social' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            {/* Notifications Section */}
            <div className="card">
              <h2 style={{ marginBottom: '0.5rem' }}>Level Up Notifications</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Customize the messages sent when members level up.</p>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem', marginBottom: '1.5rem' }}>
                <div>
                  <h4 style={{ margin: 0 }}>Enable Notifications</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>Send a message or DM whenever anyone levels up.</p>
                </div>
                <div
                  className={`toggle ${pendingSettings.lvl_msg_enabled === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('lvl_msg_enabled', pendingSettings.lvl_msg_enabled === '1' ? '0' : '1')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>

              <div className="form-group">
                <label className="label">Message Template</label>
                <textarea
                  className="input"
                  style={{ width: '100%', minHeight: '100px', fontFamily: 'monospace', fontSize: '0.9rem' }}
                  value={pendingSettings.lvl_msg_template || ''}
                  onChange={(e) => setPendingSettings({ ...pendingSettings, lvl_msg_template: e.target.value })}
                  onBlur={(e) => updateSetting('lvl_msg_template', e.target.value)}
                />
              </div>

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                <div>
                  <label className="label">Variables</label>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    {['XP', 'Member', 'Server'].map(v => (
                      <span key={v} className="badge" style={{ background: 'rgba(255,255,255,0.05)' }} title={`[[${v.toUpperCase()}]]`}>{v}</span>
                    ))}
                  </div>
                </div>
                <div>
                  <label className="label">Delivery Channel</label>
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
                  <h4 style={{ margin: 0 }}>Embed Mode</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>Send a fancy embed instead of a normal message.</p>
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
              <h2 style={{ marginBottom: '1rem' }}>Notification Interval</h2>
              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
                <div className="form-group">
                  <label className="label">Send Every X Levels</label>
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
                  <label className="label">Stop Multiples After Level</label>
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
              <div style={{ marginTop: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <h4 style={{ margin: 0 }}>Reward Roles Only</h4>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.25rem 0 0 0' }}>Only notify when obtaining a new reward role.</p>
                </div>
                <div
                  className={`toggle ${pendingSettings.lvl_msg_reward_only === '1' ? 'active' : ''}`}
                  onClick={() => updateSetting('lvl_msg_reward_only', pendingSettings.lvl_msg_reward_only === '1' ? '0' : '1')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>Rank Cards</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Tweak the details and behavior of member rank cards.</p>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem' }}>
                <div>
                  <h3 style={{ margin: 0 }}>Enable /rank command</h3>
                  <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', margin: '0.35rem 0 0 0' }}>Allows members to check their progress.</p>
                </div>
                <div
                  className={`toggle ${pendingSettings.rank_enabled !== '0' ? 'active' : ''}`}
                  onClick={() => updateSetting('rank_enabled', pendingSettings.rank_enabled === '0' ? '1' : '0')}
                >
                  <div className="toggle-handle"></div>
                </div>
              </div>

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '2rem' }}>
                <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <h4 style={{ marginBottom: '0.4rem' }}>Hide Cooldown</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Hide the time until next XP gain.</p>
                  <div
                    className={`toggle ${pendingSettings.rank_hide_cooldown === '1' ? 'active' : ''}`}
                    onClick={() => updateSetting('rank_hide_cooldown', pendingSettings.rank_hide_cooldown === '1' ? '0' : '1')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
                <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <h4 style={{ marginBottom: '0.4rem' }}>Hide Multipliers</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Hide role/channel multipliers index.</p>
                  <div
                    className={`toggle ${pendingSettings.rank_hide_multipliers === '1' ? 'active' : ''}`}
                    onClick={() => updateSetting('rank_hide_multipliers', pendingSettings.rank_hide_multipliers === '1' ? '0' : '1')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
                <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <h4 style={{ marginBottom: '0.4rem' }}>Force Ephemeral</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Make /rank visible only to the user.</p>
                  <div
                    className={`toggle ${pendingSettings.rank_force_hidden === '1' ? 'active' : ''}`}
                    onClick={() => updateSetting('rank_force_hidden', pendingSettings.rank_force_hidden === '1' ? '0' : '1')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
                <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <h4 style={{ marginBottom: '0.4rem' }}>Relative XP Mode</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Show progress toward next level (e.g. 100/500).</p>
                  <div
                    className={`toggle ${pendingSettings.rank_relative_xp !== '0' ? 'active' : ''}`}
                    onClick={() => updateSetting('rank_relative_xp', pendingSettings.rank_relative_xp === '0' ? '1' : '0')}
                  >
                    <div className="toggle-handle"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
        {activeTab === 'bulletins' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="grid" style={{ gridTemplateColumns: '1.5fr 1fr', gap: '2rem' }}>
              <div className="card">
                <h2 style={{ marginBottom: '0.25rem' }}>📢 Bulletins</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Daily automated posts and purge schedules.</p>
                
                <div className="form-group">
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

                <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                  <div className="form-group">
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
                      <option value="disabled">Never Purge</option>
                      <option value="daily">Daily at Midnight</option>
                      <option value="weekly">Weekly (Monday)</option>
                    </select>
                  </div>
                </div>

                <div style={{ marginTop: '1.5rem', display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                  <button className="btn btn-primary" onClick={saveBulletinSettings}>Save Bulletin</button>
                  <button className="btn" style={{ background: 'rgba(255,255,255,0.05)' }} onClick={handleTriggerTarot}>
                    <Wind size={16} /> Draw Tarot
                  </button>
                </div>
                {bulletinSaveMsg && <p style={{ marginTop: '0.75rem', color: bulletinSaveMsg.includes('✅') ? 'var(--success)' : 'var(--danger)', fontSize: '0.85rem' }}>{bulletinSaveMsg}</p>}
              </div>

              <div className="card">
                <h3 style={{ marginBottom: '1rem' }}>🃏 Tarot Deck</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {[
                    { id: 'thoth', label: 'Thoth', sub: 'Crowley', emoji: '🌑' },
                    { id: 'rws', label: 'Rider-Waite', sub: 'Classic', emoji: '🌟' },
                    { id: 'manara', label: 'Manara', sub: 'Erotic', emoji: '🔞' }
                  ].map(deck => (
                    <div
                      key={deck.id}
                      onClick={async () => {
                        try {
                          await axios.post(`${API_BASE}/admin-config`, { tarot_deck: deck.id });
                          setAdminConfig({ ...adminConfig, tarot_deck: deck.id });
                        } catch (err) { alert('Failed to change deck'); }
                      }}
                      style={{
                        padding: '1rem', borderRadius: '0.75rem', cursor: 'pointer',
                        border: adminConfig.tarot_deck === deck.id ? '2px solid var(--accent)' : '1px solid rgba(255,255,255,0.1)',
                        background: adminConfig.tarot_deck === deck.id ? 'rgba(99,102,241,0.1)' : 'rgba(255,255,255,0.02)',
                        display: 'flex', alignItems: 'center', gap: '1rem'
                      }}
                    >
                      <span style={{ fontSize: '1.5rem' }}>{deck.emoji}</span>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 'bold', fontSize: '0.9rem' }}>{deck.label}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>{deck.sub}</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem' }}>
                <div>
                  <h2 style={{ marginBottom: '0.25rem' }}>🔮 Numerology Engine</h2>
                  <p style={{ color: 'var(--text-secondary)' }}>Daily forecast based on dates and resonance.</p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                   <button className="btn btn-primary" onClick={async () => {
                      try {
                        await axios.post(`${API_BASE}/numerology/settings`, numerologySettings);
                        setNumerologySaveMsg('✅ Saved!');
                        setTimeout(() => setNumerologySaveMsg(''), 2000);
                      } catch { setNumerologySaveMsg('❌ Error'); }
                   }}>Save</button>
                   <button className="btn" onClick={async () => {
                      setNumerologyPreviewLoading(true);
                      try {
                        const res = await axios.get(`${API_BASE}/numerology/preview`);
                        setNumerologyPreview(res.data);
                      } catch { alert('Preview failed'); }
                      setNumerologyPreviewLoading(false);
                   }}>{numerologyPreviewLoading ? '...' : 'Preview Today'}</button>
                </div>
              </div>

              <div className="grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', gap: '1.5rem' }}>
                <div className="form-group">
                  <label className="label">Morning Hour</label>
                  <input className="input" type="number" min="0" max="23" value={numerologySettings.morning_hour} onChange={e => setNumerologySettings({...numerologySettings, morning_hour: parseInt(e.target.value)})} />
                </div>
                <div className="form-group">
                  <label className="label">Evening Hour</label>
                  <input className="input" type="number" min="0" max="23" value={numerologySettings.evening_hour} onChange={e => setNumerologySettings({...numerologySettings, evening_hour: parseInt(e.target.value)})} />
                </div>
                <div className="form-group">
                  <label className="label">Forecast Channel</label>
                  <select className="input" value={numerologySettings.channel_id} onChange={e => setNumerologySettings({...numerologySettings, channel_id: e.target.value})}>
                    <option value="">(None)</option>
                    {Object.entries(channels).map(([id, ch]) => <option key={id} value={id}>#{ch.name}</option>)}
                  </select>
                </div>
              </div>

              {numerologyPreview && (
                <div style={{ marginTop: '1.5rem', padding: '1rem', background: 'rgba(99,102,241,0.05)', borderRadius: '0.75rem', border: '1px solid rgba(99,102,241,0.2)' }}>
                  <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.8rem', fontFamily: 'monospace' }}>{numerologyPreview.reading}</pre>
                </div>
              )}
            </div>
          </div>
        )}

        {activeTab === 'keygallery' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div>
                  <h2 style={{ marginBottom: '0.25rem' }}>🔑 Key Command Gallery</h2>
                  <p style={{ color: 'var(--text-secondary)' }}>Manage the images and limits for the <code>.key</code> command.</p>
                </div>
                {keySaveMsg && <span className="badge badge-success">{keySaveMsg}</span>}
              </div>

              <div className="grid" style={{ gridTemplateColumns: '2fr 1fr', gap: '2rem' }}>
                <div className="form-group">
                  <label className="label">Active Image Repository URL</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input 
                      className="input" style={{ flex: 1 }}
                      value={keySettings.active_url} 
                      onChange={e => setKeySettings({...keySettings, active_url: e.target.value})}
                    />
                    <button className="btn btn-primary" onClick={async () => {
                       await axios.post(`${API_BASE}/key-settings/config`, { 
                         send_count_user: keySendUser, 
                         send_count_admin: keySendAdmin 
                       });
                       setKeySaveMsg('Saved!');
                       setTimeout(() => setKeySaveMsg(''), 2000);
                    }}>Save</button>
                  </div>
                </div>
                <div className="form-group">
                  <label className="label">Send Limit (User/Admin)</label>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                       <span style={{ fontSize: '0.75rem' }}>User:</span>
                       <input className="input" type="number" style={{ width: '60px' }} value={keySendUser} onChange={e => setKeySendUser(parseInt(e.target.value))} />
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                       <span style={{ fontSize: '0.75rem' }}>Admin:</span>
                       <input className="input" type="number" style={{ width: '60px' }} value={keySendAdmin} onChange={e => setKeySendAdmin(parseInt(e.target.value))} />
                    </div>
                  </div>
                </div>
              </div>

              <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)', padding: '1.5rem', marginTop: '1.5rem' }}>
                 <h3 style={{ marginBottom: '1rem' }}>Image Bank ({keySettings.images?.length || 0})</h3>
                 <div className="table-container" style={{ maxHeight: '400px' }}>
                    <table>
                      <thead>
                        <tr>
                          <th>Label</th>
                          <th>URL Fragment</th>
                          <th style={{ width: '100px' }}>Status</th>
                          <th style={{ width: '60px' }}></th>
                        </tr>
                      </thead>
                      <tbody>
                        {keySettings.images?.map(img => (
                          <tr key={img.id} style={{ opacity: img.active ? 1 : 0.6 }}>
                            <td style={{ fontWeight: img.active ? 'bold' : 'normal' }}>{img.label}</td>
                            <td style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>{img.url}</td>
                            <td>
                              {img.active ? 
                                <span className="badge badge-success">Active</span> : 
                                <button className="btn" style={{ padding: '0.2rem 0.5rem', fontSize: '0.7rem' }} onClick={async () => {
                                  await axios.post(`${API_BASE}/key-settings/images/${img.id}/activate`);
                                  const ks = await axios.get(`${API_BASE}/key-settings`);
                                  setKeySettings(ks.data);
                                }}>Activate</button>
                              }
                            </td>
                            <td>
                               <button onClick={async () => {
                                 await axios.delete(`${API_BASE}/key-settings/images/${img.id}`);
                                 const ks = await axios.get(`${API_BASE}/key-settings`);
                                 setKeySettings(ks.data);
                               }} style={{ color: 'var(--danger)', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                 </div>
                 <div className="grid" style={{ gridTemplateColumns: '1fr 1fr auto', gap: '0.5rem', marginTop: '1.5rem' }}>
                    <input className="input" placeholder="Image URL Fragment..." value={keyImageInput} onChange={e => setKeyImageInput(e.target.value)} />
                    <input className="input" placeholder="Label (e.g. Thoth)..." value={keyLabelInput} onChange={e => setKeyLabelInput(e.target.value)} />
                    <button className="btn btn-primary" onClick={async () => {
                        await axios.post(`${API_BASE}/key-settings/images`, { url: keyImageInput, label: keyLabelInput });
                        setKeyImageInput(''); setKeyLabelInput('');
                        const ks = await axios.get(`${API_BASE}/key-settings`);
                        setKeySettings(ks.data);
                    }}>Add Image</button>
                 </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'quotedrops' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                  <h2 style={{ marginBottom: '0.25rem' }}>🚀 Quote Drops</h2>
                  <p style={{ color: 'var(--text-secondary)' }}>Configure automated random quote drops in the main channel.</p>
                </div>
                <button 
                  className={`btn ${sendSuccess === 'quote-drop' ? 'btn-success' : 'btn-primary'}`} 
                  onClick={triggerQuoteDrop}
                  disabled={sendSuccess === 'quote-drop'}
                >
                  <Zap size={16} style={{ marginRight: '0.5rem' }} /> 
                  {sendSuccess === 'quote-drop' ? 'DROP SENT!' : 'SEND DROP NOW'}
                </button>
              </div>

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                <div className="form-group">
                  <label className="label">Enabled</label>
                  <div className={`toggle ${quoteDropsEnabled ? 'active' : ''}`} onClick={() => setQuoteDropsEnabled(!quoteDropsEnabled)}>
                    <div className="toggle-handle"></div>
                  </div>
                </div>
                <div className="form-group">
                  <label className="label">Interval (Hours)</label>
                  <input 
                    className="input" type="number" step="0.5"
                    value={quoteDropsInterval} 
                    onChange={e => setQuoteDropsInterval(parseFloat(e.target.value))} 
                  />
                </div>
                <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                   <button className="btn btn-primary" style={{ width: '100%' }} onClick={saveQuoteDropConfig}>Save Configuration</button>
                </div>
              </div>

              <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)', padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ margin: 0 }}>Quote Bank ({quoteDrops.length})</h3>
                  <button className="btn" style={{ padding: '0.4rem', background: 'rgba(255,255,255,0.05)' }} onClick={fetchContentData} title="Refresh list from database">
                    <RefreshCw size={16} />
                  </button>
                </div>
                <div className="table-container" style={{ maxHeight: '400px' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Quote Content</th>
                        <th style={{ width: '120px' }}>Added By</th>
                        <th style={{ width: '60px' }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {quoteDrops.length > 0 ? quoteDrops.map((q) => (
                        <tr key={q.id}>
                          <td style={{ fontSize: '0.9rem' }}>{q.quote}</td>
                          <td style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{q.added_by}</td>
                          <td style={{ textAlign: 'right' }}>
                            <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'flex-end' }}>
                              <button 
                                onClick={() => sendQuoteDrop(q.id)} 
                                title="Send this quote now"
                                style={{ color: 'var(--accent)', background: 'none', border: 'none', cursor: 'pointer' }}
                              >
                                <Send size={16} />
                              </button>
                              <button onClick={() => deleteQuoteDrop(q.id)} style={{ color: 'var(--danger)', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                            </div>
                          </td>
                        </tr>
                      )) : (
                        <tr><td colSpan="3" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>No quotes found in bank.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
                   <input 
                    className="input" placeholder="Enter a new quote for the drop bank..." 
                    value={newQuoteDrop} onChange={e => setNewQuoteDrop(e.target.value)} 
                    onKeyDown={e => e.key === 'Enter' && addQuoteDrop()}
                   />
                   <button className="btn btn-primary" onClick={addQuoteDrop}>Add Quote</button>
                </div>
              </div>
            </div>
          </div>
        )}


        {activeTab === 'quotes' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                  <h2 style={{ marginBottom: '0.25rem' }}>🌅 Daily Quotes</h2>
                  <p style={{ color: 'var(--text-secondary)' }}>Philosophical quotes posted at sunrise and sunset.</p>
                </div>
              </div>

              <div className="grid" style={{ gridTemplateColumns: '1fr 1fr 1fr', gap: '1.5rem', marginBottom: '2rem' }}>
                <div className="form-group">
                  <label className="label">Morning Hour (Morning Post)</label>
                  <input className="input" type="number" value={quoteSchedule.morning_hour} onChange={e => setQuoteSchedule({...quoteSchedule, morning_hour: parseInt(e.target.value)})} />
                </div>
                <div className="form-group">
                  <label className="label">Evening Hour (Evening Post)</label>
                  <input className="input" type="number" value={quoteSchedule.evening_hour} onChange={e => setQuoteSchedule({...quoteSchedule, evening_hour: parseInt(e.target.value)})} />
                </div>
                <div className="form-group" style={{ display: 'flex', alignItems: 'flex-end' }}>
                   <button className="btn btn-primary" style={{ width: '100%' }} onClick={saveQuoteSchedule}>Save Schedule</button>
                </div>
              </div>

              <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)', padding: '1.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ margin: 0 }}>Quote Pool ({dailyQuotes.length})</h3>
                  <button className="btn" style={{ padding: '0.4rem', background: 'rgba(255,255,255,0.05)' }} onClick={fetchContentData} title="Refresh list from database">
                    <RefreshCw size={16} />
                  </button>
                </div>
                <div className="table-container" style={{ maxHeight: '400px' }}>
                  <table>
                    <thead>
                      <tr>
                        <th>Quote Content</th>
                        <th style={{ width: '60px' }}></th>
                      </tr>
                    </thead>
                    <tbody>
                      {dailyQuotes.length > 0 ? dailyQuotes.map((q) => (
                        <tr key={q.id}>
                          <td style={{ fontSize: '0.9rem' }}>{q.quote}</td>
                          <td>
                            <button onClick={() => deleteDailyQuote(q.id)} style={{ color: 'var(--danger)', background: 'none', border: 'none', cursor: 'pointer' }}>✕</button>
                          </td>
                        </tr>
                      )) : (
                        <tr><td colSpan="2" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>No quotes found in master pool.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
                <div style={{ display: 'flex', gap: '0.5rem', marginTop: '1.5rem' }}>
                   <input 
                    className="input" placeholder="Enter a deep philosophical thought..." 
                    value={newDailyQuote} onChange={e => setNewDailyQuote(e.target.value)} 
                    onKeyDown={e => e.key === 'Enter' && addDailyQuote()}
                   />
                   <button className="btn btn-primary" onClick={addDailyQuote}>Add to Pool</button>
                </div>
              </div>
            </div>
          </div>
        )}
 
        {activeTab === 'roles' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <div>
                  <h2 style={{ marginBottom: '0.25rem' }}>🎨 Color Roles</h2>
                  <p style={{ color: 'var(--text-secondary)' }}>Server-funded vanity roles that members can vote to assign.</p>
                </div>
                <div style={{ display: 'flex', gap: '0.75rem' }}>
                    <button className="btn" style={{ background: 'rgba(255,255,255,0.05)' }} onClick={fetchColorRoles} title="Refresh Roles">
                        <RefreshCw size={16} />
                    </button>
                    <button
                        className="btn"
                        style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.3)', color: 'var(--accent)', height: 'fit-content' }}
                        onClick={async () => {
                            try {
                            await axios.post(`${API_BASE}/bulletin/refresh-colors`);
                            alert('✅ Bot commands refresh triggered! The bot will sync in a few seconds.');
                            } catch {
                            alert('❌ Failed to trigger refresh.');
                            }
                        }}
                    >
                    <Settings size={16} style={{ marginRight: '0.5rem' }} /> Refresh Bot Commands
                    </button>
                </div>
              </div>
 
              <div style={{ background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem', padding: '1.25rem', marginBottom: '1.5rem', border: '1px solid rgba(255,255,255,0.05)' }}>
                <h4 style={{ marginBottom: '1rem', color: 'var(--text-secondary)', fontSize: '0.85rem', textTransform: 'uppercase' }}>Register New Color Role</h4>
                <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="label">Name (e.g. Pink)</label>
                    <input className="input" placeholder="e.g. pink" value={newColorRole.name} onChange={e => setNewColorRole({...newColorRole, name: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="label">Discord Role ID</label>
                    <input className="input" placeholder="123456789..." value={newColorRole.role_id} onChange={e => setNewColorRole({...newColorRole, role_id: e.target.value})} />
                  </div>
                  <div className="form-group">
                    <label className="label">Vote Threshold</label>
                    <input className="input" type="number" value={newColorRole.vote_threshold} onChange={e => setNewColorRole({...newColorRole, vote_threshold: parseInt(e.target.value)})} />
                  </div>
                  <div className="form-group">
                    <label className="label">Duration (Days)</label>
                    <input className="input" type="number" value={newColorRole.duration_days} onChange={e => setNewColorRole({...newColorRole, duration_days: parseInt(e.target.value)})} />
                  </div>
                </div>
                <button className="btn btn-primary" style={{ marginTop: '1rem', width: '100%' }} onClick={async () => {
                  try {
                    await axios.post(`${API_BASE}/bulletin/color-roles`, newColorRole);
                    setNewColorRole({ name: '', role_id: '', vote_threshold: 7, duration_days: 2 });
                    fetchColorRoles();
                  } catch { alert('Failed to add color role'); }
                }}>Add System Role</button>
              </div>
 
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Prefix</th>
                      <th>Role ID</th>
                      <th>Threshold</th>
                      <th>Expiry</th>
                      <th style={{ width: '60px' }}></th>
                    </tr>
                  </thead>
                  <tbody>
                    {!colorRoles || colorRoles.length === 0 ? (
                      <tr>
                        <td colSpan="5" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-secondary)' }}>
                          No color roles defined yet. Add one above!
                        </td>
                      </tr>
                    ) : (
                      colorRoles.map(cr => (
                        <tr key={cr?.name || Math.random()}>
                          <td style={{ fontWeight: 'bold', color: 'var(--accent)' }}>.{cr?.name?.replace(/^\./, '') || 'unknown'}</td>
                          <td><code style={{ fontSize: '0.8rem' }}>{cr?.role_id || '???'}</code></td>
                          <td>{cr?.vote_threshold || 7} votes</td>
                          <td>{cr?.duration_days ?? 2} days</td>
                          <td><button className="btn" style={{ color: 'var(--danger)', padding: '0.4rem' }} onClick={async () => {
                            if (!cr?.name) return;
                            if(!confirm(`Delete .${cr.name}?`)) return;
                            await axios.delete(`${API_BASE}/bulletin/color-roles/${cr.name}`);
                            fetchColorRoles();
                          }}><Trash2 size={16}/></button></td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'moderation' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="grid" style={{ gridTemplateColumns: '1.2fr 1fr', gap: '2rem' }}>
              <div className="card">
                <h2 style={{ marginBottom: '0.5rem' }}>⭐ Hall of Fame</h2>
                <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>Record top-tier messages when they reach a reaction threshold.</p>
                <div className="form-group">
                  <label className="label">HOF Channel</label>
                  <select className="input" value={hofSettings.channel_id} onChange={e => setHofSettings({...hofSettings, channel_id: e.target.value})}>
                    <option value="">(Disabled)</option>
                    {Object.entries(channels).map(([id, ch]) => <option key={id} value={id}>#{ch.name}</option>)}
                  </select>
                </div>
                <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
                  <div className="form-group">
                    <label className="label">Star Threshold</label>
                    <input className="input" type="number" value={hofSettings.threshold} onChange={e => setHofSettings({...hofSettings, threshold: parseInt(e.target.value)})} />
                  </div>
                  <div className="form-group">
                    <label className="label">React Emojis (comma separated)</label>
                    <input className="input" value={hofEmojiInput} onChange={e => setHofEmojiInput(e.target.value)} onBlur={() => setHofSettings({...hofSettings, emojis: hofEmojiInput.split(',').map(s => s.trim()).filter(s => s)})} />
                  </div>
                </div>
                <button className="btn btn-primary" style={{ width: '100%', marginTop: '1rem' }} onClick={async () => {
                  try {
                    await axios.post(`${API_BASE}/hof-settings`, hofSettings);
                    alert('HOF Settings Saved!');
                  } catch { alert('Save failed'); }
                }}>Save Starboard Settings</button>
              </div>

              <div className="card">
                <h2 style={{ marginBottom: '1.5rem' }}>🛡️ Whitelists & Routing</h2>
                <div className="form-group">
                   <label className="label">Log Channel (Errors & Meta)</label>
                   <select className="input" value={pendingSettings.log_channel_id} onChange={e => updateSetting('log_channel_id', e.target.value)}>
                     <option value="">(None)</option>
                     {Object.entries(channels).map(([id, ch]) => <option key={id} value={id}>#{ch.name}</option>)}
                   </select>
                </div>
                <div className="form-group" style={{ marginTop: '1.5rem' }}>
                  <label className="label">Admin Channel</label>
                  <select className="input" value={pendingSettings.admin_channel} onChange={e => updateSetting('admin_channel', e.target.value)}>
                    <option value="">(None)</option>
                    {Object.entries(channels).map(([id, ch]) => <option key={id} value={id}>#{ch.name}</option>)}
                  </select>
                </div>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '1.5rem' }}>
                  More granular command whitelists for Spam/Main channels can be configured via slash commands in-chat.
                </p>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'economy' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <h2 style={{ margin: 0 }}>🛒 Shop Pricing</h2>
                {shopSaveMsg && <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>{shopSaveMsg}</span>}
              </div>
              <div className="table-container">
                <table className="table">
                  <thead>
                    <tr>
                      <th style={{ textAlign: 'left' }}>Item</th>
                      <th style={{ textAlign: 'left' }}>Description</th>
                      <th style={{ textAlign: 'center', width: '120px' }}>Base</th>
                      <th style={{ textAlign: 'center', width: '150px' }}>Current</th>
                    </tr>
                  </thead>
                  <tbody>
                    {shopItems.map(item => (
                      <tr key={item.key}>
                        <td style={{ fontWeight: '600', color: 'var(--accent)' }}>{item.name}</td>
                        <td style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>{item.description}</td>
                        <td style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>{item.base_price}</td>
                        <td style={{ textAlign: 'center' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', justifyContent: 'center' }}>
                            <input className="input" type="number" style={{ width: '80px', textAlign: 'center' }} defaultValue={item.current_price} onBlur={(e) => savePrice(item.key, e.target.value)} />
                            <span style={{ color: 'var(--accent)' }}>💎</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: '0.25rem' }}>🏦 Deposit Settings</h2>
              <p style={{ color: 'var(--text-secondary)', marginBottom: '1.25rem' }}>DM instructions for the <code>.deposit</code> command.</p>
              <textarea
                className="input"
                style={{ width: '100%', minHeight: '120px', fontFamily: 'monospace', fontSize: '0.9rem' }}
                placeholder="e.g. BTC: 1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa ..."
                value={depositInfo}
                onChange={(e) => setDepositInfo(e.target.value)}
                onBlur={saveDepositInfo}
              />
              <div style={{ marginTop: '0.75rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Auto-saves on blur</span>
                  {depositSaveMsg && <span style={{ color: depositSaveMsg.includes('✅') ? 'var(--success)' : 'var(--danger)', fontSize: '0.85rem', fontWeight: 'bold' }}>{depositSaveMsg}</span>}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'system' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
            <div className="grid" style={{ gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
              <div className="card">
                <h2 style={{ marginBottom: '1rem' }}>🤖 Bot Persona</h2>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem', marginBottom: '1.5rem' }}>
                  <div>
                    <h4 style={{ margin: 0 }}>Yap Level</h4>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{adminConfig.yap_level === 'high' ? 'Detailed & verbose responses.' : 'Concise & blunt responses.'}</p>
                  </div>
                  <div className={`toggle ${adminConfig.yap_level === 'high' ? 'active' : ''}`} onClick={() => saveAdmin({ yap_level: adminConfig.yap_level === 'high' ? 'low' : 'high' })}>
                    <div className="toggle-handle"></div>
                  </div>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem' }}>
                  <div>
                    <h4 style={{ margin: 0 }}>Economy System</h4>
                    <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Toggle global banking and shop features.</p>
                  </div>
                  <div className={`toggle ${adminConfig.economy_enabled ? 'active' : ''}`} onClick={() => saveAdmin({ economy_enabled: !adminConfig.economy_enabled })}>
                    <div className="toggle-handle"></div>
                  </div>
                </div>
              </div>

              <div className="card">
                <h2 style={{ marginBottom: '1rem' }}>🧠 System Memory</h2>
                <label className="label">Base Prompt (System Note)</label>
                <textarea
                  className="input"
                  style={{ width: '100%', minHeight: '135px', fontSize: '0.9rem' }}
                  value={pendingSettings.system_note || ''}
                  onChange={(e) => setPendingSettings({ ...pendingSettings, system_note: e.target.value })}
                  onBlur={(e) => updateSetting('system_note', e.target.value)}
                />
              </div>
            </div>

            <div className="card">
              <h2 style={{ marginBottom: '1.5rem' }}>💾 Data Management</h2>
              <div className="grid" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '1.5rem' }}>
                <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <h4 style={{ marginBottom: '0.5rem' }}>Export Statistics</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Download all user XP and level data.</p>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <button className="btn" onClick={() => window.open(`${API_BASE}/export/json`, '_blank')}>JSON</button>
                    <button className="btn" onClick={() => window.open(`${API_BASE}/export/csv`, '_blank')}>CSV</button>
                  </div>
                </div>

                <div className="card shadow-none" style={{ background: 'rgba(255,255,255,0.02)' }}>
                  <h4 style={{ marginBottom: '0.5rem', color: 'var(--danger)' }}>Maintenance</h4>
                  <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>Prune inactive members with low XP.</p>
                  <div style={{ display: 'flex', gap: '0.5rem' }}>
                    <input className="input" type="number" style={{ width: '80px' }} value={pruneThreshold} onChange={e => setPruneThreshold(e.target.value)} />
                    <button className="btn" style={{ background: 'var(--danger)', color: '#fff' }} onClick={async () => {
                       if (!window.confirm(`Delete users with < ${pruneThreshold} XP?`)) return;
                       const res = await axios.post(`${API_BASE}/prune`, { threshold: parseInt(pruneThreshold) });
                       alert(`Pruned ${res.data.deleted} members.`);
                    }}>Prune</button>
                  </div>
                </div>
              </div>

              <div style={{ marginTop: '2rem', padding: '1.5rem', border: '1px dashed rgba(255,255,255,0.1)', borderRadius: '1rem' }}>
                <h4 style={{ marginBottom: '1rem' }}>Migration / Import</h4>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '1rem' }}>
                  <input type="file" accept=".json" onChange={e => setImportFile(e.target.files[0])} style={{ fontSize: '0.8rem' }} />
                  <button className="btn btn-primary" onClick={async () => {
                    if (!importFile) return;
                    const reader = new FileReader();
                    reader.onload = async (e) => {
                      try {
                        const data = JSON.parse(e.target.result);
                        await axios.post(`${API_BASE}/import`, data);
                        alert('Import Successful');
                      } catch { alert('Import Failed'); }
                    };
                    reader.readAsText(importFile);
                  }}>Run Import</button>
                </div>
                <div style={{ display: 'flex', gap: '1rem' }}>
                   <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}><input type="checkbox" checked={importOptions.importXP} onChange={e => setImportOptions({...importOptions, importXP: e.target.checked})} /> Include XP</label>
                   <label style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}><input type="checkbox" checked={importOptions.importSettings} onChange={e => setPendingSettings({...importOptions, importSettings: e.target.checked})} /> Include Settings</label>
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
