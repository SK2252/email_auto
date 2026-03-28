# Rules Engine: Complete Integration Guide
## Backend + Frontend Wiring

**Time to Complete:** 2-3 days  
**Complexity:** Medium  
**Files Created:** 12 total (5 backend + 7 frontend)

---

## ✅ COMPLETE CHECKLIST

### DAY 1: Backend Setup

```
Morning (2-3 hours):
[ ] Step 1.1 — Copy config/rules.json
[ ] Step 1.2 — Copy utils/rules_engine.py
[ ] Step 1.3 — Test rules_engine.py locally
[ ] Step 1.4 — Run unit tests

Afternoon (2-3 hours):
[ ] Step 1.5 — Copy agents/routing_agent.py
[ ] Step 1.6 — Update agents/orchestrator.py
[ ] Step 1.7 — Copy api/routers/v1/rules.py
[ ] Step 1.8 — Update api/main.py
[ ] Step 1.9 — Test API endpoints with curl
```

### DAY 2: Frontend Setup

```
Morning (2-3 hours):
[ ] Step 2.1 — Copy all React components (6 files)
[ ] Step 2.2 — Update frontend/src/pages (or App.tsx) to import RulesUI
[ ] Step 2.3 — Test component rendering
[ ] Step 2.4 — Verify API connections

Afternoon (2-3 hours):
[ ] Step 2.5 — Test rule creation
[ ] Step 2.6 — Test rule evaluation
[ ] Step 2.7 — Test rule toggling/deletion
[ ] Step 2.8 — Integration testing with real emails
```

### DAY 3: Testing & Deployment

```
Morning (2-3 hours):
[ ] Step 3.1 — Full integration test
[ ] Step 3.2 — Performance testing
[ ] Step 3.3 — Error handling verification
[ ] Step 3.4 — Documentation update

Afternoon (2-3 hours):
[ ] Step 3.5 — Staging deployment
[ ] Step 3.6 — User acceptance testing
[ ] Step 3.7 — Production deployment
[ ] Step 3.8 — Monitoring setup
```

---

## 📁 FILE ORGANIZATION

### Backend Files (Copy These in Order)

#### 1. **config/rules.json** ← CREATE FIRST
```
Path: /path/to/project/config/rules.json
Size: ~2 KB
Type: JSON Configuration
What: Rule definitions (4 starter rules included)
Dependencies: None
```

**Action:** Copy the exact JSON from RULES_ENGINE_IMPLEMENTATION.md Step 1

---

#### 2. **utils/rules_engine.py** ← CREATE SECOND
```
Path: /path/to/project/utils/rules_engine.py
Size: ~500 lines
Type: Python Module
What: Core rule evaluation logic
Dependencies: 
  - logging
  - pathlib
  - json
  - typing
```

**Action:** Copy entire file from RULES_ENGINE_IMPLEMENTATION.md Step 2

**Test it:**
```bash
cd /path/to/project
python -c "
from utils.rules_engine import evaluate

# Test case 1
result = evaluate({
    'domain': 'IT Support',
    'type': 'network_issue',
    'priority': 'high',
    'confidence': 0.92
})
print(f'✓ Test 1: {result[\"matched\"]} - {result[\"rule_name\"]}')

# Test case 2
result = evaluate({
    'domain': 'Unknown',
    'type': 'unknown',
    'confidence': 0.5
})
print(f'✓ Test 2: {result[\"matched\"]} - default route')
"
```

Expected output:
```
✓ Test 1: True - IT support escalation
✓ Test 2: True - default route
```

---

#### 3. **agents/routing_agent.py** ← CREATE THIRD
```
Path: /path/to/project/agents/routing_agent.py
Size: ~250 lines
Type: LangGraph Node
What: Integrates rules engine into AG-03
Dependencies:
  - utils.rules_engine
  - utils.gmail_label_manager
  - LangGraph
```

**Action:** Copy entire file from RULES_ENGINE_IMPLEMENTATION.md Step 3

---

#### 4. **agents/orchestrator.py** ← UPDATE EXISTING
```
Path: /path/to/project/agents/orchestrator.py
What: Wire routing_agent into StateGraph
```

**Action:** Add these lines to your existing orchestrator.py:

```python
# At the top (imports)
from agents.routing_agent import routing_agent  # ← ADD THIS

# In build_orchestrator() function:
def build_orchestrator():
    graph = StateGraph(InboxState)
    
    # Add nodes
    graph.add_node("intake", intake_agent)
    graph.add_node("classification", classification_agent)
    graph.add_node("routing", routing_agent)  # ← ADD THIS
    graph.add_node("response", response_agent)
    # ... rest of nodes ...
    
    # Add edges
    graph.add_edge("START", "intake")
    graph.add_edge("intake", "classification")
    graph.add_edge("classification", "routing")  # ← CHANGE THIS
    graph.add_edge("routing", "response")  # ← CHANGE THIS
    # ... rest of edges ...
    
    return graph.compile()
```

---

#### 5. **api/routers/v1/rules.py** ← CREATE FOURTH
```
Path: /path/to/project/api/routers/v1/rules.py
Size: ~500 lines
Type: FastAPI Router
What: REST API endpoints for rules
Dependencies:
  - FastAPI
  - Pydantic
  - utils.rules_engine
```

