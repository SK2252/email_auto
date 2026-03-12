"""
config/domains/__init__.py — Domain package init.
Exposes the registry of all available domain configs.
"""
from config.domains.healthcare import DOMAIN_CONFIG as _healthcare
from config.domains.it_support  import DOMAIN_CONFIG as _it_support
from config.domains.billing      import DOMAIN_CONFIG as _billing
from config.domains.hr           import DOMAIN_CONFIG as _hr
from config.domains.legal        import DOMAIN_CONFIG as _legal
from config.domains.ecommerce    import DOMAIN_CONFIG as _ecommerce
from config.domains.education    import DOMAIN_CONFIG as _education

# Registry: domain_id → config dict
DOMAIN_REGISTRY: dict = {
    "healthcare":  _healthcare,
    "it_support":  _it_support,
    "billing":     _billing,
    "hr":          _hr,
    "legal":       _legal,
    "ecommerce":   _ecommerce,
    "education":   _education,
}

__all__ = ["DOMAIN_REGISTRY"]
