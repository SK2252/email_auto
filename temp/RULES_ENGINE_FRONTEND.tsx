# Rules Engine Frontend Components
## Complete React Implementation

These are all the React components you need for the Rules Engine UI.

---

## FILE 1: frontend/src/components/RulesUI.tsx

```typescript
// frontend/src/components/RulesUI.tsx
import React, { useState, useEffect } from 'react';
import { fetchRules, deleteRule, toggleRule } from '../services/rulesService';
import RuleBuilder from './RuleBuilder';
import RuleTest from './RuleTest';
import './RulesUI.css';

interface Rule {
  id?: string;
  name: string;
  description?: string;
  priority: number;
  domain: string;
  match_mode: string;
  stop_on_match: boolean;
  active: boolean;
  conditions: Condition[];
  actions: Action[];
}

interface Condition {
  field: string;
  operator: string;
  value: any;
}

interface Action {
  action: string;
  value: any;
}

type TabType = 'rules' | 'builder' | 'test';

export default function RulesUI() {
  const [rules, setRules] = useState<Rule[]>([]);
  const [activeTab, setActiveTab] = useState<TabType>('rules');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [expandedRule, setExpandedRule] = useState<string | null>(null);

  // Load rules on mount
  useEffect(() => {
    loadRules();
  }, []);

  const loadRules = async () => {
    setLoading(true);
    try {
      const data = await fetchRules();
      setRules(data.rules || []);
      setError('');
    } catch (err) {
      setError(`Failed to load rules: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (window.confirm('Are you sure you want to delete this rule?')) {
      try {
        await deleteRule(ruleId);
        loadRules();
      } catch (err) {
        setError(`Failed to delete rule: ${err}`);
      }
    }
  };

  const handleToggleRule = async (ruleId: string) => {
    try {
      await toggleRule(ruleId);
      loadRules();
    } catch (err) {
      setError(`Failed to toggle rule: ${err}`);
    }
  };

  const handleRuleSaved = () => {
    loadRules();
    setActiveTab('rules');
  };

  return (
    <div className="rules-ui">
      <div className="rules-header">
        <h2>📋 Rules Engine</h2>
        <p>Manage email routing rules with IF-THEN conditions</p>
      </div>

      {error && <div className="error-banner">{error}</div>}

      <div className="rules-tabs">
        <button
          className={`tab-button ${activeTab === 'rules' ? 'active' : ''}`}
          onClick={() => setActiveTab('rules')}
        >
          📑 Active Rules ({rules.filter(r => r.active).length})
        </button>
        <button
          className={`tab-button ${activeTab === 'builder' ? 'active' : ''}`}
          onClick={() => setActiveTab('builder')}
        >
          ➕ New Rule
        </button>
        <button
          className={`tab-button ${activeTab === 'test' ? 'active' : ''}`}
          onClick={() => setActiveTab('test')}
        >
          🧪 Test Engine
        </button>
      </div>

      <div className="rules-content">
        {activeTab === 'rules' && (
          <RulesList
            rules={rules}
            loading={loading}
            expandedRule={expandedRule}
            setExpandedRule={setExpandedRule}
            onDelete={handleDeleteRule}
            onToggle={handleToggleRule}
          />
        )}

        {activeTab === 'builder' && (
          <RuleBuilder onSaved={handleRuleSaved} />
        )}

        {activeTab === 'test' && (
          <RuleTest rules={rules} />
        )}
      </div>
    </div>
  );
}

// ============================================================================
// RULES LIST COMPONENT
// ============================================================================

interface RulesListProps {
  rules: Rule[];
  loading: boolean;
  expandedRule: string | null;
  setExpandedRule: (id: string | null) => void;
  onDelete: (id: string) => void;
  onToggle: (id: string) => void;
}

