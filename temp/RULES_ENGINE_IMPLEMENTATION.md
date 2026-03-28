# Rules Engine Implementation Guide
## Complete Step-by-Step with All Files

**Project:** Inbox Management Multi-Agent System  
**Feature:** Rules Engine (IF-THEN routing digitization)  
**Status:** Sprint 4  
**Effort:** 2-3 days  

---

## 📁 Project Folder Structure (After Implementation)

```
inbox_management_system/
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── rules.json                 ← NEW (Step 1)
│   ├── domains/
│   │   ├── it_support.py
│   │   ├── hr.py
│   │   └── billing.py
│   └── gmail_labels.json
│
├── utils/
│   ├── __init__.py
│   ├── rules_engine.py            ← NEW (Step 2)
│   ├── gmail_label_manager.py
│   ├── pii_detector.py
│   └── retry_logic.py
│
├── agents/
│   ├── __init__.py
│   ├── intake_agent.py
│   ├── classification_agent.py
│   ├── routing_agent.py           ← UPDATE (Step 3)
│   ├── response_agent.py
│   ├── sla_agent.py
│   ├── audit_agent.py
│   └── orchestrator.py            ← UPDATE (Step 3)
│
├── api/
│   ├── main.py
│   ├── routers/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── intake.py
│   │       ├── classify.py
│   │       ├── registry.py
│   │       ├── rules.py           ← NEW (Step 4)
│   │       └── control.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── RulesUI.tsx        ← NEW (UI Component)
│   │   │   ├── RuleBuilder.tsx    ← NEW (UI Component)
│   │   │   └── RuleTest.tsx       ← NEW (UI Component)
│   │   ├── services/
│   │   │   └── rulesService.ts    ← NEW (API Service)
│   │   └── pages/
│   │       └── RulesDashboard.tsx ← NEW (Dashboard)
│
├── tests/
│   ├── test_rules_engine.py       ← NEW (Unit Tests)
│   └── test_rules_integration.py  ← NEW (Integration Tests)
│
└── docs/
    └── RULES_ENGINE.md            ← NEW (Documentation)
```

---

## 📋 Implementation Checklist

### Phase 1: Backend Infrastructure (1 Day)
- [ ] Step 1: Create config/rules.json
- [ ] Step 2: Create utils/rules_engine.py
- [ ] Step 3: Update agents/routing_agent.py
- [ ] Step 3b: Update agents/orchestrator.py
- [ ] Step 4: Create api/routers/v1/rules.py
- [ ] Test rules engine locally

### Phase 2: Frontend UI (1 Day)
- [ ] Create frontend/src/components/RulesUI.tsx
- [ ] Create frontend/src/components/RuleBuilder.tsx
- [ ] Create frontend/src/components/RuleTest.tsx
- [ ] Create frontend/src/services/rulesService.ts
- [ ] Create frontend/src/pages/RulesDashboard.tsx
- [ ] Connect to backend APIs

### Phase 3: Testing & Integration (1 Day)
- [ ] Unit tests for rules_engine.py
- [ ] Integration tests for routing
- [ ] Test via UI
- [ ] Test with real emails
- [ ] Documentation

---

## 🔧 STEP 1: Create config/rules.json

**File:** `config/rules.json`  
**Time:** 15 minutes

