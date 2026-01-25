# Database Migration Tracking

## Overview
This document tracks all database migrations and schema changes across all WMS modules.

## Migration History

### Version 1.0 - Core WMS (Initial)
**Date:** 2025-12-01
**Status:** ✅ Completed

**Tables Created:**
- users
- branches
- user_sessions
- inventory_transfers
- inventory_transfer_items
- pick_lists
- pick_list_items
- pick_list_lines
- inventory_counts
- inventory_count_items
- sap_inventory_counts
- sap_inventory_count_lines
- barcode_labels
- bin_scanning_logs
- document_number_series
- qr_code_labels
- direct_inventory_transfers
- direct_inventory_transfer_items
- transfer_scan_states
- inventory_transfer_request_lines

**Migration File:** `mysql_consolidated_migration.py`

---

### Version 1.1 - Module Configuration (Global Label Settings)
**Date:** 2026-01-22
**Status:** ✅ Completed

**Tables Created:**
- module_configurations

**Purpose:** Global label configuration system for all modules

**Configuration Keys:**
- `label_size` (small, medium, large)
- `labels_per_row` (2, 3, 4, 6)
- `qr_code_size` (80, 120, 150, 200)
- `print_layout` (compact, standard, detailed)

**Migration File:** `add_module_configuration_table.py`

**Default Values:**
```
global.label_size = medium
global.labels_per_row = 4
global.qr_code_size = 120
global.print_layout = compact
```

---

### Version 1.2 - GRPO Module
**Date:** 2025-12-15
**Status:** ✅ Completed

**Tables Created:**
- grpo_documents
- grpo_items
- grpo_serial_numbers
- grpo_batch_numbers
- purchase_delivery_notes

**Purpose:** GRPO document management with serial and batch tracking

**Key Features:**
- Serial number management
- Batch number tracking
- QR code label generation
- Multi-pack support

**Migration File:** Part of `mysql_consolidated_migration.py`

---

### Version 1.3 - Multi-GRN Module
**Date:** 2026-01-10
**Status:** ✅ Completed

**Tables Created:**
- multi_grn_batches

**Purpose:** Multi-GRN batch creation and management

**Key Features:**
- Multiple PO selection
- Batch number consolidation
- QR label generation
- Global label configuration support

**Migration File:** Part of `mysql_consolidated_migration.py`

---

### Version 2.0 - GRPO Transfer Module (NEW)
**Date:** 2026-01-25
**Status:** ✅ Completed

**Tables Created:**
- grpo_transfer_sessions
- grpo_transfer_items
- grpo_transfer_batches
- grpo_transfer_splits
- grpo_transfer_logs
- grpo_transfer_qr_labels

**Purpose:** QC validation and warehouse transfer management

**Key Features:**
- QC validation workflow
- Item type validation (batch/serial/non-managed)
- Quantity splitting for partial approvals
- Warehouse transfer management
- SAP B1 stock transfer integration
- QR label generation for approved items
- Complete audit trail

**Workflow Steps:**
1. Get GRPO series list
2. Select GRPO document
3. Validate item types
4. QC team approves/rejects items
5. Split quantities if needed
6. Generate QR labels
7. Post stock transfer to SAP B1

**Migration File:** `add_grpo_transfer_module.py`

**Consolidated File:** `mysql_consolidated_migration_v2.py`

---

## Database Schema Relationships

### Core Tables
```
users (1) ──→ (N) user_sessions
users (1) ──→ (N) inventory_transfers
users (1) ──→ (N) pick_lists
users (1) ──→ (N) inventory_counts
```

### GRPO Module
```
grpo_documents (1) ──→ (N) grpo_items
grpo_items (1) ──→ (N) grpo_serial_numbers
grpo_items (1) ──→ (N) grpo_batch_numbers
```

### Multi-GRN Module
```
multi_grn_batches (1) ──→ (N) grpo_items
```