function RulesList({
  rules,
  loading,
  expandedRule,
  setExpandedRule,
  onDelete,
  onToggle,
}: RulesListProps) {
  if (loading) {
    return <div className="loading">Loading rules...</div>;
  }

  if (rules.length === 0) {
    return (
      <div className="empty-state">
        <p>No rules configured yet</p>
        <p style={{ fontSize: '12px', color: '#999' }}>
          Create a rule to get started with email routing automation
        </p>
      </div>
    );
  }

  // Sort by priority
  const sorted = [...rules].sort((a, b) => a.priority - b.priority);

  return (
    <div className="rules-list">
      {sorted.map(rule => (
        <div
          key={rule.id || rule.name}
          className={`rule-card ${rule.active ? 'active' : 'inactive'}`}
        >
          <div
            className="rule-header"
            onClick={() =>
              setExpandedRule(
                expandedRule === rule.id ? null : rule.id || rule.name
              )
            }
          >
            <div className="rule-title">
              <span className="rule-priority">#{rule.priority}</span>
              <span className="rule-name">{rule.name}</span>
              <span className="rule-domain">{rule.domain}</span>
            </div>

            <div className="rule-actions">
              <button
                className={`toggle-btn ${rule.active ? 'on' : 'off'}`}
                onClick={e => {
                  e.stopPropagation();
                  onToggle(rule.id || rule.name);
                }}
                title={rule.active ? 'Disable' : 'Enable'}
              >
                {rule.active ? '✓ Active' : '✗ Inactive'}
              </button>

              <button
                className="delete-btn"
                onClick={e => {
                  e.stopPropagation();
                  onDelete(rule.id || rule.name);
                }}
              >
                Delete
              </button>

              <span className="expand-icon">
                {expandedRule === rule.id ? '▼' : '▶'}
              </span>
            </div>
          </div>

          {expandedRule === rule.id && (
            <div className="rule-details">
              {rule.description && (
                <p className="rule-description">{rule.description}</p>
              )}

              <div className="rule-section">
                <h4>Conditions ({rule.match_mode.toUpperCase()})</h4>
                <ul className="conditions-list">
                  {rule.conditions.map((cond, i) => (
                    <li key={i}>
                      <code>
                        {cond.field} {cond.operator}{' '}
                        {typeof cond.value === 'object'
                          ? JSON.stringify(cond.value)
                          : cond.value}
                      </code>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rule-section">
                <h4>Actions</h4>
                <ul className="actions-list">
                  {rule.actions.map((action, i) => (
                    <li key={i}>
                      <span className="action-type">{action.action}</span>
                      <span className="action-value">→ {action.value}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="rule-meta">
                <span>Match mode: {rule.match_mode}</span>
                <span>Stop on match: {rule.stop_on_match ? 'Yes' : 'No'}</span>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
```

---

## FILE 2: frontend/src/components/RuleBuilder.tsx

```typescript
// frontend/src/components/RuleBuilder.tsx
import React, { useState } from 'react';
import { createRule } from '../services/rulesService';
import './RuleBuilder.css';

interface Condition {
  field: string;
  operator: string;
  value: any;
}

interface Action {
  action: string;
  value: any;
}

interface RuleBuilderProps {
  onSaved: () => void;
}

const VALID_OPERATORS = [
  'is',
  'is_not',
  'in',
  'not_in',
  'contains',
  'starts_with',
  'greater_than',
  'less_than',
  'greater_or_equal',
  'less_or_equal',
];

const VALID_ACTIONS = [
  'route_to',
  'set_sla',
  'send_ack',
  'notify_slack',
  'hold_for_review',
  'apply_label',
];

const VALID_FIELDS = [
  'domain',
  'type',
  'priority',
  'sentiment',
  'confidence',
  'sender',
  'subject',
];

export default function RuleBuilder({ onSaved }: RuleBuilderProps) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState(10);
  const [domain, setDomain] = useState('IT Support');
  const [matchMode, setMatchMode] = useState('all');
  const [stopOnMatch, setStopOnMatch] = useState(true);
  const [conditions, setConditions] = useState<Condition[]>([
    { field: 'domain', operator: 'is', value: '' },
  ]);
  const [actions, setActions] = useState<Action[]>([
    { action: 'route_to', value: '' },
  ]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const addCondition = () => {
    setConditions([
      ...conditions,
      { field: 'domain', operator: 'is', value: '' },
    ]);
  };

  const removeCondition = (index: number) => {
    setConditions(conditions.filter((_, i) => i !== index));
  };

  const updateCondition = (
    index: number,
    field: keyof Condition,
    value: any
  ) => {
    const updated = [...conditions];
    updated[index] = { ...updated[index], [field]: value };
    setConditions(updated);
  };

  const addAction = () => {
    setActions([...actions, { action: 'route_to', value: '' }]);
  };

  const removeAction = (index: number) => {
    setActions(actions.filter((_, i) => i !== index));
  };

  const updateAction = (index: number, field: keyof Action, value: any) => {
    const updated = [...actions];
    updated[index] = { ...updated[index], [field]: value };
    setActions(updated);
  };

  const save = async () => {
    if (!name.trim()) {
      setError('Rule name is required');
      return;
    }
    if (conditions.length === 0) {
      setError('At least one condition is required');
      return;
    }
    if (actions.length === 0) {
      setError('At least one action is required');
      return;
    }

    setSaving(true);
    setError('');

    try {
      await createRule({
        name,
        description,
        priority,
        domain,
        match_mode: matchMode,
        stop_on_match: stopOnMatch,
        active: true,
        conditions,
        actions,
      });

      // Reset form
      setName('');
      setDescription('');
      setPriority(10);
      setDomain('IT Support');
      setMatchMode('all');
      setStopOnMatch(true);
      setConditions([{ field: 'domain', operator: 'is', value: '' }]);
      setActions([{ action: 'route_to', value: '' }]);

      onSaved();
    } catch (err) {
      setError(`Failed to save rule: ${err}`);
    } finally {
      setSaving(false);
    }
  };

  const previewJson = {
    name,
    priority,
    domain,
    match_mode: matchMode,
    stop_on_match: stopOnMatch,
    conditions,
    actions,
  };

  return (
    <div className="rule-builder">
      <div className="builder-form">
        <div className="form-group">
          <label>Rule Name *</label>
          <input
            type="text"
            value={name}
            onChange={e => setName(e.target.value)}
            placeholder="e.g., IT support escalation"
          />
        </div>

        <div className="form-group">
          <label>Description</label>
          <textarea
            value={description}
            onChange={e => setDescription(e.target.value)}
            placeholder="What does this rule do?"
            rows={2}
          />
        </div>

        <div className="form-row">
          <div className="form-group" style={{ flex: 1 }}>
            <label>Priority</label>
            <input
              type="number"
              value={priority}
              onChange={e => setPriority(parseInt(e.target.value))}
              min="1"
              max="100"
            />
            <small>Lower = higher priority</small>
          </div>

          <div className="form-group" style={{ flex: 1 }}>
            <label>Domain</label>
            <select value={domain} onChange={e => setDomain(e.target.value)}>
              <option>IT Support</option>
              <option>HR</option>
              <option>Customer Support</option>
              <option>Billing</option>
              <option>any</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group" style={{ flex: 1 }}>
            <label>Match Mode</label>
            <select value={matchMode} onChange={e => setMatchMode(e.target.value)}>
              <option value="all">ALL conditions must match</option>
              <option value="any">ANY condition can match</option>
            </select>
          </div>

          <div className="form-group" style={{ flex: 1 }}>
            <label>
              <input
                type="checkbox"
                checked={stopOnMatch}
                onChange={e => setStopOnMatch(e.target.checked)}
              />
              Stop processing after match
            </label>
          </div>
        </div>

        {/* Conditions */}
        <div className="form-section">
          <h3>Conditions</h3>
          {conditions.map((cond, i) => (
            <div key={i} className="condition-row">
              <select
                value={cond.field}
                onChange={e => updateCondition(i, 'field', e.target.value)}
              >
                {VALID_FIELDS.map(f => (
                  <option key={f}>{f}</option>
                ))}
              </select>

              <select
                value={cond.operator}
                onChange={e => updateCondition(i, 'operator', e.target.value)}
              >
                {VALID_OPERATORS.map(op => (
                  <option key={op}>{op}</option>
                ))}
              </select>

              <input
                type="text"
                value={
                  typeof cond.value === 'object'
                    ? JSON.stringify(cond.value)
                    : cond.value
                }
                onChange={e => updateCondition(i, 'value', e.target.value)}
                placeholder="Value"
              />

              <button
                className="remove-btn"
                onClick={() => removeCondition(i)}
                disabled={conditions.length === 1}
              >
                ✕
              </button>
            </div>
          ))}

          <button className="add-btn" onClick={addCondition}>
            + Add Condition
          </button>
        </div>

        {/* Actions */}
        <div className="form-section">
          <h3>Actions</h3>
          {actions.map((action, i) => (
            <div key={i} className="action-row">
              <select
                value={action.action}
                onChange={e => updateAction(i, 'action', e.target.value)}
              >
                {VALID_ACTIONS.map(a => (
                  <option key={a}>{a}</option>
                ))}
              </select>

              <input
                type="text"
                value={action.value}
                onChange={e => updateAction(i, 'value', e.target.value)}
                placeholder="Action value"
              />

              <button
                className="remove-btn"
                onClick={() => removeAction(i)}
                disabled={actions.length === 1}
              >
                ✕
              </button>
            </div>
          ))}

          <button className="add-btn" onClick={addAction}>
            + Add Action
          </button>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="form-actions">
          <button
            className="save-btn"
            onClick={save}
            disabled={saving}
          >
            {saving ? 'Saving...' : '💾 Save Rule'}
          </button>
        </div>
      </div>

      {/* JSON Preview */}
      <div className="builder-preview">
        <h3>Preview</h3>
        <pre>{JSON.stringify(previewJson, null, 2)}</pre>
      </div>
    </div>
  );
}
```

---

## FILE 3: frontend/src/components/RuleTest.tsx

```typescript
// frontend/src/components/RuleTest.tsx
import React, { useState } from 'react';
import { testRule } from '../services/rulesService';
import './RuleTest.css';

interface Rule {
  id?: string;
  name: string;
  priority: number;
  conditions: any[];
  actions: any[];
  active: boolean;
}

interface RuleTestProps {
  rules: Rule[];
}

interface TestResult {
  matched: boolean;
  rule_name?: string;
  rule_id?: string;
  actions: Array<{ action: string; value: string }>;
}

export default function RuleTest({ rules }: RuleTestProps) {
  const [domain, setDomain] = useState('IT Support');
  const [type, setType] = useState('network_issue');
  const [priority, setPriority] = useState('high');
  const [sentiment, setSentiment] = useState('neutral');
  const [confidence, setConfidence] = useState(0.85);
  const [sender, setSender] = useState('user@company.com');
  const [subject, setSubject] = useState('');
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const runTest = async () => {
    setLoading(true);
    setError('');

    try {
      const result = await testRule({
        domain,
        type,
        priority,
        sentiment,
        confidence,
        sender,
        subject,
      });
      setTestResult(result);
    } catch (err) {
      setError(`Test failed: ${err}`);
    } finally {
      setLoading(false);
    }
  };

  const loadTestCase = (ruleName: string) => {
    const rule = rules.find(r => r.name === ruleName);
    if (!rule) return;

    // Extract test case from rule conditions
    const cond = rule.conditions[0];
    if (cond?.field === 'domain') {
      setDomain(cond.value);
    }

    runTest();
  };

  return (
    <div className="rule-test">
      <div className="test-form">
        <h3>Test Email Context</h3>

        <div className="form-row">
          <div className="form-group">
            <label>Domain</label>
            <select value={domain} onChange={e => setDomain(e.target.value)}>
              <option>IT Support</option>
              <option>HR</option>
              <option>Customer Support</option>
              <option>Billing</option>
              <option>Unknown</option>
            </select>
          </div>

          <div className="form-group">
            <label>Type</label>
            <input
              type="text"
              value={type}
              onChange={e => setType(e.target.value)}
              placeholder="e.g., network_issue"
            />
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>Priority</label>
            <select value={priority} onChange={e => setPriority(e.target.value)}>
              <option>high</option>
              <option>medium</option>
              <option>low</option>
            </select>
          </div>

          <div className="form-group">
            <label>Sentiment</label>
            <select value={sentiment} onChange={e => setSentiment(e.target.value)}>
              <option>negative</option>
              <option>neutral</option>
              <option>positive</option>
            </select>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group">
            <label>
              Confidence: {confidence.toFixed(2)}
              <input
                type="range"
                min="0"
                max="1"
                step="0.01"
                value={confidence}
                onChange={e => setConfidence(parseFloat(e.target.value))}
              />
            </label>
          </div>
        </div>

        <div className="form-row">
          <div className="form-group" style={{ flex: 1 }}>
            <label>Sender</label>
            <input
              type="email"
              value={sender}
              onChange={e => setSender(e.target.value)}
            />
          </div>

          <div className="form-group" style={{ flex: 1 }}>
            <label>Subject</label>
            <input
              type="text"
              value={subject}
              onChange={e => setSubject(e.target.value)}
            />
          </div>
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="test-actions">
          <button className="test-btn" onClick={runTest} disabled={loading}>
            {loading ? '🔄 Testing...' : '🧪 Run Test'}
          </button>

          {rules.length > 0 && (
            <div className="quick-tests">
              <label>Quick test:</label>
              {rules.slice(0, 3).map(rule => (
                <button
                  key={rule.name}
                  className="quick-test-btn"
                  onClick={() => loadTestCase(rule.name)}
                >
                  {rule.name}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Test Results */}
      {testResult && (
        <div className="test-result">
          <h3>Test Result</h3>

          <div
            className={`result-card ${testResult.matched ? 'matched' : 'no-match'}`}
          >
            <div className="result-status">
              {testResult.matched ? (
                <>
                  <span className="badge-match">✓ MATCHED</span>
                  <span className="rule-name">{testResult.rule_name}</span>
                </>
              ) : (
                <>
                  <span className="badge-nomatch">✗ NO MATCH</span>
                  <span className="rule-name">Using default route</span>
                </>
              )}
            </div>

            <div className="result-actions">
              <h4>Actions</h4>
              <ul>
                {testResult.actions.map((action, i) => (
                  <li key={i}>
                    <span className="action">{action.action}</span>
                    <span className="value">→ {action.value}</span>
                  </li>
                ))}
              </ul>
            </div>

            <div className="result-json">
              <h4>Raw Result</h4>
              <pre>{JSON.stringify(testResult, null, 2)}</pre>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
```

---

## FILE 4: frontend/src/services/rulesService.ts

```typescript
// frontend/src/services/rulesService.ts
/**
 * Rules Engine API Service
 * Handles all communication with backend rules API
 */

const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const RULES_ENDPOINT = `${API_BASE}/api/v1/rules`;

export async function fetchRules() {
  const response = await fetch(`${RULES_ENDPOINT}/`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function getRuleById(ruleId: string) {
  const response = await fetch(`${RULES_ENDPOINT}/${ruleId}`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function createRule(rule: any) {
  const response = await fetch(`${RULES_ENDPOINT}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rule),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function updateRule(ruleId: string, rule: any) {
  const response = await fetch(`${RULES_ENDPOINT}/${ruleId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(rule),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function deleteRule(ruleId: string) {
  const response = await fetch(`${RULES_ENDPOINT}/${ruleId}`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function toggleRule(ruleId: string) {
  const response = await fetch(`${RULES_ENDPOINT}/${ruleId}/toggle`, {
    method: 'PATCH',
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function testRule(emailContext: any) {
  const response = await fetch(`${RULES_ENDPOINT}/test`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(emailContext),
  });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}

export async function validateRules() {
  const response = await fetch(`${RULES_ENDPOINT}/validate`);
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.json();
}
```

---

## FILE 5: frontend/src/components/RulesUI.css

```css
/* frontend/src/components/RulesUI.css */

.rules-ui {
  display: flex;
  flex-direction: column;
  gap: 20px;
  padding: 20px;
  background: var(--color-background);
  border-radius: 8px;
}

.rules-header {
  border-bottom: 2px solid var(--color-border);
  padding-bottom: 16px;
}

.rules-header h2 {
  margin: 0 0 8px 0;
  font-size: 24px;
  color: var(--color-text-primary);
}

.rules-header p {
  margin: 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.error-banner {
  padding: 12px 16px;
  background: #fee;
  border-left: 4px solid #f66;
  color: #c33;
  border-radius: 4px;
  font-size: 13px;
}

/* TABS */
.rules-tabs {
  display: flex;
  gap: 8px;
  border-bottom: 1px solid var(--color-border);
}

.tab-button {
  padding: 12px 20px;
  background: transparent;
  border: none;
  border-bottom: 3px solid transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-weight: 500;
  transition: all 0.2s;
  font-size: 13px;
}

.tab-button:hover {
  color: var(--color-text-primary);
}

.tab-button.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}

/* RULES LIST */
.rules-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rule-card {
  border: 1px solid var(--color-border);
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.2s;
}

.rule-card:hover {
  border-color: var(--color-primary-light);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.rule-card.inactive {
  opacity: 0.6;
}

.rule-header {
  padding: 16px;
  background: var(--color-background-secondary);
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  gap: 16px;
}

.rule-title {
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
}

.rule-priority {
  font-weight: bold;
  color: var(--color-primary);
  min-width: 32px;
}

.rule-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.rule-domain {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--color-primary-light);
  border-radius: 4px;
  color: var(--color-primary);
}

.rule-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-btn,
.delete-btn {
  padding: 6px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 500;
  transition: all 0.2s;
}

.toggle-btn.on {
  background: #e8f5e9;
  color: #2e7d32;
}

.toggle-btn.off {
  background: #ffebee;
  color: #c62828;
}

.delete-btn {
  background: #ffebee;
  color: #c62828;
}

.delete-btn:hover {
  background: #ffcdd2;
}

.expand-icon {
  color: var(--color-text-secondary);
  transition: transform 0.2s;
}

.rule-details {
  padding: 16px;
  border-top: 1px solid var(--color-border);
  background: var(--color-background);
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.rule-description {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  font-style: italic;
}

.rule-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-section h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.conditions-list,
.actions-list {
  margin: 0;
  padding-left: 20px;
  list-style: none;
}

.conditions-list li,
.actions-list li {
  padding: 4px 0;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.conditions-list code {
  background: var(--color-background-secondary);
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
}

.action-type {
  font-weight: 600;
  color: var(--color-primary);
}

.action-value {
  color: var(--color-text-secondary);
}

.rule-meta {
  display: flex;
  gap: 16px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
  font-size: 12px;
  color: var(--color-text-secondary);
}

.empty-state {
  text-align: center;
  padding: 40px;
  color: var(--color-text-secondary);
}

.empty-state p {
  margin: 0 0 8px 0;
}

.loading {
  text-align: center;
  padding: 40px;
  color: var(--color-text-secondary);
}
```

---

## FILE 6: frontend/src/components/RuleBuilder.css

```css
/* frontend/src/components/RuleBuilder.css */

.rule-builder {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.builder-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: var(--color-background-secondary);
  border-radius: 8px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.form-group input[type="text"],
.form-group input[type="email"],
.form-group input[type="number"],
.form-group textarea,
.form-group select {
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 13px;
  font-family: inherit;
  background: var(--color-background);
}

.form-group input[type="checkbox"] {
  margin-right: 6px;
}

.form-group small {
  font-size: 11px;
  color: var(--color-text-secondary);
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
  background: var(--color-background);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.form-section h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.condition-row,
.action-row {
  display: grid;
  grid-template-columns: 1fr 1fr 2fr 40px;
  gap: 8px;
  align-items: center;
}

.condition-row select,
.condition-row input,
.action-row select,
.action-row input {
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 12px;
}

.add-btn,
.remove-btn {
  padding: 6px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-background);
  color: var(--color-text-primary);
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;
}

.add-btn:hover {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
}

.remove-btn:hover:not(:disabled) {
  background: #ffebee;
  border-color: #f66;
  color: #c33;
}

.remove-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error-message {
  padding: 8px 12px;
  background: #fee;
  border: 1px solid #fcc;
  border-radius: 4px;
  color: #c33;
  font-size: 12px;
}

.form-actions {
  display: flex;
  gap: 8px;
}

.save-btn {
  flex: 1;
  padding: 10px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.save-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.save-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.builder-preview {
  padding: 16px;
  background: var(--color-background-secondary);
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.builder-preview h3 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
}

.builder-preview pre {
  margin: 0;
  padding: 12px;
  background: var(--color-background);
  border-radius: 4px;
  overflow-x: auto;
  font-size: 11px;
  line-height: 1.5;
  color: var(--color-text-secondary);
}
```

---

## FILE 7: frontend/src/components/RuleTest.css

```css
/* frontend/src/components/RuleTest.css */

.rule-test {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.test-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 16px;
  background: var(--color-background-secondary);
  border-radius: 8px;
  border: 1px solid var(--color-border);
}

.test-form h3 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 600;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.form-group input[type="text"],
.form-group input[type="email"],
.form-group input[type="range"],
.form-group select {
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-size: 12px;
  background: var(--color-background);
}

.test-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border);
}

.test-btn {
  padding: 10px;
  background: var(--color-primary);
  color: white;
  border: none;
  border-radius: 4px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
}

.test-btn:hover:not(:disabled) {
  background: var(--color-primary-dark);
}

.test-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.quick-tests {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.quick-tests label {
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-secondary);
}

.quick-test-btn {
  padding: 6px 8px;
  background: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  color: var(--color-text-primary);
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;
}

.quick-test-btn:hover {
  background: var(--color-primary-light);
  border-color: var(--color-primary);
}

.test-result {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.test-result h3 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
}

.result-card {
  padding: 16px;
  background: var(--color-background-secondary);
  border-radius: 8px;
  border: 2px solid var(--color-border);
}

.result-card.matched {
  border-color: #4caf50;
  background: #f1f8f6;
}

.result-card.no-match {
  border-color: #ffc107;
  background: #fff8f0;
}

.result-status {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid currentColor;
  opacity: 0.5;
}

.badge-match,
.badge-nomatch {
  font-weight: 600;
  font-size: 12px;
  padding: 4px 8px;
  border-radius: 4px;
}

.badge-match {
  background: #4caf50;
  color: white;
}

.badge-nomatch {
  background: #ffc107;
  color: #333;
}

.rule-name {
  font-weight: 600;
  color: var(--color-text-primary);
}

.result-actions {
  margin-bottom: 12px;
}

.result-actions h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
  font-weight: 600;
}

.result-actions ul {
  margin: 0;
  padding-left: 20px;
  list-style: none;
}

.result-actions li {
  padding: 4px 0;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.action {
  font-weight: 600;
  color: var(--color-primary);
  margin-right: 6px;
}

.value {
  color: var(--color-text-secondary);
}

.result-json {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--color-border);
}

.result-json h4 {
  margin: 0 0 8px 0;
  font-size: 12px;
  font-weight: 600;
}

.result-json pre {
  margin: 0;
  padding: 8px;
  background: var(--color-background);
  border-radius: 4px;
  overflow-x: auto;
  font-size: 10px;
  line-height: 1.4;
  color: var(--color-text-secondary);
}
```

---

## Summary: All Frontend Files

| File | Purpose | Size |
|------|---------|------|
| RulesUI.tsx | Main component + rules list | ~400 lines |
| RuleBuilder.tsx | Form to create new rules | ~350 lines |
| RuleTest.tsx | Test engine UI | ~250 lines |
| rulesService.ts | API communication | ~100 lines |
| RulesUI.css | Styling for rules list | ~250 lines |
| RuleBuilder.css | Form styling | ~200 lines |
| RuleTest.css | Test UI styling | ~250 lines |

**Total:** ~1,800 lines of React code + CSS

