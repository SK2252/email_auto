# Rules Engine Implementation - Quick Reference

**Status:** Ready to implement  
**Total Files:** 14  
**Implementation Time:** 2-3 days  
**Complexity:** Medium

---

## 📋 ALL FILES YOU NEED TO CREATE/UPDATE

### BACKEND (6 files) - Copy & Paste Ready

| # | File | Type | Action | Source |
|---|------|------|--------|--------|
| 1 | config/rules.json | JSON | **CREATE** | RULES_ENGINE_IMPLEMENTATION.md, Step 1 |
| 2 | utils/rules_engine.py | Python | **CREATE** | RULES_ENGINE_IMPLEMENTATION.md, Step 2 |
| 3 | agents/routing_agent.py | Python | **CREATE** | RULES_ENGINE_IMPLEMENTATION.md, Step 3 |
| 4 | agents/orchestrator.py | Python | **UPDATE** | RULES_ENGINE_IMPLEMENTATION.md, Step 3b |
| 5 | api/routers/v1/rules.py | Python | **CREATE** | RULES_ENGINE_IMPLEMENTATION.md, Step 4 |
| 6 | api/main.py | Python | **UPDATE** | Add router import + include line |

### FRONTEND (8 files) - Copy & Paste Ready

| # | File | Type | Action | Source |
|---|------|------|--------|--------|
| 7 | frontend/src/services/rulesService.ts | TypeScript | **CREATE** | RULES_ENGINE_FRONTEND.tsx, FILE 4 |
| 8 | frontend/src/components/RulesUI.tsx | React | **CREATE** | RULES_ENGINE_FRONTEND.tsx, FILE 1 |
| 9 | frontend/src/components/RuleBuilder.tsx | React | **CREATE** | RULES_ENGINE_FRONTEND.tsx, FILE 2 |
| 10 | frontend/src/components/RuleTest.tsx | React | **CREATE** | RULES_ENGINE_FRONTEND.tsx, FILE 3 |
| 11 | frontend/src/components/RulesUI.css | CSS | **CREATE** | RULES_ENGINE_FRONTEND.tsx, FILE 5 |
| 12 | frontend/src/components/RuleBuilder.css | CSS | **CREATE** | RULES_ENGINE_FRONTEND.tsx, FILE 6 |
| 13 | frontend/src/components/RuleTest.css | CSS | **CREATE** | RULES_ENGINE_FRONTEND.tsx, FILE 7 |
| 14 | frontend/src/App.tsx | React | **UPDATE** | Add RulesUI route |

---

## 🚀 STEP-BY-STEP IMPLEMENTATION

### PHASE 1: BACKEND (Day 1)

#### Morning (2-3 hours)

```bash
# 1. Create rules config
touch config/rules.json
# Copy content from Step 1 in RULES_ENGINE_IMPLEMENTATION.md

# 2. Create rules engine
touch utils/rules_engine.py
# Copy entire code from Step 2

# 3. Test it works
python -c "
from utils.rules_engine import evaluate
result = evaluate({
    'domain': 'IT Support',
    'type': 'network_issue',
    'priority': 'high',
    'confidence': 0.92
})
print(f'✓ Works! Matched: {result[\"matched\"]}, Rule: {result[\"rule_name\"]}')"
```

#### Afternoon (2-3 hours)

```bash
# 4. Create routing agent
touch agents/routing_agent.py
# Copy entire code from Step 3

# 5. Update orchestrator
# Add imports and routing node (Step 3b)

# 6. Create API router
touch api/routers/v1/rules.py
# Copy entire code from Step 4

# 7. Update main.py
# Add router import + include_router line

# 8. Test API
uvicorn api.main:app --reload
# In another terminal:
curl http://localhost:8000/api/v1/rules/
```

### PHASE 2: FRONTEND (Day 2)

#### Morning (2-3 hours)

```bash
# 1. Create service
touch frontend/src/services/rulesService.ts
# Copy rulesService.ts from RULES_ENGINE_FRONTEND.tsx

# 2. Create components
touch frontend/src/components/RulesUI.tsx
touch frontend/src/components/RuleBuilder.tsx
touch frontend/src/components/RuleTest.tsx
# Copy each from RULES_ENGINE_FRONTEND.tsx

# 3. Create styles
touch frontend/src/components/RulesUI.css
touch frontend/src/components/RuleBuilder.css
touch frontend/src/components/RuleTest.css
# Copy each from RULES_ENGINE_FRONTEND.tsx

# 4. Update App.tsx
# Add: import RulesUI from './components/RulesUI'
# Add: <Route path="/rules" element={<RulesUI />} />
```

#### Afternoon (2-3 hours)

```bash
# 5. Start frontend
cd frontend && npm start

# 6. Open browser
# http://localhost:3000/rules

# 7. Test functionality
# - Create rule
# - Test rule
# - Toggle rule
# - Delete rule
```

### PHASE 3: INTEGRATION & TESTING (Day 3)

```bash
# 1. Test with real email
# Simulate email through system, verify rule matches

# 2. Test all CRUD operations
# - Create ✓
# - Read ✓
# - Update ✓
# - Delete ✓

# 3. Performance test
# Create 50+ rules, verify < 100ms evaluation

# 4. Deploy to staging
# Run full integration test

# 5. Deploy to production
```

