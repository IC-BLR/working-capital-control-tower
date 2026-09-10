"""
Migration manager for tracking and executing database migrations.
"""
import importlib.util
import logging
import os
from pathlib import Path
from typing import List, Tuple, Optional
import duckdb

logger = logging.getLogger(__name__)


class MigrationManager:
    """Manages database schema migrations."""
    
    def __init__(self, migrations_dir: Optional[Path] = None):
        """
        Initialize migration manager.
        
        Args:
            migrations_dir: Directory containing migration files (defaults to app/db/migrations)
        """
        if migrations_dir is None:
            migrations_dir = Path(__file__).parent / "migrations"
        self.migrations_dir = migrations_dir
    
    def _ensure_migrations_table(self, conn: duckdb.DuckDBPyConnection):
        """Create schema_migrations table if it doesn't exist."""
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS schema_migrations (
                    migration_id VARCHAR PRIMARY KEY,
                    description VARCHAR,
                    applied_at TIMESTAMP DEFAULT now()
                )
            """)
            logger.debug("schema_migrations table ensured")
        except Exception as e:
            logger.error(f"Failed to create schema_migrations table: {e}", exc_info=True)
            raise
    
    def _get_applied_migrations(self, conn: duckdb.DuckDBPyConnection) -> set:
        """Get set of already applied migration IDs."""
        try:
            rows = conn.execute("SELECT migration_id FROM schema_migrations").fetchall()
            return {row[0] for row in rows}
        except Exception as e:
            logger.warning(f"Could not read applied migrations: {e}")
            return set()
    
    def _load_migration_files(self) -> List[Tuple[str, Path]]:
        """Load all migration files sorted by name."""
        migrations = []
        if not self.migrations_dir.exists():
            logger.warning(f"Migrations directory not found: {self.migrations_dir}")
            return migrations
        
        for file_path in sorted(self.migrations_dir.glob("*.py")):
            if file_path.name == "__init__.py":
                continue
            migration_id = file_path.stem
            migrations.append((migration_id, file_path))
        
        logger.info(f"Found {len(migrations)} migration files")
        return migrations
    
    def _load_migration_module(self, migration_id: str, file_path: Path):
        """Dynamically load a migration module."""
        try:
            # Import the migration module
            spec = importlib.util.spec_from_file_location(migration_id, file_path)
            if spec is None or spec.loader is None:
                raise ValueError(f"Could not load spec for {migration_id}")
            
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            return module
        except Exception as e:
            logger.error(f"Failed to load migration {migration_id}: {e}", exc_info=True)
            raise
    
    def run_migrations(self, conn: duckdb.DuckDBPyConnection) -> int:
        """
        Run all pending migrations.
        
        Args:
            conn: DuckDB connection
            
        Returns:
            Number of migrations applied
        """
        self._ensure_migrations_table(conn)
        applied = self._get_applied_migrations(conn)
        migrations = self._load_migration_files()
        
        applied_count = 0
        
        for migration_id, file_path in migrations:
            if migration_id in applied:
                logger.debug(f"Migration {migration_id} already applied - skipping")
                continue
            
            logger.info(f"Applying migration: {migration_id}")
            try:
                module = self._load_migration_module(migration_id, file_path)
                
                # Get migration functions - support both old and new format
                if not hasattr(module, "up"):
                    logger.error(f"Migration {migration_id} missing 'up' function")
                    continue
                
                up_func = module.up
                # Support both MIGRATION_ID/DESCRIPTION constants and get_description() function
                if hasattr(module, "DESCRIPTION"):
                    description = module.DESCRIPTION
                else:
                    description = getattr(module, "get_description", lambda: migration_id)()
                
                # Execute migration
                statements = up_func(conn)
                if not isinstance(statements, list):
                    statements = [statements] if statements else []
                
                for stmt, desc in statements:
                    if isinstance(stmt, str) and stmt.strip():
                        try:
                            conn.execute(stmt)
                            logger.debug(f"  ✓ {desc}")
                        except Exception as e:
                            logger.error(f"  ✗ Failed: {desc} - {e}")
                            raise
                
                # Record migration
                conn.execute("""
                    INSERT INTO schema_migrations (migration_id, description)
                    VALUES (?, ?)
                """, [migration_id, description])
                
                applied_count += 1
                logger.info(f"✓ Migration {migration_id} applied successfully")
                
            except Exception as e:
                logger.error(f"Failed to apply migration {migration_id}: {e}", exc_info=True)
                raise
        
        if applied_count == 0:
            logger.info("All migrations up to date")
        else:
            logger.info(f"Applied {applied_count} migration(s)")
        
        return applied_count