### GRPO Transfer Module
```
grpo_transfer_sessions (1) ──→ (N) grpo_transfer_items
grpo_transfer_sessions (1) ──→ (N) grpo_transfer_logs
grpo_transfer_sessions (1) ──→ (N) grpo_transfer_qr_labels

grpo_transfer_items (1) ──→ (N) grpo_transfer_batches
grpo_transfer_items (1) ──→ (N) grpo_transfer_splits
```

### Configuration
```
module_configurations (global settings for all modules)
```

---

## Migration Commands

### Run Individual Module Migration
```bash
# GRPO Transfer Module only
python migrations/add_grpo_transfer_module.py

# Rollback GRPO Transfer Module
python migrations/add_grpo_transfer_module.py --rollback
```

### Run Consolidated Migration (All Modules)
```bash
# Version 1.0 (Core WMS)
python migrations/mysql_consolidated_migration.py

# Version 2.0 (All modules including GRPO Transfer)
python migrations/mysql_consolidated_migration_v2.py

# Rollback all tables
python migrations/mysql_consolidated_migration_v2.py --rollback
```

---

## Table Statistics

### Total Tables: 31

**By Module:**
- Core WMS: 20 tables
- Module Configuration: 1 table
- GRPO Module: 5 tables
- Multi-GRN Module: 1 table
- GRPO Transfer Module: 6 tables

### Total Relationships: 15+

---

## Data Migration Notes

### When Adding New Module

1. **Create Models File**
   - Location: `modules/<module_name>/models.py`
   - Define all SQLAlchemy models

2. **Create Migration File**
   - Location: `migrations/add_<module_name>_module.py`
   - Include create and rollback functions
   - Add logging for all operations

3. **Update Consolidated Migration**
   - Add module imports to `mysql_consolidated_migration_v2.py`
   - Add tables to documentation
   - Update version number

4. **Create Routes File**
   - Location: `modules/<module_name>/routes.py`
   - Define all API endpoints
   - Register blueprint in `main.py`

5. **Create Documentation**
   - Add module guide (e.g., `GRPO_TRANSFER_MODULE_GUIDE.md`)
   - Document all endpoints
   - Include workflow steps

6. **Update This File**
   - Add new version entry
   - Document tables and features
   - Update statistics

---

## Backup & Recovery

### Before Running Migration
```bash
# Backup current database
mysqldump -u root -p emrald > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restore from Backup
```bash
# Restore database
mysql -u root -p emrald < backup_20260125_120000.sql
```

---

## Version Compatibility

| Version | Date | Status | Python | Flask | SQLAlchemy |
|---------|------|--------|--------|-------|------------|
| 1.0 | 2025-12-01 | ✅ | 3.8+ | 2.0+ | 1.4+ |
| 1.1 | 2026-01-22 | ✅ | 3.8+ | 2.0+ | 1.4+ |
| 1.2 | 2025-12-15 | ✅ | 3.8+ | 2.0+ | 1.4+ |
| 1.3 | 2026-01-10 | ✅ | 3.8+ | 2.0+ | 1.4+ |
| 2.0 | 2026-01-25 | ✅ | 3.8+ | 2.0+ | 1.4+ |

---

## Future Migrations

### Planned Modules

1. **Inventory Counting Module** (v2.1)
   - Advanced counting workflows
   - Variance tracking
   - Approval workflows

2. **Serial Item Transfer Module** (v2.2)
   - Serial number tracking
   - Transfer history
   - Warranty tracking

3. **Pick List Module** (v2.3)
   - Advanced picking workflows
   - Wave management
   - Batch picking

4. **QC Dashboard Module** (v2.4)
   - Real-time metrics
   - Performance tracking
   - Reporting

---

## Maintenance

### Regular Tasks

- **Weekly:** Check migration logs for errors
- **Monthly:** Verify database integrity
- **Quarterly:** Archive old logs
- **Annually:** Review and optimize schema

### Performance Optimization

- Add indexes on frequently queried columns
- Archive old audit logs
- Optimize foreign key constraints
- Monitor query performance

---

## Support & Documentation

- **Migration Guide:** See individual module documentation
- **API Documentation:** See module guide files
- **Troubleshooting:** Check application logs
- **Contact:** Development team