**Action:** Copy entire file from RULES_ENGINE_IMPLEMENTATION.md Step 4

---

#### 6. **api/main.py** ← UPDATE EXISTING
```
Path: /path/to/project/api/main.py
What: Register rules router
```

**Action:** Add these lines:

```python
# At the top
from api.routers.v1 import rules  # ← ADD THIS

# In app creation
app = FastAPI()

# Include routers
app.include_router(rules.router, prefix="/api/v1")  # ← ADD THIS

# ... rest of your app ...
```

---

### Frontend Files (Copy These in Order)

#### 7. **frontend/src/services/rulesService.ts**
```
Path: /path/to/frontend/src/services/rulesService.ts
Size: ~150 lines
Type: TypeScript Service
What: API communication
Dependencies:
  - fetch API
  - React environment
```

**Action:** Create new file and copy from RULES_ENGINE_FRONTEND.tsx

---

#### 8. **frontend/src/components/RulesUI.tsx**
```
Path: /path/to/frontend/src/components/RulesUI.tsx
Size: ~400 lines
Type: React Component
What: Main rules dashboard
Dependencies:
  - React
  - rulesService
```

**Action:** Create new file and copy from RULES_ENGINE_FRONTEND.tsx

---

#### 9. **frontend/src/components/RuleBuilder.tsx**
```
Path: /path/to/frontend/src/components/RuleBuilder.tsx
Size: ~350 lines
Type: React Component
What: Form to create/edit rules
Dependencies:
  - React
  - rulesService
```

**Action:** Create new file and copy from RULES_ENGINE_FRONTEND.tsx

---

#### 10. **frontend/src/components/RuleTest.tsx**
```
Path: /path/to/frontend/src/components/RuleTest.tsx
Size: ~250 lines
Type: React Component
What: Test rules with simulated emails
Dependencies:
  - React
  - rulesService
```

**Action:** Create new file and copy from RULES_ENGINE_FRONTEND.tsx

---

#### 11-13. **CSS Files** (3 files)
```
- frontend/src/components/RulesUI.css (250 lines)
- frontend/src/components/RuleBuilder.css (200 lines)
- frontend/src/components/RuleTest.css (250 lines)
```

**Action:** Create each file and copy styles from RULES_ENGINE_FRONTEND.tsx

---

#### 14. **Update frontend App** (App.tsx or main routing)
```
Path: /path/to/frontend/src/App.tsx (or pages/index.tsx)
```

**Action:** Import and add RulesUI to your app:

```typescript
import RulesUI from './components/RulesUI';

export default function App() {
  return (
    <div className="app">
      {/* ... other pages/routes ... */}
      
      <Route path="/rules" element={<RulesUI />} />
      
      {/* ... */}
    </div>
  );
}
```

---

## 🧪 TESTING COMMANDS

### Backend Testing

```bash
# Test 1: Validate rules.json syntax
python -m json.tool config/rules.json

# Test 2: Test rules engine directly
python -c "
from utils.rules_engine import evaluate, load_rules
rules = load_rules()
print(f'Loaded {len(rules)} rules')
result = evaluate({'domain': 'IT Support', 'type': 'network_issue', 'priority': 'high', 'confidence': 0.92})
print(f'Matched: {result[\"matched\"]}, Rule: {result[\"rule_name\"]}')
"

# Test 3: Start FastAPI server
uvicorn api.main:app --reload --port 8000

# Test 4: List all rules (curl)
curl http://localhost:8000/api/v1/rules/

# Test 5: Test a rule (curl)
curl -X POST http://localhost:8000/api/v1/rules/test \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "IT Support",
    "type": "network_issue",
    "priority": "high",
    "confidence": 0.92
  }'

# Test 6: Validate all rules
curl http://localhost:8000/api/v1/rules/validate
```

### Frontend Testing

```bash
# Test 1: Start React dev server
cd frontend
npm start

# Test 2: Navigate to rules UI
# Open: http://localhost:3000/rules

# Test 3: In browser console, test API
fetch('http://localhost:8000/api/v1/rules/')
  .then(r => r.json())
  .then(d => console.log(d))

# Test 4: Create a rule via UI
# - Click "New Rule" tab
# - Fill in form
# - Click "Save Rule"

# Test 5: Test rules via UI
# - Click "Test Engine" tab
# - Adjust email context
# - Click "Run Test"
```

---

## 🔌 API ENDPOINTS REFERENCE

All endpoints are relative to `http://localhost:8000/api/v1`

### GET /rules/
**Get all rules**
```bash
curl http://localhost:8000/api/v1/rules/
```

Response:
```json
{
  "rules": [...],
  "total": 4
}
```

---

### GET /rules/{rule_id}
**Get specific rule**
```bash
curl http://localhost:8000/api/v1/rules/rule-001
```

---

### POST /rules/
**Create new rule**
```bash
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Rule",
    "priority": 5,
    "domain": "IT Support",
    "conditions": [...],
    "actions": [...]
  }'
```

---

