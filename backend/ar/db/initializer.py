"""
Idempotent database initializer.
Handles migrations, seeding, and locking.
"""
import os
import logging
import time
import sys
from pathlib import Path
from typing import Optional
from contextlib import contextmanager
import duckdb

# Cross-platform file locking
if sys.platform == "win32":
    _HAS_FCNTL = False
else:
    try:
        import fcntl
        _HAS_FCNTL = True
    except ImportError:
        _HAS_FCNTL = False

from ar.db.migration_manager import MigrationManager
from ar.db.seed_data import SeedDataGenerator

logger = logging.getLogger(__name__)


class DatabaseInitializer:
    """Idempotent database initialization orchestrator."""
    
    def __init__(self, db_path: str):
        """
        Initialize database initializer.
        
        Args:
            db_path: Path to DuckDB database file
        """
        self.db_path = Path(db_path)
        self.lock_file = self.db_path.parent / ".db_init.lock"
        self.migration_manager = MigrationManager()
        self.seed_generator = SeedDataGenerator()
    
    @contextmanager
    def _acquire_lock(self, timeout: int = 30):
        """
        Acquire file-based lock for migration/seeding.
        
        Args:
            timeout: Maximum seconds to wait for lock
        """
        self.lock_file.parent.mkdir(parents=True, exist_ok=True)
        start_time = time.time()
        lock_fd = None
        
        try:
            # Try to acquire lock
            while time.time() - start_time < timeout:
                try:
                    # Check for stale lock (older than 5 minutes)
                    if self.lock_file.exists():
                        lock_age = time.time() - self.lock_file.stat().st_mtime
                        if lock_age > 300:
                            logger.warning(f"Removing stale lock (age: {lock_age:.0f}s)")
                            self.lock_file.unlink()
                        else:
                            time.sleep(0.5)
                            continue
                    
                    # Create lock file exclusively
                    lock_fd = open(self.lock_file, 'x')
                    lock_fd.write(str(os.getpid()))
                    lock_fd.flush()
                    
                    # Acquire OS-level lock if available
                    if sys.platform != "win32" and _HAS_FCNTL:
                        try:
                            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                        except (IOError, OSError):
                            lock_fd.close()
                            self.lock_file.unlink(missing_ok=True)
                            time.sleep(0.5)
                            continue
                    
                    logger.debug("Acquired initialization lock")
                    yield
                    return
                    
                except FileExistsError:
                    time.sleep(0.5)
                except (IOError, OSError):
                    if lock_fd:
                        lock_fd.close()
                        lock_fd = None
                    time.sleep(0.5)
            
            raise TimeoutError(f"Could not acquire lock within {timeout} seconds")
            
        finally:
            if lock_fd:
                try:
                    if sys.platform != "win32" and _HAS_FCNTL:
                        fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)
                    lock_fd.close()
                    self.lock_file.unlink(missing_ok=True)
                    logger.debug("Released initialization lock")
                except Exception as e:
                    logger.warning(f"Error releasing lock: {e}")
    
    def _should_seed(self, conn: duckdb.DuckDBPyConnection) -> bool:
        """
        Check if seeding should run.
        
        Args:
            conn: DuckDB connection
            
        Returns:
            True if seeding should run
        """
        # Environment check
        env = os.getenv("ENVIRONMENT", "dev").lower()
        enable_seed = os.getenv("ENABLE_SEED_DATA", "true").lower() == "true"
        
        if env == "prod":
            logger.info("Production environment - skipping seed data")
            return False
        
        if not enable_seed:
            logger.info("Seed data disabled via ENABLE_SEED_DATA=false")
            return False
        
        # Data threshold check
        try:
            result = conn.execute("SELECT COUNT(*) FROM payment_allocations").fetchone()
            count = result[0] if result else 0
            min_threshold = int(os.getenv("MIN_DATA_THRESHOLD", "100"))
            
            if count >= min_threshold:
                logger.info(f"Database has {count} records (>= {min_threshold}) - skipping seed")
                return False
            
            logger.info(f"Database has {count} records (< {min_threshold}) - will seed")
            return True
        except Exception as e:
            logger.warning(f"Could not check data count: {e} - will attempt seed")
            return True
    
    def initialize(self) -> duckdb.DuckDBPyConnection:
        """
        Main initialization entry point.
        
        Returns:
            Initialized DuckDB connection
            
        Raises:
            Exception: If initialization fails
        """
        logger.info(f"Initializing database: {self.db_path}")
        
        with self._acquire_lock():
            # Connect to DB (creates if not exists)
            db_exists = self.db_path.exists()
            if db_exists:
                logger.info(f"Database file exists - opening existing database")
            else:
                logger.info(f"Database file does not exist - will create new database")
            
            conn = duckdb.connect(str(self.db_path))
            
            try:
                # Run migrations
                logger.info("Running migrations...")
                applied = self.migration_manager.run_migrations(conn)
                if applied > 0:
                    logger.info(f"✓ Applied {applied} migration(s)")
                else:
                    logger.info("✓ All migrations up to date")
                
                # Seed data if needed
                if self._should_seed(conn):
                    logger.info("Seeding database with synthetic data...")
                    self.seed_generator.seed(conn)
                    logger.info("✓ Database seeding complete")
                else:
                    logger.info("✓ Database seeding skipped")
                
                logger.info("✓ Database initialization complete")
                return conn
                
            except Exception as e:
                logger.error(f"Database initialization failed: {e}", exc_info=True)
                conn.close()
                raise