```json
[
  {
    "id": "rule-001",
    "name": "IT support escalation",
    "description": "Route high-priority IT issues to Network Ops team",
    "priority": 1,
    "domain": "IT Support",
    "match_mode": "all",
    "stop_on_match": true,
    "active": true,
    "created_at": "2026-03-25T00:00:00Z",
    "conditions": [
      {
        "field": "domain",
        "operator": "is",
        "value": "IT Support"
      },
      {
        "field": "type",
        "operator": "in",
        "value": ["network_issue", "hardware_failure", "server_down"]
      },
      {
        "field": "priority",
        "operator": "is",
        "value": "high"
      }
    ],
    "actions": [
      {
        "action": "route_to",
        "value": "IT Support/Network Ops Team"
      },
      {
        "action": "set_sla",
        "value": "2h"
      },
      {
        "action": "notify_slack",
        "value": "#it-ops"
      },
      {
        "action": "apply_label",
        "value": "Escalated"
      }
    ]
  },
  {
    "id": "rule-002",
    "name": "HR leave request auto-route",
    "description": "Auto-route leave requests with high confidence",
    "priority": 2,
    "domain": "HR",
    "match_mode": "all",
    "stop_on_match": true,
    "active": true,
    "created_at": "2026-03-25T00:00:00Z",
    "conditions": [
      {
        "field": "domain",
        "operator": "is",
        "value": "HR"
      },
      {
        "field": "type",
        "operator": "is",
        "value": "leave_request"
      },
      {
        "field": "confidence",
        "operator": "greater_than",
        "value": 0.85
      }
    ],
    "actions": [
      {
        "action": "route_to",
        "value": "HR/Leave Management"
      },
      {
        "action": "send_ack",
        "value": "leave_ack"
      },
      {
        "action": "set_sla",
        "value": "24h"
      }
    ]
  },
  {
    "id": "rule-003",
    "name": "Low confidence fallback",
    "description": "Hold low-confidence emails for human review",
    "priority": 99,
    "domain": "any",
    "match_mode": "any",
    "stop_on_match": true,
    "active": true,
    "created_at": "2026-03-25T00:00:00Z",
    "conditions": [
      {
        "field": "confidence",
        "operator": "less_than",
        "value": 0.70
      }
    ],
    "actions": [
      {
        "action": "hold_for_review",
        "value": true
      },
      {
        "action": "route_to",
        "value": "human_review_queue"
      },
      {
        "action": "notify_slack",
        "value": "#inbox-reviews"
      }
    ]
  },
  {
    "id": "rule-004",
    "name": "Billing urgent payment",
    "description": "Route urgent billing/payment issues to priority queue",
    "priority": 3,
    "domain": "Customer Support",
    "match_mode": "all",
    "stop_on_match": true,
    "active": true,
    "created_at": "2026-03-25T00:00:00Z",
    "conditions": [
      {
        "field": "domain",
        "operator": "is",
        "value": "Customer Support"
      },
      {
        "field": "type",
        "operator": "in",
        "value": ["billing_issue", "payment_failed", "refund_request"]
      },
      {
        "field": "sentiment",
        "operator": "is",
        "value": "negative"
      }
    ],
    "actions": [
      {
        "action": "route_to",
        "value": "Customer Support/Customer Issues"
      },
      {
        "action": "set_sla",
        "value": "4h"
      },
      {
        "action": "apply_label",
        "value": "Urgent"
      }
    ]
  }
]
```

**What this file does:**
- Stores all routing rules in JSON format
- Each rule has conditions (IF) and actions (THEN)
- Rules are evaluated in priority order (1 = highest)
- `stop_on_match: true` means stop evaluating after this rule matches

**Test it:**
```bash
# Verify JSON is valid
python -m json.tool config/rules.json
```

---

## 🔧 STEP 2: Create utils/rules_engine.py

**File:** `utils/rules_engine.py`  
**Time:** 30 minutes