### PUT /rules/{rule_id}
**Update rule**
```bash
curl -X PUT http://localhost:8000/api/v1/rules/rule-001 \
  -H "Content-Type: application/json" \
  -d '{ ... updated rule ... }'
```

---

### DELETE /rules/{rule_id}
**Delete rule**
```bash
curl -X DELETE http://localhost:8000/api/v1/rules/rule-001
```

---

### PATCH /rules/{rule_id}/toggle
**Enable/disable rule**
```bash
curl -X PATCH http://localhost:8000/api/v1/rules/rule-001/toggle
```

---

### POST /rules/test
**Test rule with email context**
```bash
curl -X POST http://localhost:8000/api/v1/rules/test \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "IT Support",
    "type": "network_issue",
    "priority": "high",
    "sentiment": "negative",
    "confidence": 0.92,
    "sender": "user@company.com",
    "subject": "VPN not working"
  }'
```

---

### GET /rules/validate
**Validate all rules for errors**
```bash
curl http://localhost:8000/api/v1/rules/validate
```

---

## 📊 DATABASE SCHEMA (if using database later)

When you migrate from JSON to database, use this schema:

```sql
CREATE TABLE rules (
  id VARCHAR(50) PRIMARY KEY,
  name VARCHAR(255) NOT NULL UNIQUE,
  description TEXT,
  priority INT DEFAULT 99,
  domain VARCHAR(100),
  match_mode VARCHAR(10), -- 'all' or 'any'
  stop_on_match BOOLEAN DEFAULT true,
  active BOOLEAN DEFAULT true,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  created_by VARCHAR(100),
  updated_by VARCHAR(100)
);

CREATE TABLE rule_conditions (
  id SERIAL PRIMARY KEY,
  rule_id VARCHAR(50) NOT NULL,
  field VARCHAR(100),
  operator VARCHAR(50),
  value TEXT,
  FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE
);

CREATE TABLE rule_actions (
  id SERIAL PRIMARY KEY,
  rule_id VARCHAR(50) NOT NULL,
  action VARCHAR(100),
  value TEXT,
  FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE
);

CREATE INDEX idx_rules_priority ON rules(priority);
CREATE INDEX idx_rules_domain ON rules(domain);
CREATE INDEX idx_rules_active ON rules(active);
```

---

## 🚀 DEPLOYMENT CHECKLIST

Before deploying to production:

- [ ] All rules validated via /rules/validate endpoint
- [ ] Email context fields match your AG-02 Classification output
- [ ] All actions are implemented in AG-03 Routing Agent
- [ ] Slack channels exist (if using notify_slack action)
- [ ] Gmail label paths are correct
- [ ] Rules have been tested with real emails
- [ ] Error handling works (DLQ, fallback routes)
- [ ] Performance tested (100+ rules, 1000+ evaluations/sec)
- [ ] Audit logging enabled
- [ ] Monitoring/alerting configured

---

## 🐛 COMMON ISSUES & SOLUTIONS

### Issue 1: "Rule not found" in API
**Cause:** Rule ID doesn't match JSON
**Solution:** Use exact rule ID from /rules/ endpoint

### Issue 2: Rules not matching
**Cause:** Email context fields don't match condition field names
**Solution:** Print email_context in routing_agent.py, verify field names

### Issue 3: Frontend can't connect to backend
**Cause:** CORS or API URL misconfiguration
**Solution:** 
```typescript
// In rulesService.ts
const API_BASE = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// In .env file
REACT_APP_API_URL=http://localhost:8000
```

### Issue 4: Rules engine slow
**Cause:** Too many rules or complex conditions
**Solution:** 
- Add indexes on priority/domain
- Use match_mode="any" instead of "all"
- Cache evaluated rules

### Issue 5: Actions not executing
**Cause:** Action not implemented in routing_agent.py
**Solution:** Check routing_agent.py match statement covers all action types

---

## 📈 NEXT STEPS

After successful Rules Engine deployment:

1. **Add Agent Health Monitoring** (Sprint 1)
   - Agent heartbeat every 30 seconds
   - Alert if agent missing 3 consecutive heartbeats

2. **Add Event-Driven Triggers** (Sprint 1)
   - Replace polling with event bus
   - Webhook triggers immediately process email

3. **Add Human Approval Loop** (Sprint 1)
   - Hold queue for responses
   - Admin dashboard to approve/reject

4. **Migrate to Database** (Sprint 2)
   - Move rules.json to PostgreSQL
   - Add version history/audit trail

5. **Add Rule Templates** (Sprint 2)
   - Pre-built rules for common scenarios
   - One-click rule creation

---

## ✅ SUCCESS CRITERIA

You'll know it's working when:

✅ Rules list loads in UI  
✅ Can create new rule from form  
✅ Rule appears in list immediately  
✅ Test Engine shows correct match  
✅ Real email follows matched rule's actions  
✅ Toggle rule on/off works  
✅ Delete rule works  
✅ All CRUD operations complete in <1 second  

---

**Total Implementation Time:** 2-3 days  
**Difficulty:** Medium  
**Value:** High (enables non-technical routing management)

Good luck! 🚀
