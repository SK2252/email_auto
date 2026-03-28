import { useState, useEffect } from "react"

const API = "http://localhost:8000/api/v1/rules/default"

const CATEGORIES = [
  "network_issue","leave_request","billing_complaint",
  "security_incident","invoice_dispute","unknown","password_reset",
]
const PRIORITIES  = ["high","medium","low"]
const OPERATORS   = ["is","is_not","in","not_in","contains","starts_with","greater_than","less_than"]
const ACTIONS_LIST = ["route_to","set_sla","send_ack","notify_slack","notify_email","hold_for_review","apply_label"]

type Condition = { field: string; operator: string; value: string }
type Action    = { action: string; value: string }
type Rule      = {
  name: string; priority: string; domain: string
  match_mode: "all"|"any"; stop_on_match: boolean; active: boolean
  conditions: Condition[]; actions: Action[]
}

// ─── badge helpers ───────────────────────────────────────────────────────────
const domainColor: Record<string,string> = {
  "IT Support":"bg-teal-50 text-teal-800",
  "HR":"bg-blue-50 text-blue-800",
  "Customer Support":"bg-amber-50 text-amber-800",
  "any":"bg-gray-100 text-gray-600",
}
const statusColor = (active: boolean) =>
  active ? "bg-green-50 text-green-800" : "bg-gray-100 text-gray-500"

// ─── Simulator paths ──────────────────────────────────────────────────────────
const STATIC_MATRIX: Record<string,string> = {
  network_issue:    "IT Support/Network Ops Team",
  security_incident:"IT Support/Security Team",
  leave_request:    "HR/HR Operations",
  invoice_dispute:  "Customer Support/Customer Issues",
  password_reset:   "IT Support/General IT Queue",
  billing_complaint:"Customer Support/Customer Issues",
}