```python
# utils/rules_engine.py
"""
Rules Engine for email routing
Evaluates email context against configured rules
Returns matching rule and its actions
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from app.core.logging import get_logger

logger = get_logger(__name__)

RULES_PATH = Path("config/rules.json")

class RuleNotFoundError(Exception):
    """Rule not found"""
    pass

class InvalidRuleError(Exception):
    """Invalid rule configuration"""
    pass

def load_rules() -> List[Dict[str, Any]]:
    """
    Load all active rules from config/rules.json
    Returns rules sorted by priority (lower number = higher priority)
    """
    try:
        with open(RULES_PATH, 'r') as f:
            rules = json.load(f)
        
        # Filter active rules and sort by priority
        active_rules = [r for r in rules if r.get("active", True)]
        sorted_rules = sorted(active_rules, key=lambda r: r.get("priority", 99))
        
        logger.debug(f"Loaded {len(sorted_rules)} active rules from {RULES_PATH}")
        return sorted_rules
    
    except FileNotFoundError:
        logger.error(f"Rules file not found at {RULES_PATH}")
        raise
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in rules file: {e}")
        raise

def _match_condition(condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
    """
    Evaluate a single condition against the email context
    
    Returns: True if condition matches, False otherwise
    """
    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")
    actual = context.get(field)

    # If field doesn't exist in context, condition doesn't match
    if actual is None:
        logger.debug(f"Field '{field}' not in context, condition fails")
        return False

    try:
        match operator:
            case "is":
                # Exact match (case-insensitive for strings)
                result = str(actual).lower() == str(expected).lower()
                logger.debug(f"[is] {actual} == {expected} → {result}")
                return result

            case "is_not":
                # Not equal (case-insensitive)
                result = str(actual).lower() != str(expected).lower()
                logger.debug(f"[is_not] {actual} != {expected} → {result}")
                return result

            case "in":
                # Value in list (case-insensitive)
                expected_list = [str(v).lower() for v in (expected if isinstance(expected, list) else [expected])]
                result = str(actual).lower() in expected_list
                logger.debug(f"[in] {actual} in {expected_list} → {result}")
                return result

            case "not_in":
                # Value not in list (case-insensitive)
                expected_list = [str(v).lower() for v in (expected if isinstance(expected, list) else [expected])]
                result = str(actual).lower() not in expected_list
                logger.debug(f"[not_in] {actual} not in {expected_list} → {result}")
                return result

            case "contains":
                # Substring match (case-insensitive)
                result = str(expected).lower() in str(actual).lower()
                logger.debug(f"[contains] '{expected}' in '{actual}' → {result}")
                return result

            case "starts_with":
                # String starts with (case-insensitive)
                result = str(actual).lower().startswith(str(expected).lower())
                logger.debug(f"[starts_with] '{actual}' starts with '{expected}' → {result}")
                return result

            case "greater_than":
                # Numeric comparison
                result = float(actual) > float(expected)
                logger.debug(f"[greater_than] {actual} > {expected} → {result}")
                return result

            case "less_than":
                # Numeric comparison
                result = float(actual) < float(expected)
                logger.debug(f"[less_than] {actual} < {expected} → {result}")
                return result

            case "greater_or_equal":
                result = float(actual) >= float(expected)
                logger.debug(f"[>=] {actual} >= {expected} → {result}")
                return result

            case "less_or_equal":
                result = float(actual) <= float(expected)
                logger.debug(f"[<=] {actual} <= {expected} → {result}")
                return result

            case _:
                logger.warning(f"Unknown operator: {operator}")
                return False

    except (ValueError, TypeError) as e:
        logger.error(f"Error evaluating condition: {e}")
        return False

def evaluate(email_context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate all active rules against email context
    Returns the first matching rule's actions + metadata
    
    Args:
        email_context: Dictionary with email data
        Example:
        {
            "domain": "IT Support",
            "type": "network_issue",
            "priority": "high",
            "sentiment": "negative",
            "confidence": 0.92,
            "sender": "user@company.com",
            "subject": "VPN not working"
        }
    
    Returns:
        {
            "matched": True/False,
            "rule_id": "rule-001",
            "rule_name": "IT support escalation",
            "priority": 1,
            "actions": [...],
            "stop": True/False
        }
    """
    try:
        rules = load_rules()
    except Exception as e:
        logger.error(f"Failed to load rules: {e}")
        return {
            "matched": False,
            "rule_id": None,
            "rule_name": "error",
            "actions": [{"action": "route_to", "value": "error_queue"}],
            "stop": True,
            "error": str(e)
        }

    logger.info(f"Evaluating {len(rules)} rules against context: {email_context}")

    # Evaluate each rule in priority order
    for rule in rules:
        conditions = rule.get("conditions", [])
        match_mode = rule.get("match_mode", "all")
        rule_name = rule.get("name", "unnamed")

        # Evaluate all conditions
        condition_results = [_match_condition(cond, email_context) for cond in conditions]

        # Determine if rule matches based on match_mode
        if match_mode == "all":
            matched = all(condition_results) if condition_results else False
        elif match_mode == "any":
            matched = any(condition_results)
        else:
            logger.warning(f"Unknown match_mode: {match_mode}, defaulting to 'all'")
            matched = all(condition_results)

        if matched:
            logger.info(
                f"✓ Rule matched: {rule_name} (priority={rule.get('priority')}, "
                f"id={rule.get('id')})"
            )
            return {
                "matched": True,
                "rule_id": rule.get("id"),
                "rule_name": rule_name,
                "priority": rule.get("priority", 99),
                "actions": rule.get("actions", []),
                "stop": rule.get("stop_on_match", True),
            }

    # No rule matched
    logger.warning(f"✗ No rule matched for context: {email_context}")
    return {
        "matched": False,
        "rule_id": None,
        "rule_name": None,
        "actions": [{"action": "route_to", "value": "default_queue"}],
        "stop": True,
    }

def get_rule(rule_id: str) -> Optional[Dict[str, Any]]:
    """Get a specific rule by ID"""
    try:
        rules = load_rules()
        for rule in rules:
            if rule.get("id") == rule_id:
                return rule
        return None
    except Exception as e:
        logger.error(f"Error getting rule {rule_id}: {e}")
        return None

def save_rules(rules: List[Dict[str, Any]]) -> bool:
    """Save rules to config/rules.json"""
    try:
        with open(RULES_PATH, 'w') as f:
            json.dump(rules, f, indent=2)
        logger.info(f"Saved {len(rules)} rules to {RULES_PATH}")
        return True
    except Exception as e:
        logger.error(f"Error saving rules: {e}")
        return False
```

