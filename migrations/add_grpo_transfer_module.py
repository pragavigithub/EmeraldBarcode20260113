#!/usr/bin/env python3
"""
Migration: Add GRPO Transfer Module Tables
Date: 2026-01-25
Purpose: Create database tables for QC validation and warehouse transfers
Tables:
  - grpo_transfer_sessions: Main QC validation sessions
  - grpo_transfer_items: Items in each session
  - grpo_transfer_batches: Batch numbers for batch-managed items
  - grpo_transfer_splits: Split quantities for partial approvals
  - grpo_transfer_logs: Audit trail
  - grpo_transfer_qr_labels: Generated QR labels
"""

import sys
import os
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_grpo_transfer_tables():
    """Create GRPO Transfer module tables"""
    try:
        with app.app_context():
            logger.info("🚀 Starting GRPO Transfer Module table creation...")
            
            # Import models to register them
            from modules.grpo_transfer.models import (
                GRPOTransferSession,
                GRPOTransferItem,
                GRPOTransferBatch,
                GRPOTransferSplit,
                GRPOTransferLog,
                GRPOTransferQRLabel
            )
            
            # Create all tables
            db.create_all()
            logger.info("✅ GRPO Transfer module tables created successfully")
            
            # Log table creation
            tables = [
                'grpo_transfer_sessions',
                'grpo_transfer_items',
                'grpo_transfer_batches',
                'grpo_transfer_splits',
                'grpo_transfer_logs',
                'grpo_transfer_qr_labels'
            ]
            
            for table in tables:
                logger.info(f"✅ Table created: {table}")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error creating GRPO Transfer tables: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        return False

def rollback_migration():
    """Rollback the migration by dropping tables"""
    try:
        with app.app_context():
            logger.info("🔄 Rolling back GRPO Transfer module tables...")
            
            from modules.grpo_transfer.models import (
                GRPOTransferSession,
                GRPOTransferItem,
                GRPOTransferBatch,
                GRPOTransferSplit,
                GRPOTransferLog,
                GRPOTransferQRLabel
            )
            
            # Drop tables in reverse order of dependencies
            tables = [
                GRPOTransferQRLabel.__table__,
                GRPOTransferLog.__table__,
                GRPOTransferSplit.__table__,
                GRPOTransferBatch.__table__,
                GRPOTransferItem.__table__,
                GRPOTransferSession.__table__
            ]
            
            for table in tables:
                table.drop(db.engine)
                logger.info(f"✅ Table dropped: {table.name}")
            
            logger.info("✅ GRPO Transfer module tables dropped successfully")
            return True
            
    except Exception as e:
        logger.error(f"❌ Error rolling back migration: {str(e)}")
        return False

def main():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("   GRPO Transfer Module Migration")
    logger.info("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        logger.info("🔄 Rollback mode selected")
        success = rollback_migration()
    else:
        logger.info("🚀 Migration mode selected")
        success = create_grpo_transfer_tables()
    
    if success:
        logger.info("✅ Migration completed successfully!")
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()