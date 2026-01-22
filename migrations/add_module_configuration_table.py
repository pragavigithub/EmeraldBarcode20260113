#!/usr/bin/env python3
"""
Migration: Add ModuleConfiguration table for module-specific settings
Date: 2026-01-22
Purpose: Add configuration table to support configurable label sizes in Multi GRN module
"""

import sys
import os
import logging
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import from the correct module structure
try:
    from app import app, db
except ImportError:
    # Alternative import if app is structured differently
    import app as flask_app
    app = flask_app.app
    db = flask_app.db

from models_extensions import ModuleConfiguration

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_module_configuration_table():
    """Create the module_configurations table"""
    try:
        with app.app_context():
            logger.info("🚀 Starting ModuleConfiguration table creation...")
            
            # Create the table
            db.create_all()
            logger.info("✅ ModuleConfiguration table created successfully")
            
            # Add default configurations for Multi GRN module
            default_configs = [
                {
                    'module_name': 'multi_grn',
                    'config_key': 'label_size',
                    'config_value': 'medium',
                    'description': 'Label size for batch printing (small, medium, large)'
                },
                {
                    'module_name': 'multi_grn',
                    'config_key': 'labels_per_row',
                    'config_value': '4',
                    'description': 'Number of labels per row (2, 3, 4, 6)'
                },
                {
                    'module_name': 'multi_grn',
                    'config_key': 'qr_code_size',
                    'config_value': '120',
                    'description': 'QR code size in pixels (80, 120, 150, 200)'
                },
                {
                    'module_name': 'multi_grn',
                    'config_key': 'print_layout',
                    'config_value': 'compact',
                    'description': 'Print layout style (compact, standard, detailed)'
                }
            ]
            
            # Insert default configurations
            for config_data in default_configs:
                existing = ModuleConfiguration.query.filter_by(
                    module_name=config_data['module_name'],
                    config_key=config_data['config_key']
                ).first()
                
                if not existing:
                    config = ModuleConfiguration(
                        module_name=config_data['module_name'],
                        config_key=config_data['config_key'],
                        config_value=config_data['config_value'],
                        description=config_data['description']
                    )
                    db.session.add(config)
                    logger.info(f"✅ Added default config: {config_data['module_name']}.{config_data['config_key']} = {config_data['config_value']}")
                else:
                    logger.info(f"⚠️ Config already exists: {config_data['module_name']}.{config_data['config_key']}")
            
            db.session.commit()
            logger.info("✅ Default configurations added successfully")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error creating ModuleConfiguration table: {str(e)}")
        import traceback
        logger.error(f"📋 Full traceback: {traceback.format_exc()}")
        return False

def rollback_migration():
    """Rollback the migration by dropping the table"""
    try:
        with app.app_context():
            logger.info("🔄 Rolling back ModuleConfiguration table...")
            
            # Drop the table
            ModuleConfiguration.__table__.drop(db.engine)
            logger.info("✅ ModuleConfiguration table dropped successfully")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error rolling back migration: {str(e)}")
        return False

def main():
    """Main migration function"""
    logger.info("=" * 60)
    logger.info("   ModuleConfiguration Table Migration")
    logger.info("=" * 60)
    
    if len(sys.argv) > 1 and sys.argv[1] == '--rollback':
        logger.info("🔄 Rollback mode selected")
        success = rollback_migration()
    else:
        logger.info("🚀 Migration mode selected")
        success = create_module_configuration_table()
    
    if success:
        logger.info("✅ Migration completed successfully!")
    else:
        logger.error("❌ Migration failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()