**What this file does:**
- Loads rules from JSON
- Evaluates conditions (field, operator, value)
- Returns matching rule + actions
- Supports multiple operators (is, in, contains, >/<, etc.)

**Test it:**
```bash
cd /path/to/project
python -c "
from utils.rules_engine import evaluate

# Test case 1: IT support escalation
result = evaluate({
    'domain': 'IT Support',
    'type': 'network_issue',
    'priority': 'high',
    'confidence': 0.92
})
print('Test 1 - IT Escalation:')
print(f'  Matched: {result[\"matched\"]}')
print(f'  Rule: {result[\"rule_name\"]}')
print()

# Test case 2: HR leave request
result = evaluate({
    'domain': 'HR',
    'type': 'leave_request',
    'confidence': 0.88
})
print('Test 2 - HR Leave Request:')
print(f'  Matched: {result[\"matched\"]}')
print(f'  Rule: {result[\"rule_name\"]}')
print()

# Test case 3: No match
result = evaluate({
    'domain': 'Unknown',
    'type': 'unknown'
})
print('Test 3 - No Match:')
print(f'  Matched: {result[\"matched\"]}')
print(f'  Default action: {result[\"actions\"][0]}')
"
```

Expected output:
```
Test 1 - IT Escalation:
  Matched: True
  Rule: IT support escalation

Test 2 - HR Leave Request:
  Matched: True
  Rule: HR leave request auto-route

Test 3 - No Match:
  Matched: False
  Default action: {'action': 'route_to', 'value': 'default_queue'}
```

---

## 🔧 STEP 3: Update agents/routing_agent.py

**File:** `agents/routing_agent.py`  
**Time:** 45 minutes