---

## 📖 DOCUMENTATION REFERENCE

| Document | Purpose | Read Time |
|----------|---------|-----------|
| RULES_ENGINE_IMPLEMENTATION.md | Complete backend guide | 30 min |
| RULES_ENGINE_FRONTEND.tsx | Complete React code | 20 min |
| RULES_ENGINE_INTEGRATION_GUIDE.md | Backend + Frontend wiring | 20 min |
| This file | Quick reference | 5 min |

---

## ✅ TESTING CHECKLIST

### Unit Tests
- [ ] rules_engine.py: evaluate() returns correct rule
- [ ] rules_engine.py: condition matching works
- [ ] rules_engine.py: handles missing fields
- [ ] rules_engine.py: sorts rules by priority

### Integration Tests
- [ ] API GET /rules/ returns all rules
- [ ] API POST /rules/ creates rule
- [ ] API PUT /rules/{id} updates rule
- [ ] API DELETE /rules/{id} deletes rule
- [ ] API POST /rules/test evaluates email context
- [ ] API PATCH /rules/{id}/toggle toggles active status

### Frontend Tests
- [ ] Rules list renders correctly
- [ ] Can create new rule via form
- [ ] Can delete rule from list
- [ ] Can toggle rule on/off
- [ ] Test engine shows correct match
- [ ] Error messages display properly

### End-to-End Tests
- [ ] Email → AG-02 (classification) → AG-03 (routing via rules) → correct label
- [ ] Rule evaluation < 100ms
- [ ] 50+ rules evaluate correctly
- [ ] Fallback to default_queue if no match

---

## 🔗 API QUICK REFERENCE

```bash
# List all rules
GET /api/v1/rules/

# Create rule
POST /api/v1/rules/
Body: { name, priority, domain, conditions[], actions[] }

# Update rule
PUT /api/v1/rules/{rule_id}
Body: { updated rule }

# Delete rule
DELETE /api/v1/rules/{rule_id}

# Toggle rule active/inactive
PATCH /api/v1/rules/{rule_id}/toggle

# Test rule with email context
POST /api/v1/rules/test
Body: {
  domain: "IT Support",
  type: "network_issue",
  priority: "high",
  confidence: 0.92
}

# Validate all rules
GET /api/v1/rules/validate
```

---

## 💾 FILE SIZES (Approximate)

| File | Lines | Size |
|------|-------|------|
| config/rules.json | 80 | 2 KB |
| utils/rules_engine.py | 350 | 12 KB |
| agents/routing_agent.py | 180 | 6 KB |
| api/routers/v1/rules.py | 400 | 15 KB |
| Frontend components (7 files) | 1800 | 60 KB |
| **TOTAL** | **~3,000** | **~100 KB** |

---

## 🎯 SUCCESS CRITERIA

✅ Can create rule from UI  
✅ Rule appears in list immediately  
✅ Can test rule with email context  
✅ Real email gets routed via matching rule  
✅ Can toggle rule on/off  
✅ Can delete rule  
✅ All operations < 1 second  
✅ Error handling works  

---

## 🆘 TROUBLESHOOTING

| Problem | Solution |
|---------|----------|
| Rules not loading | Check config/rules.json exists and is valid JSON |
| API endpoints 404 | Verify api/routers/v1/rules.py is imported in api/main.py |
| Frontend can't connect | Set REACT_APP_API_URL in .env file |
| Rules not matching | Print email_context in routing_agent.py, verify field names |
| Frontend crashes | Check all imports are correct in package.json |

---

## 📚 LEARNING RESOURCES

- **Rules Engine Logic:** config/rules.json (sample rules)
- **Condition Operators:** utils/rules_engine.py (_match_condition function)
- **Action Types:** agents/routing_agent.py (routing_agent function)
- **API Design:** api/routers/v1/rules.py (all endpoints)
- **UI Components:** frontend/src/components/ (React code)

---

## 🚀 NEXT FEATURES (After Rules Engine)

1. **Sprint 1 - Human Approval Loop** (2 days)
   - Hold queue + manual approve endpoint
   - Admin dashboard to approve/reject

2. **Sprint 1 - Agent Health Monitoring** (1 day)
   - Heartbeat every 30 seconds
   - Alert on missed heartbeats

3. **Sprint 1 - Event-Driven Triggers** (2 days)
   - Replace polling with event bus
   - Webhook immediate processing

4. **Sprint 2 - Domain Management UI** (2 days)
   - Add domain without code
   - Config-via-UI toggle switches

5. **Sprint 3 - Auto-Learning** (3 days)
   - Store human corrections
   - Feed corrections back to LLM context

---

## 📞 NEED HELP?

1. Check the detailed guide: RULES_ENGINE_IMPLEMENTATION.md
2. Check integration guide: RULES_ENGINE_INTEGRATION_GUIDE.md
3. Look at example code: RULES_ENGINE_FRONTEND.tsx
4. Check error messages in browser console / server logs

---

**Ready to implement?** Start with Step 1 (create config/rules.json) and follow the timeline above! 🚀
