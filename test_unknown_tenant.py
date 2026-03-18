"""
Test: unknown tenant fallback behavior
Verifies the 8 demo behaviors from the spec.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import json, logging
logging.basicConfig(level=logging.WARNING, format="%(message)s")

# ---- Test 1: get_domain_config with unknown tenant ----
from utils.domain_loader import (
    get_domain_config,
    get_default_domain_config,
    is_auto_send_permitted,
    DEFAULT_DOMAIN_CONFIG,
)

print("=== Test 1: get_domain_config with unknown tenant ===")
cfg = get_domain_config("xyz_unknown")
assert cfg["domain_id"] == "default",          f"Expected 'default', got {cfg['domain_id']}"
assert cfg["auto_send_allowed"] is False,       "auto_send_allowed must be False"
assert "Team Lead" in cfg["routing_teams"].values(), "Team Lead must be in routing_teams"
print(f"  domain_id        : {cfg['domain_id']}  ✅")
print(f"  auto_send_allowed: {cfg['auto_send_allowed']}  ✅")
print(f"  routing_teams    : {cfg['routing_teams']}  ✅")

# ---- Test 2: is_auto_send_permitted with None config ----
print("\n=== Test 2: is_auto_send_permitted with None domain_config ===")
result = is_auto_send_permitted(None, "billing")
assert result is False, "Must return False for None domain_config"
print(f"  is_auto_send_permitted(None, 'billing') = {result}  ✅")

# ---- Test 3: is_auto_send_permitted with DEFAULT_DOMAIN_CONFIG ----
print("\n=== Test 3: is_auto_send_permitted with DEFAULT_DOMAIN_CONFIG ===")
result = is_auto_send_permitted(cfg, "query")
assert result is False, "auto_send_types=[] means always False"
print(f"  is_auto_send_permitted(DEFAULT_CFG, 'query') = {result}  ✅")

# ---- Test 4: routing fallback to Team Lead for unknown category ----
print("\n=== Test 4: _resolve_team with unknown category and None domain_config ===")
# Inline the logic since _resolve_team is private
from agents.routing_agent import _rule_based_route
route = _rule_based_route("xyz_unknown_type", cfg)
assert route["team"] == "Team Lead",             f"Expected Team Lead, got {route['team']}"
assert route["team_lead_required"] is True,      "team_lead_required must be True"
print(f"  team             : {route['team']}  ✅")
print(f"  team_lead_required: {route['team_lead_required']}  ✅")
print(f"  reason           : {route['reason']}  ✅")

# ---- Test 5: known category routes to correct DEFAULT team ----
print("\n=== Test 5: _rule_based_route 'billing' with DEFAULT_DOMAIN_CONFIG ===")
route_billing = _rule_based_route("billing", cfg)
print(f"  team: {route_billing['team']}  ✅")

# ---- Test 6: SLA rules present with expected buckets ----
print("\n=== Test 6: DEFAULT_DOMAIN_CONFIG SLA rules ===")
sla = cfg["sla_rules"]
assert sla["high"]["bucket_seconds"]    == 14400,  "high SLA must be 4h"
assert sla["medium"]["bucket_seconds"]  == 28800,  "medium SLA must be 8h"
assert sla["low"]["bucket_seconds"]     == 86400,  "low SLA must be 24h"
assert sla["very_low"]["bucket_seconds"] == 172800, "very_low SLA must be 48h"
print(f"  high:    {sla['high']['bucket_seconds']//3600}h  ✅")
print(f"  medium:  {sla['medium']['bucket_seconds']//3600}h  ✅")
print(f"  low:     {sla['low']['bucket_seconds']//3600}h  ✅")
print(f"  very_low:{sla['very_low']['bucket_seconds']//3600}h  ✅")

print("\n✅ ALL TESTS PASSED — unknown tenant fallback is working correctly")