```python
# agents/routing_agent.py
"""
Routing Agent (AG-03) - Routes classified emails to appropriate queues
Uses the Rules Engine to determine routing decisions
"""

from typing import Any, Dict
from utils.rules_engine import evaluate
from utils.gmail_label_manager import apply_label
from app.core.logging import get_logger
import asyncio

logger = get_logger(__name__)

async def routing_agent(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    LangGraph node - Routes classified email using rules engine
    
    Input state:
        - email_id: str
        - domain: str
        - classification: dict (type, priority, sentiment, confidence)
        - sender: str
        - subject: str
    
    Output state:
        - routing_decision: str (Gmail label path)
        - rule_matched: str (rule name)
        - actions_taken: list[str]
        - agent_status: str ("routed")
    """
    
    email_id = state.get("email_id", "unknown")
    
    logger.info(f"🔀 [AG-03] Routing Agent processing: {email_id}")
    
    try:
        # Build email context from state
        classification = state.get("classification", {})
        
        email_context = {
            "domain": state.get("domain", "unknown"),
            "type": classification.get("type", "unknown"),
            "priority": classification.get("priority", "medium"),
            "sentiment": classification.get("sentiment", "neutral"),
            "confidence": classification.get("confidence", 0.0),
            "sender": state.get("sender", "unknown"),
            "subject": state.get("subject", ""),
        }
        
        logger.debug(f"Email context: {email_context}")
        
        # Evaluate rules
        result = evaluate(email_context)
        actions_taken = []
        
        logger.info(f"Rule evaluation: matched={result['matched']}, "
                   f"rule={result.get('rule_name', 'none')}")
        
        # Execute actions
        for action in result.get("actions", []):
            act = action.get("action")
            val = action.get("value")
            
            try:
                match act:
                    case "route_to":
                        # Route to Gmail label
                        state["routing_decision"] = val
                        
                        # Apply Gmail label (async)
                        try:
                            await apply_label(email_id, val)
                            logger.info(f"✓ Applied label: {val}")
                            actions_taken.append(f"routed → {val}")
                        except Exception as e:
                            logger.warning(f"Failed to apply label: {e}")
                            actions_taken.append(f"route → {val} (label pending)")
                    
                    case "set_sla":
                        # Set SLA deadline
                        state["sla_deadline"] = val
                        logger.info(f"✓ SLA set: {val}")
                        actions_taken.append(f"SLA: {val}")
                    
                    case "send_ack":
                        # Queue ACK response
                        state["send_ack_template"] = val
                        logger.info(f"✓ ACK queued: {val}")
                        actions_taken.append(f"ACK: {val}")
                    
                    case "notify_slack":
                        # Notify Slack channel
                        state["slack_notify"] = val
                        logger.info(f"✓ Slack notify: {val}")
                        actions_taken.append(f"Slack: {val}")
                    
                    case "hold_for_review":
                        # Mark for human review
                        state["human_review"] = True
                        logger.info(f"✓ Marked for review")
                        actions_taken.append("held for human review")
                    
                    case "apply_label":
                        # Apply custom label
                        try:
                            await apply_label(email_id, val)
                            logger.info(f"✓ Applied label: {val}")
                            actions_taken.append(f"label: {val}")
                        except Exception as e:
                            logger.warning(f"Failed to apply label: {e}")
                            actions_taken.append(f"label: {val} (pending)")
                    
                    case _:
                        logger.warning(f"Unknown action: {act}")
                        actions_taken.append(f"unknown: {act}")
            
            except Exception as e:
                logger.error(f"Error executing action {act}: {e}")
                actions_taken.append(f"error: {act}")
        
        # Update state with routing results
        state["rule_matched"] = result.get("rule_name")
        state["rule_id"] = result.get("rule_id")
        state["actions_taken"] = actions_taken
        state["agent_status"] = "routed"
        state["routing_complete"] = True
        
        logger.info(f"✓ Routing complete: {', '.join(actions_taken)}")
        
        return state
    
    except Exception as e:
        logger.error(f"❌ Routing agent error: {e}")
        state["agent_status"] = "error"
        state["error"] = str(e)
        return state
```

**What this does:**
- Takes classified email from AG-02
- Evaluates rules engine to get routing decision
- Executes actions (apply labels, notify, hold for review, etc.)
- Updates state with routing results

---

## 🔧 STEP 3b: Update agents/orchestrator.py

**File:** `agents/orchestrator.py`  
**Time:** 15 minutes

Add routing agent to your LangGraph StateGraph:

```python
# agents/orchestrator.py (add to existing file)
from langgraph.graph import StateGraph
from agents.intake_agent import intake_agent
from agents.classification_agent import classification_agent
from agents.routing_agent import routing_agent  # ← ADD THIS
from agents.response_agent import response_agent
from agents.sla_agent import sla_agent
from agents.audit_agent import audit_agent
from agents.analytics_agent import analytics_agent

# ... existing code ...

def build_orchestrator():
    """Build LangGraph state machine with all agents"""
    
    graph = StateGraph(InboxState)
    
    # Add nodes
    graph.add_node("intake", intake_agent)
    graph.add_node("classification", classification_agent)
    graph.add_node("routing", routing_agent)  # ← ADD THIS LINE
    graph.add_node("response", response_agent)
    graph.add_node("sla", sla_agent)
    graph.add_node("audit", audit_agent)
    graph.add_node("analytics", analytics_agent)
    
    # Add edges
    graph.add_edge("START", "intake")
    graph.add_edge("intake", "classification")
    graph.add_edge("classification", "routing")  # ← UPDATE THIS
    graph.add_edge("routing", "response")  # ← UPDATE THIS
    graph.add_edge("response", "sla")
    graph.add_edge("sla", "audit")
    graph.add_edge("audit", "analytics")
    graph.add_edge("analytics", "END")
    
    return graph.compile()

# Compile the graph
orchestrator = build_orchestrator()
```

