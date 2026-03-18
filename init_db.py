import psycopg2
import sys
import os

# Ensure the paths are correct for imports
sys.path.insert(0, r"D:\email_auto\enterprise-mcp-server")
sys.path.insert(0, r"D:\email_auto")

from config.settings import settings

def init_db():
    # Convert asyncpg URL to psycopg2 format
    db_url = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    schema_path = r"D:\email_auto\db\schema.sql"
    
    try:
        print(f"Connecting to Supabase...")
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Verify tables
        cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
        tables = [row[0] for row in cur.fetchall()]
        
        if "emails" in tables and "tenants" in tables:
            print(f"Tables already exist: {', '.join(tables)}")
        else:
            print(f"Reading schema from {schema_path}...")
            with open(schema_path, "r", encoding="utf-8") as f:
                sql = f.read()
            print("Executing schema SQL...")
            cur.execute(sql)
            
            cur.execute("SELECT tablename FROM pg_catalog.pg_tables WHERE schemaname = 'public'")
            tables = [row[0] for row in cur.fetchall()]
            print(f"Tables created: {', '.join(tables)} SUCCESS")
        
        # Step 3: Insert demo tenant if not exists
        print("Ensuring demo tenant exists...")
        cur.execute("SELECT tenant_id FROM tenants WHERE tenant_id = 'demo_tenant'")
        if not cur.fetchone():
            cur.execute("""
                INSERT INTO tenants (tenant_id, domain_id, name, active)
                VALUES ('demo_tenant', 'ecommerce', 'Demo Company', true)
            """)
            print("Demo tenant inserted SUCCESS")
        else:
            print("Demo tenant already exists")
            
        cur.close()
        conn.close()
        print("Database initialization complete.")
    except Exception as e:
        print(f"Database initialization failed ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    init_db()
