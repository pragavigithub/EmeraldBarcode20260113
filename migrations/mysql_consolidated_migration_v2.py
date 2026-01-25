#!/usr/bin/env python3
"""
Consolidated MySQL Migration Script - All WMS Tables (Version 2)
Combines all migration scripts into a single comprehensive file.

INCLUDES:
✅ Core WMS tables (users, branches, sessions)
✅ Module Configuration (global label settings)
✅ GRPO module with serial/batch number support
✅ Multi-GRN module with enhanced QR label generation
✅ GRPO Transfer module (NEW):
   - QC validation sessions
   - Item splitting for partial approvals
   - Batch number tracking
   - Warehouse transfer management
   - QR label generation for approved items
✅ Inventory transfers and serial transfers
✅ Pick lists and QC workflows
✅ Serial item transfers
✅ Document number series
✅ Performance optimizations and indexing

Date: 2026-01-25
Version: 2.0
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

def create_all_tables():
    """Create all WMS tables"""
    try:
        with app.app_context():
            logger.info("🚀 Starting Consolidated WMS Migration (v2)...")
            logger.info("=" * 60)
            
            # Import all models to register them
            logger.info("📦 Importing core models...")
            from models import (
                User, InventoryTransfer, InventoryTransferItem,
                PickList, PickListItem, InventoryCount, InventoryCountItem,
                SAPInventoryCount, SAPInventoryCountLine, BarcodeLabel,
                BinScanningLog, DocumentNumberSeries, QRCodeLabel,
                PickListLine, DirectInventoryTransfer, DirectInventoryTransferItem,
                TransferScanState, InventoryTransferRequestLine
            )
            
            logger.info("📦 Importing models_extensions...")
            from models_extensions import Branch, UserSession, ModuleConfiguration
            
            logger.info("📦 Importing GRPO module models...")
            from modules.grpo.models import (
                GRPODocument, GRPOItem, GRPOSerialNumber, GRPOBatchNumber,
                PurchaseDeliveryNote
            )
            
            logger.info("📦 Importing Multi-GRN module models...")
            from modules.multi_grn_creation.models import MultiGRNBatch
            
            logger.info("📦 Importing GRPO Transfer module models...")
            from modules.grpo_transfer.models import (
                GRPOTransferSession, GRPOTransferItem, GRPOTransferBatch,
                GRPOTransferSplit, GRPOTransferLog, GRPOTransferQRLabel
            )
            
            # Create all tables
            logger.info("\n🔨 Creating all tables...")
            db.create_all()
            logger.info("✅ All tables created successfully")
            
            # Log created tables
            logger.info("\n📋 Created Tables:")
            logger.info("=" * 60)
            
            core_tables = [
                'users', 'branches', 'user_sessions', 'module_configurations',
                'inventory_transfers', 'inventory_transfer_items',
                'pick_lists', 'pick_list_items', 'pick_list_lines',
                'inventory_counts', 'inventory_count_items',
                'sap_inventory_counts', 'sap_inventory_count_lines',
                'barcode_labels', 'bin_scanning_logs',
                'document_number_series', 'qr_code_labels',
                'direct_inventory_transfers', 'direct_inventory_transfer_items',
                'transfer_scan_states', 'inventory_transfer_request_lines'
            ]
            
            grpo_tables = [
                'grpo_documents', 'grpo_items',
                'grpo_serial_numbers', 'grpo_batch_numbers',
                'purchase_delivery_notes'
            ]
            
            multi_grn_tables = [
                'multi_grn_batches'
            ]
            
            grpo_transfer_tables = [
                'grpo_transfer_sessions', 'grpo_transfer_items',
                'grpo_transfer_batches', 'grpo_transfer_splits',
                'grpo_transfer_logs', 'grpo_transfer_qr_labels'
            ]
            
            logger.info("\n🔹 Core WMS Tables:")
            for table in core_tables:
                logger.info(f"   ✅ {table}")
            
            logger.info("\n🔹 GRPO Module Tables:")
            for table in grpo_tables:
                logger.info(f"   ✅ {table}")
            
            logger.info("\n🔹 Multi-GRN Module Tables:")
            for table in multi_grn_tables:
                logger.info(f"   ✅ {table}")
            
            logger.info("\n🔹 GRPO Transfer Module Tables (NEW):")
            for table in grpo_transfer_tables:
                logger.info(f"   ✅ {table}")
            
            logger.info("\n" + "=" * 60)
            logger.info("✅ Consolidated migration completed successfully!")
            logger.info("=" * 60)
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error during migration: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        return False

def rollback_all_tables():
    """Rollback all tables"""
    try:
        with app.app_context():
            logger.info("🔄 Rolling back all WMS tables...")
            logger.info("=" * 60)
            
            # Drop all tables
            db.drop_all()
            logger.info("✅ All tables dropped successfully")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error rolling back: {str(e)}")
        return False

def main():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("   Consolidated WMS Migration (v2)")
    logger.info("   All Modules and Tables")
    logger.info("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        logger.info("🔄 Rollback mode selected")
        success = rollback_all_tables()
    else:
        logger.info("🚀 Migration mode selected")
        success = create_all_tables()
    
    if success:
        logger.info("\n✅ Migration completed successfully!")
        sys.exit(0)
    else:
        logger.error("\n❌ Migration failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()