---

## 🔧 STEP 4: Create api/routers/v1/rules.py

**File:** `api/routers/v1/rules.py`  
**Time:** 1 hour

```python
# api/routers/v1/rules.py
"""
Rules Engine API Endpoints
CRUD operations for rules + testing
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json
from pathlib import Path
from utils.rules_engine import evaluate, load_rules, save_rules
from app.core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/rules", tags=["rules"])

RULES_PATH = Path("config/rules.json")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class Condition(BaseModel):
    field: str
    operator: str
    value: Any

class Action(BaseModel):
    action: str
    value: Any

class Rule(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    priority: int = 99
    domain: str
    match_mode: str = "all"
    stop_on_match: bool = True
    active: bool = True
    conditions: List[Condition]
    actions: List[Action]

class RuleTestRequest(BaseModel):
    domain: str
    type: str
    priority: str = "medium"
    sentiment: str = "neutral"
    confidence: float = 0.0
    sender: str = "unknown@example.com"
    subject: str = ""

# ============================================================================
# API ENDPOINTS
# ============================================================================

@router.get("/")
async def list_rules(active_only: bool = Query(True)):
    """List all rules, optionally filtered by active status"""
    try:
        rules = load_rules() if active_only else json.loads(RULES_PATH.read_text())
        return {"rules": rules, "total": len(rules)}
    except Exception as e:
        logger.error(f"Error listing rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{rule_id}")
async def get_rule(rule_id: str):
    """Get a specific rule by ID"""
    try:
        all_rules = json.loads(RULES_PATH.read_text())
        rule = next((r for r in all_rules if r.get("id") == rule_id), None)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        return rule
    except Exception as e:
        logger.error(f"Error getting rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/")
async def create_rule(rule: Rule):
    """Create a new rule"""
    try:
        all_rules = json.loads(RULES_PATH.read_text())
        
        # Generate ID if not provided
        if not rule.id:
            next_id = max([int(r.get("id", "rule-0").split("-")[1]) for r in all_rules], default=0) + 1
            rule.id = f"rule-{next_id:03d}"
        
        # Check if rule name already exists
        if any(r["name"] == rule.name for r in all_rules):
            raise HTTPException(status_code=409, detail="Rule name already exists")
        
        # Add created_at timestamp
        import datetime
        rule_dict = rule.model_dump()
        rule_dict["created_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        all_rules.append(rule_dict)
        save_rules(all_rules)
        
        logger.info(f"Created rule: {rule.name} (id={rule.id})")
        return {"status": "created", "rule": rule_dict}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{rule_id}")
async def update_rule(rule_id: str, rule: Rule):
    """Update an existing rule"""
    try:
        all_rules = json.loads(RULES_PATH.read_text())
        
        # Find and update rule
        idx = next((i for i, r in enumerate(all_rules) if r.get("id") == rule_id), None)
        if idx is None:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        rule_dict = rule.model_dump()
        rule_dict["id"] = rule_id
        rule_dict["updated_at"] = datetime.datetime.utcnow().isoformat() + "Z"
        
        all_rules[idx] = rule_dict
        save_rules(all_rules)
        
        logger.info(f"Updated rule: {rule.name} (id={rule_id})")
        return {"status": "updated", "rule": rule_dict}
    
    except Exception as e:
        logger.error(f"Error updating rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{rule_id}")
async def delete_rule(rule_id: str):
    """Delete a rule"""
    try:
        all_rules = json.loads(RULES_PATH.read_text())
        
        # Find and remove rule
        rule_to_delete = next((r for r in all_rules if r.get("id") == rule_id), None)
        if not rule_to_delete:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        all_rules = [r for r in all_rules if r.get("id") != rule_id]
        save_rules(all_rules)
        
        logger.info(f"Deleted rule: {rule_to_delete['name']} (id={rule_id})")
        return {"status": "deleted", "rule_id": rule_id}
    
    except Exception as e:
        logger.error(f"Error deleting rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{rule_id}/toggle")
async def toggle_rule(rule_id: str):
    """Toggle rule active/inactive status"""
    try:
        all_rules = json.loads(RULES_PATH.read_text())
        
        # Find and toggle rule
        rule = next((r for r in all_rules if r.get("id") == rule_id), None)
        if not rule:
            raise HTTPException(status_code=404, detail="Rule not found")
        
        rule["active"] = not rule.get("active", True)
        save_rules(all_rules)
        
        logger.info(f"Toggled rule: {rule['name']} (active={rule['active']})")
        return {"status": "toggled", "rule_id": rule_id, "active": rule["active"]}
    
    except Exception as e:
        logger.error(f"Error toggling rule {rule_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/test")
async def test_rule(test_request: RuleTestRequest):
    """
    Test the rules engine with a simulated email context
    Returns which rule matches and what actions would be taken
    """
    try:
        context = {
            "domain": test_request.domain,
            "type": test_request.type,
            "priority": test_request.priority,
            "sentiment": test_request.sentiment,
            "confidence": test_request.confidence,
            "sender": test_request.sender,
            "subject": test_request.subject,
        }
        
        result = evaluate(context)
        
        return {
            "status": "tested",
            "context": context,
            "matched": result.get("matched"),
            "rule_id": result.get("rule_id"),
            "rule_name": result.get("rule_name"),
            "actions": result.get("actions"),
        }
    
    except Exception as e:
        logger.error(f"Error testing rule: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/validate")
async def validate_rules():
    """Validate all rules for syntax and logic errors"""
    try:
        rules = load_rules()
        errors = []
        
        for rule in rules:
            # Validate required fields
            if not rule.get("name"):
                errors.append(f"Rule {rule.get('id')} missing name")
            if not rule.get("conditions"):
                errors.append(f"Rule '{rule.get('name')}' missing conditions")
            if not rule.get("actions"):
                errors.append(f"Rule '{rule.get('name')}' missing actions")
            
            # Validate operators
            valid_operators = ["is", "is_not", "in", "not_in", "contains", 
                             "starts_with", "greater_than", "less_than",
                             "greater_or_equal", "less_or_equal"]
            for cond in rule.get("conditions", []):
                if cond.get("operator") not in valid_operators:
                    errors.append(
                        f"Rule '{rule.get('name')}' has invalid operator: "
                        f"{cond.get('operator')}"
                    )
            
            # Validate match_mode
            if rule.get("match_mode") not in ["all", "any"]:
                errors.append(
                    f"Rule '{rule.get('name')}' has invalid match_mode: "
                    f"{rule.get('match_mode')}"
                )
        
        return {
            "status": "valid" if not errors else "invalid",
            "total_rules": len(rules),
            "errors": errors
        }
    
    except Exception as e:
        logger.error(f"Error validating rules: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

**What this provides:**
- GET /rules/ — List all rules
- POST /rules/ — Create new rule
- PUT /rules/{rule_id} — Update rule
- DELETE /rules/{rule_id} — Delete rule
- PATCH /rules/{rule_id}/toggle — Enable/disable rule
- POST /rules/test — Test rule with email context
- GET /rules/validate — Validate all rules

---

## 📝 Integration with FastAPI main.py

**File:** `api/main.py` (add to existing file)

```python
# api/main.py
from fastapi import FastAPI
from api.routers.v1 import rules  # ← ADD THIS

