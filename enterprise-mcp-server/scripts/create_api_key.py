"""
CLI Tool: Create an API key from the command line.

Usage:
    python scripts/create_api_key.py --owner "admin" --scopes "search,document,email,admin"
    python scripts/create_api_key.py --owner "readonly-bot" --scopes "search" --rate-limit 30
"""

import argparse
import asyncio
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.engine import async_session_factory, dispose_engine
from app.db.repository import ApiKeyRepository


async def create_key(
    owner: str,
    scopes: list[str],
    description: str | None = None,
    environment: str = "development",
    rate_limit: int = 60,
    expires_in_days: int | None = None,
) -> None:
    """Create an API key and print the raw key."""
    async with async_session_factory() as session:
        repo = ApiKeyRepository(session)
        raw_key, api_key = await repo.create_key(
            owner=owner,
            scopes=scopes,
            description=description,
            environment=environment,
            rate_limit=rate_limit,
            expires_in_days=expires_in_days,
        )
        await session.commit()

    print("\n" + "=" * 60)
    print("  API KEY CREATED SUCCESSFULLY")
    print("=" * 60)
    print(f"  Key ID:       {api_key.id}")
    print(f"  Owner:        {owner}")
    print(f"  Scopes:       {', '.join(scopes)}")
    print(f"  Environment:  {environment}")
    print(f"  Rate Limit:   {rate_limit} req/min")
    print(f"  Status:       {api_key.status.value}")
    if api_key.expires_at:
        print(f"  Expires:      {api_key.expires_at.isoformat()}")
    print()
    print(f"  RAW KEY (store securely — shown only once):")
    print(f"  {raw_key}")
    print("=" * 60 + "\n")

    await dispose_engine()


def main():
    parser = argparse.ArgumentParser(description="Create an MCP API key")
    parser.add_argument("--owner", required=True, help="Key owner name")
    parser.add_argument(
        "--scopes", required=True,
        help="Comma-separated scopes: search,document,email,admin"
    )
    parser.add_argument("--description", default=None, help="Key description")
    parser.add_argument(
        "--environment", default="development",
        choices=["development", "staging", "production"],
    )
    parser.add_argument("--rate-limit", type=int, default=60, help="Requests per minute")
    parser.add_argument("--expires-in-days", type=int, default=None, help="Days until expiry")

    args = parser.parse_args()
    scopes = [s.strip() for s in args.scopes.split(",")]

    asyncio.run(
        create_key(
            owner=args.owner,
            scopes=scopes,
            description=args.description,
            environment=args.environment,
            rate_limit=args.rate_limit,
            expires_in_days=args.expires_in_days,
        )
    )


if __name__ == "__main__":
    main()
