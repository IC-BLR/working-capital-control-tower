"""
Synthetic data generator for seeding database.
"""
import logging
import random
from datetime import date, timedelta
from typing import List, Tuple
import duckdb

logger = logging.getLogger(__name__)


class SeedDataGenerator:
    """Generates synthetic invoice and payment data."""
    
    # Partner names for realistic data
    PARTNER_NAMES = [
        "Acme Corporation", "Tech Solutions Inc", "Global Industries Ltd",
        "Digital Services Co", "Manufacturing Partners", "Retail Ventures",
        "Supply Chain Solutions", "Enterprise Systems", "Innovation Labs",
        "Business Services Group", "Trade Partners LLC", "Commercial Services",
        "Industrial Solutions", "Logistics Partners", "Distribution Co",
        "Service Providers Inc", "Technology Partners", "Business Associates",
        "Corporate Services", "Professional Group", "Strategic Partners",
        "Value Services", "Premium Solutions", "Quality Services",
        "Reliable Partners", "Trusted Services", "Excellence Corp",
        "Prime Solutions", "Elite Services", "Advanced Partners"
    ]
    
    def __init__(self):
        """Initialize seed data generator."""
        pass
    
    @staticmethod
    def _generate_partner_code(index: int) -> str:
        """Generate partner code."""
        return f"PART{index:04d}"
    
    @staticmethod
    def _generate_invoice_number(partner_code: str, index: int) -> str:
        """Generate invoice number."""
        return f"INV-{partner_code}-{index:05d}"
    
    @staticmethod
    def _generate_payment_reference(index: int) -> float:
        """Generate payment reference number."""
        return float(1000000 + index)
    
    @staticmethod
    def _random_date(start: date, end: date) -> date:
        """Generate random date between start and end."""
        return start + timedelta(days=random.randint(0, (end - start).days))
    
    @staticmethod
    def _generate_payment_scenario() -> dict:
        """Generate payment scenario (on-time, overdue, partial, etc.)."""
        scenario_type = random.choices(
            ["on_time", "overdue_short", "overdue_long", "partial", "fully_paid"],
            weights=[40, 25, 10, 15, 10]
        )[0]
        
        scenarios = {
            "on_time": (-5, 0, 1.0),
            "overdue_short": (1, 30, (0.7, 0.95)),
            "overdue_long": (31, 120, (0.3, 0.7)),
            "partial": (0, 45, (0.2, 0.8)),
            "fully_paid": (-5, 15, 1.0)
        }
        
        delay_min, delay_max, ratio = scenarios[scenario_type]
        delay_days = random.randint(delay_min, delay_max)
        payment_ratio = ratio if isinstance(ratio, float) else random.uniform(*ratio)
        
        return {"delay_days": delay_days, "payment_ratio": payment_ratio}
    
    def generate_payment_allocations(
        self, 
        num_partners: int = 25,
        invoices_per_partner: int = 15,
        min_amount: float = 10000.0,
        max_amount: float = 500000.0
    ) -> List[Tuple]:
        """
        Generate synthetic payment allocation records.
        
        Args:
            num_partners: Number of partners to generate
            invoices_per_partner: Number of invoices per partner
            min_amount: Minimum invoice amount
            max_amount: Maximum invoice amount
            
        Returns:
            List of tuples ready for INSERT
        """
        logger.info(f"Generating synthetic data: {num_partners} partners, {invoices_per_partner} invoices each")
        
        end_date = date.today()
        start_date = end_date - timedelta(days=180)
        records = []
        record_index = 0
        
        # Weekly snapshots for last 6 months
        run_dates = [end_date - timedelta(days=x) for x in range(0, 180, 7)]
        
        for partner_idx in range(1, num_partners + 1):
            partner_code = self._generate_partner_code(partner_idx)
            partner_name = random.choice(self.PARTNER_NAMES)
            
            # Generate invoices for this partner
            for invoice_idx in range(1, invoices_per_partner + 1):
                invoice_number = self._generate_invoice_number(partner_code, invoice_idx)
                invoice_amount = round(random.uniform(min_amount, max_amount), 2)
                
                # Invoice date (30-180 days ago)
                invoice_date = self._random_date(
                    start_date,
                    end_date - timedelta(days=30)
                )
                
                # Due date (15-45 days after invoice)
                due_date = invoice_date + timedelta(days=random.randint(15, 45))
                
                # Generate payment scenarios across run dates
                scenario = self._generate_payment_scenario()
                delay_days = scenario["delay_days"]
                payment_ratio = scenario["payment_ratio"]
                
                # Payment date (can't be before invoice)
                payment_date = max(invoice_date, due_date + timedelta(days=delay_days))
                
                # Calculate amounts
                due_amount = invoice_amount * (1.0 - payment_ratio) if payment_ratio < 1.0 else 0.0
                payment_amount = invoice_amount * payment_ratio
                allocated_amount = payment_amount  # Assume full allocation
                
                # Create records for multiple run dates
                for run_date in run_dates:
                    # Only include if invoice exists by this run date
                    if invoice_date > run_date:
                        continue
                    
                    # Adjust amounts based on run date
                    payment_occurred = run_date >= payment_date
                    current_due = max(0, invoice_amount - allocated_amount) if payment_occurred else invoice_amount
                    current_allocated = allocated_amount if payment_occurred else 0.0
                    payment_ref = self._generate_payment_reference(record_index) if payment_occurred and payment_amount > 0 else None
                    
                    record = (
                        run_date,
                        partner_code,
                        partner_name,
                        invoice_number,
                        payment_ref,
                        invoice_date,
                        invoice_amount,
                        due_date,
                        current_due,
                        payment_date if payment_occurred else None,
                        payment_amount if payment_occurred else None,
                        current_allocated
                    )
                    
                    records.append(record)
                    record_index += 1
        
        logger.info(f"Generated {len(records)} payment allocation records")
        return records
    
    def seed(self, conn: duckdb.DuckDBPyConnection, min_records: int = 100):
        """
        Seed database with synthetic data if below threshold.
        
        Args:
            conn: DuckDB connection
            min_records: Minimum number of records required
        """
        try:
            # Check current count
            result = conn.execute("SELECT COUNT(*) FROM payment_allocations").fetchone()
            current_count = result[0] if result else 0
            
            if current_count >= min_records:
                logger.info(f"Database has {current_count} records (>= {min_records}) - skipping seed")
                return
            
            # Generate fixed amount: 10 partners with 5 invoices each
            # This ensures consistent data for all UI screens
            logger.info(f"Generating 10 partners with 5 invoices each")
            records = self.generate_payment_allocations(num_partners=10, invoices_per_partner=5)
            
            # Insert in batches (DuckDB doesn't support executemany, use execute with VALUES)
            batch_size = 500
            total_inserted = 0
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                values_list = []
                
                for record in batch:
                    formatted = []
                    for val in record:
                        if val is None:
                            formatted.append("NULL")
                        elif isinstance(val, str):
                            escaped_val = val.replace("'", "''")
                            formatted.append(f"'{escaped_val}'")
                        elif isinstance(val, date):
                            formatted.append(f"DATE '{val.isoformat()}'")
                        else:
                            formatted.append(str(val))
                    values_list.append(f"({', '.join(formatted)})")
                
                conn.execute(f"""
                    INSERT INTO payment_allocations (
                        "Run Date", "Partner Code", "Partner Name", "Invoice Number",
                        "Paymt Ref", "Invoice Date", "Invoice Amount", "Due Date",
                        "Due Amount", "Pymnt Dt", "Payment Amount", "Allocated Amt"
                    ) VALUES {', '.join(values_list)}
                """)
                
                total_inserted += len(batch)
                logger.debug(f"Inserted batch: {len(batch)} records (total: {total_inserted})")
            
            logger.info(f"✓ Seeded {total_inserted} payment allocation records")
            
        except Exception as e:
            logger.error(f"Failed to seed database: {e}", exc_info=True)
            raise