app = FastAPI()

# ... existing code ...

# Include rules router
app.include_router(rules.router, prefix="/api/v1")  # ← ADD THIS

# ... rest of your app ...
```

---

## 🧪 STEP 5: Unit Tests

**File:** `tests/test_rules_engine.py`

```python
# tests/test_rules_engine.py
"""
Unit tests for rules engine
"""

import pytest
from utils.rules_engine import evaluate, _match_condition, load_rules

class TestRulesEngine:
    """Test rules engine evaluation"""
    
    def test_it_support_escalation(self):
        """Test IT support escalation rule"""
        result = evaluate({
            "domain": "IT Support",
            "type": "network_issue",
            "priority": "high",
            "confidence": 0.92
        })
        assert result["matched"] == True
        assert result["rule_name"] == "IT support escalation"
    
    def test_hr_leave_request(self):
        """Test HR leave request rule"""
        result = evaluate({
            "domain": "HR",
            "type": "leave_request",
            "confidence": 0.88
        })
        assert result["matched"] == True
        assert result["rule_name"] == "HR leave request auto-route"
    
    def test_low_confidence_fallback(self):
        """Test low confidence fallback rule"""
        result = evaluate({
            "domain": "Unknown",
            "confidence": 0.50
        })
        assert result["matched"] == True
        assert "hold_for_review" in [a["action"] for a in result["actions"]]
    
    def test_no_match_default_route(self):
        """Test default route when no rule matches"""
        result = evaluate({
            "domain": "Unknown",
            "type": "unknown",
            "confidence": 0.85
        })
        assert result["matched"] == False
        assert result["actions"][0]["action"] == "route_to"
        assert result["actions"][0]["value"] == "default_queue"

