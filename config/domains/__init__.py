"""
config/domains/__init__.py — Domain Package Registry

3 domains matching the Gmail label structure in config/gmail_labels.json:

  it_support  →  IT Support/* labels       (5 sublabels)
  hr          →  HR/* labels               (4 sublabels)
  billing     →  Customer Support/* labels (Issues / Product Support / Warranty)

All unmatched or cross-domain emails fall to Others/Uncategorised.

Usage in domain_loader.py:
    from config.domains import DOMAIN_REGISTRY
    config = DOMAIN_REGISTRY.get(tenant_domain, DOMAIN_REGISTRY["default"])
"""
from config.domains.it_support import DOMAIN_CONFIG as _it_support
from config.domains.hr         import DOMAIN_CONFIG as _hr
from config.domains.billing    import DOMAIN_CONFIG as _billing

# Registry: domain_id → config dict
DOMAIN_REGISTRY: dict = {
    "it_support": _it_support,
    "hr":         _hr,
    "billing":    _billing,
    # Default fallback for any unrecognised tenant domain
    "default":    _billing,
}

__all__ = ["DOMAIN_REGISTRY"]