export default function RulesEngine() {
  const [tab, setTab]         = useState<"list"|"builder"|"simulator">("list")
  const [rules, setRules]     = useState<Rule[]>([])
  const [version, setVersion] = useState(0)
  const [loading, setLoading] = useState(false)
  const [expanded, setExpanded] = useState<string|null>(null)
  const [domains, setDomains] = useState<string[]>(["IT Support","HR","Customer Support"])

  // builder state
  const [bName,    setBName]    = useState("")
  const [bPri,     setBPri]     = useState("medium")
  const [bDomain,  setBDomain]  = useState("IT Support")
  const [bMode,    setBMode]    = useState<"all"|"any">("all")
  const [bStop,    setBStop]    = useState(true)
  const [bConds,   setBConds]   = useState<Condition[]>([
    { field:"category", operator:"is", value:"" }
  ])
  const [bActions, setBActions] = useState<Action[]>([
    { action:"route_to", value:"" }
  ])
  const [saving, setSaving]   = useState(false)
  const [saveMsg, setSaveMsg] = useState("")

  // simulator state
  const [simCat,    setSimCat]    = useState("network_issue")
  const [simPri,    setSimPri]    = useState("high")
  const [simDomain, setSimDomain] = useState("IT Support")
  const [simRules,  setSimRules]  = useState<"yes"|"no">("yes")
  const [simRunning, setSimRunning] = useState(false)
  const [simSteps,  setSimSteps]  = useState<any[]>([])
  const [simFinal,  setSimFinal]  = useState<any>(null)

  useEffect(() => { fetchRules() }, [])

  async function fetchRules() {
    setLoading(true)
    try {
      const r = await fetch(API)
      const d = await r.json()
      setRules(d.rules || [])
      setVersion(d.version || 0)
    } catch { setRules([]) }
    try {
      const dr = await fetch(API.replace('/default', '').replace('/api/v1/rules', '/api/v1/rules/domains'))
      const dd = await dr.json()
      if (dd.domains) setDomains(dd.domains)
    } catch { }
    setLoading(false)
  }

  async function saveRules(updated: Rule[]) {
    setSaving(true); setSaveMsg("")
    try {
      const r = await fetch(API, {
        method:"PUT",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ rules: updated }),
      })
      const d = await r.json()
      if (!r.ok) throw new Error(d.detail || "Save failed")
      setSaveMsg(d.message)
      setRules(updated)
      setVersion(v => v + 1)
      setTimeout(() => setSaveMsg(""), 4000)
    } catch(e: any) { setSaveMsg("Error: " + e.message) }
    setSaving(false)
  }

  function addRule() {
    if (!bName.trim()) { alert("Rule name required"); return }
    const newRule: Rule = {
      name: bName, priority: bPri, domain: bDomain,
      match_mode: bMode, stop_on_match: bStop, active: true,
      conditions: bConds.filter(c => c.value),
      actions:    bActions.filter(a => a.value),
    }
    saveRules([...rules, newRule])
    setBName(""); setBPri("medium")
    setBConds([{ field:"category", operator:"is", value:"" }])
    setBActions([{ action:"route_to", value:"" }])
    setTab("list")
  }

  function deleteRule(name: string) {
    if (!confirm(`Delete rule "${name}"?`)) return
    saveRules(rules.filter(r => r.name !== name))
  }

  function toggleRule(name: string) {
    saveRules(rules.map(r =>
      r.name === name ? { ...r, active: !r.active } : r
    ))
  }

  // ── Simulator ──────────────────────────────────────────────────────────────
  async function runSimulator() {
    setSimRunning(true)
    setSimSteps([])
    setSimFinal(null)
    const steps: any[] = []

    const delay = (ms: number) =>
      new Promise<void>(res => setTimeout(res, ms))

    // Step 1 — Classification
    steps.push({ id:"class", label:"AG-02 — Classification agent",
                 tag:"existing", status:"active", logs:[] })
    setSimSteps([...steps])
    await delay(350)
    steps[0].logs = [
      { dot:"info", text:"Groq llama-3.3-70b called" },
      { dot:"info", text:"category →", val: simCat },
      { dot:"info", text:"priority →", val: simPri },
      { dot:"info", text:"domain →",   val: simDomain },
    ]
    steps[0].status = "matched"
    setSimSteps([...steps])
    await delay(300)

    // Step 2 — Rules engine
    steps.push({ id:"rules", label:"Step 0.5 — rules_engine.evaluate()",
                 tag:"new", status:"active", logs:[] })
    setSimSteps([...steps])

    let rulesMatched = false
    let finalTeam = ""
    let finalSLA  = ""
    let finalSource = ""

    if (simRules === "no") {
      await delay(200)
      steps[1].logs = [
        { dot:"warn", text:"Redis: MISS — no rules:{tenant_id} key" },
        { dot:"warn", text:"Postgres: rules_versions is empty" },
        { dot:"info", text:"evaluate() returns None → fall through" },
      ]
      steps[1].status = "skipped"
      steps[1].tag    = "skip"
    } else {
      steps[1].logs = [{ dot:"info", text:"Redis: checking rules:default..." }]
      setSimSteps([...steps])
      await delay(300)

      // Check if any rule matches simulation context (sorted by priority)
      const pMap: Record<string, number> = { high: 0, medium: 1, low: 2 }
      const sorted = [...rules]
        .filter(r => r.active)
        .sort((a,b) => (pMap[a.priority] ?? 3) - (pMap[b.priority] ?? 3))

      const matchedRule = sorted.find(r =>
        r.conditions.some(c =>
          c.field === "category" &&
          c.operator === "is" &&
          c.value.toLowerCase() === simCat.toLowerCase()
        )
      )

      if (matchedRule) {
        rulesMatched = true
        const routeAction = matchedRule.actions.find(a => a.action === "route_to")
        const slaAction   = matchedRule.actions.find(a => a.action === "set_sla")
        const slackAction = matchedRule.actions.find(a => a.action === "notify_slack")
        if (routeAction) finalTeam = routeAction.value
        if (slaAction)   finalSLA  = slaAction.value
        finalSource = "rules_engine"

        steps[1].logs.push(
          { dot:"ok", text:"Redis HIT — rules loaded" },
          { dot:"ok", text:"Rule matched →", val: matchedRule.name },
          ...matchedRule.actions.map(a => ({
            dot:"ok", text:`action: ${a.action} →`, val: String(a.value)
          }))
        )
        steps[1].status = "matched"
        steps[1].tag    = "match"
      } else {
        steps[1].logs.push(
          { dot:"info", text:"Redis HIT — rules loaded" },
          { dot:"err",  text:"No rule matched category:", val: simCat },
          { dot:"info", text:"evaluate() returns None → fall through" },
        )
        steps[1].status = "skipped"
        steps[1].tag    = "nomatch"
      }
    }
    setSimSteps([...steps])
    await delay(250)

    // Step 3 — Static matrix
    steps.push({ id:"matrix", label:"Step 1 — _rule_based_route() static matrix",
                 tag:"existing", status:"active", logs:[] })
    setSimSteps([...steps])

    if (rulesMatched) {
      steps[2].logs = [{ dot:"warn", text:"Skipped — rules engine already matched" }]
      steps[2].status = "skipped"; steps[2].tag = "skip"
    } else {
      await delay(300)
      const staticMatch = STATIC_MATRIX[simCat]
      if (staticMatch) {
        finalTeam   = staticMatch
        finalSLA    = finalSLA || "8h"
        finalSource = "static_matrix"
        steps[2].logs = [
          { dot:"info", text:"Looking up domain_config[routing_rules]..." },
          { dot:"ok",   text:"Rule found →", val: staticMatch },
        ]
        steps[2].status = "matched"; steps[2].tag = "match"
        rulesMatched = true
      } else {
        steps[2].logs = [
          { dot:"info", text:"Looking up domain_config[routing_rules]..." },
          { dot:"err",  text:"No entry for category:", val: simCat },
          { dot:"info", text:"Fall through to LLM fallback" },
        ]
        steps[2].status = "skipped"; steps[2].tag = "nomatch"
      }
    }
    setSimSteps([...steps])
    await delay(250)

    // Step 4 — LLM fallback
    steps.push({ id:"llm", label:"Step 2 — _llm_fallback_route() Gemini",
                 tag:"existing", status:"active", logs:[] })
    setSimSteps([...steps])

    if (rulesMatched) {
      steps[3].logs = [{ dot:"warn", text:"Skipped — already routed" }]
      steps[3].status = "skipped"; steps[3].tag = "skip"
    } else {
      steps[3].logs = [{ dot:"info", text:"Calling Gemini 2.5 Flash-Lite (max 2 retries)..." }]
      setSimSteps([...steps])
      await delay(500)
      finalTeam   = "Others/Uncategorised"
      finalSLA    = "24h"
      finalSource = "llm_fallback"
      steps[3].logs.push({ dot:"ok", text:"LLM returned →", val:"Others/Uncategorised" })
      steps[3].status = "matched"
    }
    setSimSteps([...steps])
    await delay(200)

    // Step 5 — Post routing
    steps.push({ id:"post", label:"Step 3 — post-routing actions",
                 tag:"existing", status:"active", logs:[] })
    setSimSteps([...steps])
    await delay(200)
    steps[4].logs = [
      { dot:"info", text:"Writing routing_decision to Postgres..." },
      { dot:"ok",   text:"Gmail label →", val: finalTeam },
      { dot:"ok",   text:"Source →",      val: finalSource },
      { dot:"ok",   text:"SLA bucket →",  val: finalSLA || "8h" },
    ]
    steps[4].status = "matched"
    setSimSteps([...steps])

    setSimFinal({ team: finalTeam, source: finalSource,
                  sla: finalSLA || "8h", domain: simDomain })
    setSimRunning(false)
  }

  // ── Render helpers ─────────────────────────────────────────────────────────
  const dotColor: Record<string,string> = {
    info:"bg-blue-400", ok:"bg-green-500",
    warn:"bg-amber-400", err:"bg-red-400",
  }
  const stepBorder: Record<string,string> = {
    active:"border-blue-300",
    matched:"border-green-400",
    skipped:"border-gray-200 opacity-50",
  }
  const tagStyle: Record<string,string> = {
    new:     "bg-purple-50 text-purple-800",
    existing:"bg-teal-50 text-teal-800",
    skip:    "bg-gray-100 text-gray-500",
    match:   "bg-green-50 text-green-800",
    nomatch: "bg-red-50 text-red-700",
  }

  return (
    <div className="flex-1 overflow-y-auto">
    <div className="p-4 max-w-4xl mx-auto pb-16">

      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-lg font-medium">Rules engine</h1>
          <p className="text-sm text-gray-500">
            {rules.length} rules · version {version}
          </p>
        </div>
        <button
          onClick={() => setTab("builder")}
          className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50"
        >
          + New rule
        </button>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b mb-4">
        {(["list","builder","simulator"] as const).map(t => (
          <button key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm border-b-2 transition-colors ${
              tab === t
                ? "border-gray-900 font-medium text-gray-900"
                : "border-transparent text-gray-500 hover:text-gray-700"
            }`}
          >
            {t === "list" ? `Active rules (${rules.length})`
             : t === "builder" ? "Rule builder"
             : "Pipeline simulator"}
          </button>
        ))}
      </div>

      {/* Save message */}
      {saveMsg && (
        <div className={`mb-3 px-3 py-2 rounded-lg text-sm ${
          saveMsg.startsWith("Error")
            ? "bg-red-50 text-red-700 border border-red-200"
            : "bg-green-50 text-green-700 border border-green-200"
        }`}>
          {saveMsg}
        </div>
      )}

      {/* ── TAB: Active Rules ── */}
      {tab === "list" && (
        <div>
          {loading && (
            <p className="text-sm text-gray-400 text-center py-8">Loading...</p>
          )}
          {!loading && rules.length === 0 && (
            <div className="text-center py-12 text-gray-400">
              <p className="text-sm">No rules configured.</p>
              <p className="text-xs mt-1">
                System uses static matrix + LLM fallback only.
              </p>
              <button
                onClick={() => setTab("builder")}
                className="mt-3 px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50 text-gray-600"
              >
                Create first rule
              </button>
            </div>
          )}
          {rules.map(rule => (
            <div key={rule.name}
              className={`border rounded-xl mb-2 overflow-hidden transition-all ${
                !rule.active ? "opacity-50" : ""
              }`}
            >
              {/* Rule header */}
              <div
                className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-gray-50"
                onClick={() => setExpanded(
                  expanded === rule.name ? null : rule.name
                )}
              >
                <div>
                  <span className="text-sm font-medium">{rule.name}</span>
                  <span className="ml-2 text-xs text-gray-400">
                    Priority {rule.priority}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                    ${domainColor[rule.domain] || domainColor["any"]}`}>
                    {rule.domain}
                  </span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                    ${statusColor(rule.active)}`}>
                    {rule.active ? "Active" : "Off"}
                  </span>
                  {/* Toggle */}
                  <button
                    onClick={e => { e.stopPropagation(); toggleRule(rule.name) }}
                    className={`relative w-8 h-4 rounded-full transition-colors ${
                      rule.active ? "bg-green-500" : "bg-gray-300"
                    }`}
                  >
                    <span className={`absolute top-0.5 w-3 h-3 bg-white rounded-full
                      transition-transform ${
                        rule.active ? "translate-x-4" : "translate-x-0.5"
                      }`}
                    />
                  </button>
                </div>
              </div>

              {/* Rule detail */}
              {expanded === rule.name && (
                <div className="border-t px-4 py-3 text-sm space-y-3">
                  <div>
                    <p className="text-xs text-gray-500 mb-1 font-medium uppercase tracking-wide">
                      IF {rule.match_mode === "all" ? "ALL" : "ANY"} of these match
                    </p>
                    <div className="bg-gray-50 rounded-lg p-3 space-y-1">
                      {rule.conditions.map((c, i) => (
                        <div key={i} className="flex gap-2 text-xs">
                          <span className="bg-white border px-2 py-0.5 rounded-full">{c.field}</span>
                          <span className="text-gray-400">{c.operator}</span>
                          <span className="bg-white border px-2 py-0.5 rounded-full">{c.value}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 mb-1 font-medium uppercase tracking-wide">
                      THEN
                    </p>
                    <div className="space-y-1">
                      {rule.actions.map((a, i) => (
                        <div key={i} className="flex gap-2 text-xs items-center">
                          <span className="w-5 h-5 bg-blue-50 text-blue-700 rounded
                            flex items-center justify-center font-mono">→</span>
                          <span className="font-medium">{a.action}:</span>
                          <span className="text-gray-600">{String(a.value)}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="flex gap-2 pt-1 border-t justify-end">
                    <button
                      onClick={() => deleteRule(rule.name)}
                      className="text-xs px-3 py-1 border border-red-200
                        text-red-600 rounded-lg hover:bg-red-50"
                    >
                      Delete
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── TAB: Rule Builder ── */}
      {tab === "builder" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Rule name *
              </label>
              <input
                value={bName}
                onChange={e => setBName(e.target.value)}
                placeholder="e.g. IT escalation"
                className="w-full text-sm border rounded-lg px-3 py-2"
              />
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Priority</label>
              <select 
                value={bPri}
                onChange={e => setBPri(e.target.value)}
                className="w-full text-sm border rounded-lg px-3 py-2"
              >
                {PRIORITIES.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-xs text-gray-500 mb-1">Domain</label>
              <select
                value={bDomain}
                onChange={e => setBDomain(e.target.value)}
                className="w-full text-sm border rounded-lg px-3 py-2"
              >
                {[...domains, "any"].map(d =>
                  <option key={d}>{d}</option>
                )}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Match mode
              </label>
              <select
                value={bMode}
                onChange={e => setBMode(e.target.value as "all"|"any")}
                className="w-full text-sm border rounded-lg px-3 py-2"
              >
                <option value="all">ALL conditions (AND)</option>
                <option value="any">ANY condition (OR)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Stop on match
              </label>
              <select
                value={String(bStop)}
                onChange={e => setBStop(e.target.value === "true")}
                className="w-full text-sm border rounded-lg px-3 py-2"
              >
                <option value="true">Yes — stop evaluating</option>
                <option value="false">No — continue</option>
              </select>
            </div>
          </div>

          {/* Conditions */}
          <div>
            <label className="block text-xs text-gray-500 mb-2 font-medium">
              Conditions
            </label>
            {bConds.map((c, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <select
                  value={c.field}
                  onChange={e => {
                    const n = [...bConds]
                    n[i] = { ...n[i], field: e.target.value }
                    setBConds(n)
                  }}
                  className="text-xs border rounded-lg px-2 py-1.5 w-32"
                >
                  {["category","priority","domain_id","sender","subject"].map(f =>
                    <option key={f}>{f}</option>
                  )}
                </select>
                <select
                  value={c.operator}
                  onChange={e => {
                    const n = [...bConds]
                    n[i] = { ...n[i], operator: e.target.value }
                    setBConds(n)
                  }}
                  className="text-xs border rounded-lg px-2 py-1.5 w-28"
                >
                  {OPERATORS.map(o => <option key={o}>{o}</option>)}
                </select>
                <input
                  value={c.value}
                  onChange={e => {
                    const n = [...bConds]
                    n[i] = { ...n[i], value: e.target.value }
                    setBConds(n)
                  }}
                  placeholder="value"
                  className="flex-1 text-xs border rounded-lg px-2 py-1.5"
                />
                <button
                  onClick={() => setBConds(bConds.filter((_, j) => j !== i))}
                  className="text-gray-400 hover:text-gray-600 px-1"
                >×</button>
              </div>
            ))}
            <button
              onClick={() => setBConds([...bConds,
                { field:"category", operator:"is", value:"" }])}
              className="text-xs border border-dashed rounded-lg px-3 py-1.5
                text-gray-500 hover:bg-gray-50 w-full"
            >
              + add condition
            </button>
          </div>

          {/* Actions */}
          <div>
            <label className="block text-xs text-gray-500 mb-2 font-medium">
              Actions
            </label>
            {bActions.map((a, i) => (
              <div key={i} className="flex gap-2 mb-2">
                <select
                  value={a.action}
                  onChange={e => {
                    const n = [...bActions]
                    n[i] = { ...n[i], action: e.target.value }
                    setBActions(n)
                  }}
                  className="text-xs border rounded-lg px-2 py-1.5 w-36"
                >
                  {ACTIONS_LIST.map(ac => <option key={ac}>{ac}</option>)}
                </select>
                <input
                  value={a.value}
                  onChange={e => {
                    const n = [...bActions]
                    n[i] = { ...n[i], value: e.target.value }
                    setBActions(n)
                  }}
                  placeholder="value / target"
                  className="flex-1 text-xs border rounded-lg px-2 py-1.5"
                />
                <button
                  onClick={() => setBActions(bActions.filter((_,j) => j !== i))}
                  className="text-gray-400 hover:text-gray-600 px-1"
                >×</button>
              </div>
            ))}
            <button
              onClick={() => setBActions([...bActions,
                { action:"route_to", value:"" }])}
              className="text-xs border border-dashed rounded-lg px-3 py-1.5
                text-gray-500 hover:bg-gray-50 w-full"
            >
              + add action
            </button>
          </div>

          {/* JSON preview */}
          <div>
            <label className="block text-xs text-gray-500 mb-1">
              Live JSON preview
            </label>
            <pre className="bg-gray-50 rounded-lg p-3 text-xs text-gray-500
              overflow-auto max-h-40 whitespace-pre-wrap">
              {JSON.stringify({
                name: bName || "rule_name",
                priority: bPri, domain: bDomain,
                match_mode: bMode, stop_on_match: bStop,
                active: true,
                conditions: bConds,
                actions: bActions,
              }, null, 2)}
            </pre>
          </div>

          <div className="flex gap-2 justify-end">
            <button
              onClick={() => setTab("list")}
              className="px-3 py-1.5 text-sm border rounded-lg hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={addRule}
              disabled={saving}
              className="px-4 py-1.5 text-sm bg-gray-900 text-white
                rounded-lg hover:opacity-85 disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save rule"}
            </button>
          </div>
        </div>
      )}

      {/* ── TAB: Pipeline Simulator ── */}
      {tab === "simulator" && (
        <div>
          {/* Controls — no confidence or sentiment */}
          <div className="grid grid-cols-2 gap-3 mb-4">
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Email category
              </label>
              <select
                value={simCat}
                onChange={e => setSimCat(e.target.value)}
                className="w-full text-sm border rounded-lg px-3 py-2"
              >
                {CATEGORIES.map(c => <option key={c}>{c}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Priority</label>
              <select
                value={simPri}
                onChange={e => setSimPri(e.target.value)}
                className="w-full text-sm border rounded-lg px-3 py-2"
              >
                {PRIORITIES.map(p => <option key={p}>{p}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">Domain</label>
              <select
                value={simDomain}
                onChange={e => setSimDomain(e.target.value)}
                className="w-full text-sm border rounded-lg px-3 py-2"
              >
                {domains.map(d => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="block text-xs text-gray-500 mb-1">
                Rules in DB?
              </label>
              <select
                value={simRules}
                onChange={e => setSimRules(e.target.value as "yes"|"no")}
                className="w-full text-sm border rounded-lg px-3 py-2"
              >
                <option value="yes">Yes — rules configured</option>
                <option value="no">No — no rules yet</option>
              </select>
            </div>
          </div>

          <button
            onClick={runSimulator}
            disabled={simRunning}
            className="w-full py-2.5 text-sm font-medium bg-gray-900 text-white
              rounded-xl mb-4 hover:opacity-85 disabled:opacity-50"
          >
            {simRunning ? "Running..." : "Run email through pipeline"}
          </button>

          {/* Pipeline steps */}
          {simSteps.map(step => (
            <div key={step.id}
              className={`border rounded-xl mb-2 overflow-hidden transition-all
                ${stepBorder[step.status] || "border-gray-200"}`}
            >
              <div className="flex items-center gap-3 px-4 py-3">
                <div className={`w-6 h-6 rounded-full flex items-center justify-center
                  text-xs font-medium border flex-shrink-0 ${
                  step.status === "active"
                    ? "bg-blue-50 text-blue-700 border-blue-300"
                  : step.status === "matched"
                    ? "bg-green-50 text-green-700 border-green-300"
                  : "bg-gray-50 text-gray-400 border-gray-200"
                }`}>
                  {step.status === "matched" ? "✓" : "·"}
                </div>
                <span className="text-sm font-medium flex-1">{step.label}</span>
                <span className={`text-xs px-2 py-0.5 rounded-full font-medium
                  ${tagStyle[step.tag] || tagStyle["existing"]}`}>
                  {step.tag}
                </span>
              </div>
              {step.logs?.length > 0 && (
                <div className="border-t px-4 py-2.5 space-y-1">
                  {step.logs.map((log: any, i: number) => (
                    <div key={i} className="flex gap-2 items-start text-xs">
                      <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0
                        ${dotColor[log.dot] || "bg-gray-300"}`}
                      />
                      <span className="text-gray-500">
                        {log.text}{" "}
                        {log.val && (
                          <span className="font-medium text-gray-800">
                            {log.val}
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}

          {/* Final result */}
          {simFinal && (
            <div className="border-2 border-green-300 rounded-xl p-4 mt-2">
              <p className="text-xs text-gray-500 mb-3">Final routing decision</p>
              <div className="grid grid-cols-2 gap-3">
                {[
                  { label:"Routed to",  val: simFinal.team },
                  { label:"Source",     val: simFinal.source },
                  { label:"SLA bucket", val: simFinal.sla },
                  { label:"Domain",     val: simFinal.domain },
                ].map(item => (
                  <div key={item.label}
                    className="bg-gray-50 rounded-lg p-3">
                    <p className="text-xs text-gray-400">{item.label}</p>
                    <p className="text-sm font-medium mt-0.5">{item.val}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
    </div>
  )
}