class TestConditionMatching:
    """Test individual condition matching"""
    
    def test_is_operator(self):
        """Test 'is' operator"""
        assert _match_condition(
            {"field": "domain", "operator": "is", "value": "IT Support"},
            {"domain": "IT Support"}
        ) == True
    
    def test_in_operator(self):
        """Test 'in' operator"""
        assert _match_condition(
            {"field": "type", "operator": "in", "value": ["network", "hardware"]},
            {"type": "network"}
        ) == True
    
    def test_greater_than_operator(self):
        """Test 'greater_than' operator"""
        assert _match_condition(
            {"field": "confidence", "operator": "greater_than", "value": 0.85},
            {"confidence": 0.92}
        ) == True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
```

**Run tests:**
```bash
pytest tests/test_rules_engine.py -v
```

---

## ✅ STEP-BY-STEP CHECKLIST

### Phase 1: Backend (Complete in Order)
```
Day 1 — Morning:
[ ] 1. Create config/rules.json with starter rules
[ ] 2. Create utils/rules_engine.py with rule evaluation logic
[ ] 3. Test rules_engine.py locally (python -c "...")
[ ] 4. Create tests/test_rules_engine.py and run tests

Day 1 — Afternoon:
[ ] 5. Update agents/routing_agent.py to use rules engine
[ ] 6. Update agents/orchestrator.py to wire routing agent
[ ] 7. Test orchestrator with sample email

Day 2 — Morning:
[ ] 8. Create api/routers/v1/rules.py with CRUD endpoints
[ ] 9. Add router to api/main.py
[ ] 10. Test API endpoints with curl
```

### API Testing with curl:
```bash
# Get all rules
curl http://localhost:8000/api/v1/rules/

# Test a rule
curl -X POST http://localhost:8000/api/v1/rules/test \
  -H "Content-Type: application/json" \
  -d '{
    "domain": "IT Support",
    "type": "network_issue",
    "priority": "high",
    "confidence": 0.92
  }'

# Create a new rule
curl -X POST http://localhost:8000/api/v1/rules/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Custom Rule",
    "priority": 5,
    "domain": "Custom",
    "conditions": [...],
    "actions": [...]
  }'

# Validate all rules
curl http://localhost:8000/api/v1/rules/validate
```

---

## 📋 SUMMARY OF ALL FILES TO ADD

| File | Type | Size | Purpose |
|------|------|------|---------|
| config/rules.json | JSON | ~1 KB | Rule definitions |
| utils/rules_engine.py | Python | ~500 lines | Core rule evaluation logic |
| agents/routing_agent.py | Python | ~200 lines | Integration with LangGraph |
| api/routers/v1/rules.py | Python | ~400 lines | REST API endpoints |
| tests/test_rules_engine.py | Python | ~100 lines | Unit tests |

**Total new code:** ~1,200 lines  
**Integration changes:** api/main.py, agents/orchestrator.py  
**Estimated time:** 2-3 days

---

Good luck with implementation! 🚀
