# GRPO Transfer Module - Complete Implementation Guide

## 📋 Overview

The GRPO Transfer Module is a comprehensive QC validation and warehouse transfer system that integrates with SAP B1. It allows quality teams to validate received goods, split quantities for partial approvals, and manage warehouse transfers with full traceability.

## 🏗️ Architecture

### Database Models

#### 1. **GRPOTransferSession**
Main session for QC validation
- `session_code`: Unique identifier (GRPO-{DocEntry}-{Timestamp})
- `grpo_doc_entry`: Reference to SAP B1 GRPO document
- `status`: draft → in_progress → completed → transferred
- `qc_approved_by`: User who approved items
- `transfer_doc_entry`: SAP B1 StockTransfer DocEntry (after posting)

#### 2. **GRPOTransferItem**
Individual items in the session
- `item_code`, `item_name`: Item details
- `is_batch_item`, `is_serial_item`, `is_non_managed`: Item type flags
- `received_quantity`: Original quantity from GRPO
- `approved_quantity`, `rejected_quantity`: QC split quantities
- `from_warehouse`, `to_warehouse`: Warehouse routing
- `qc_status`: pending → approved → rejected → partial

#### 3. **GRPOTransferBatch**
Batch numbers for batch-managed items
- `batch_number`: SAP B1 batch identifier
- `batch_quantity`: Original quantity
- `approved_quantity`, `rejected_quantity`: QC split
- `expiry_date`, `manufacture_date`: Batch details

#### 4. **GRPOTransferSplit**
Quantity splits for partial approvals
- `split_number`: Sequential split identifier
- `quantity`: Split quantity
- `status`: 'OK', 'NOTOK', 'HOLD'
- `from_warehouse`, `to_warehouse`: Warehouse routing per split
- `batch_number`: Batch for this split (if batch item)

#### 5. **GRPOTransferLog**
Audit trail for all activities
- `action`: created, item_added, qc_approved, transferred, etc.
- `sap_response`: Stores SAP B1 API responses
- `status`: success, error, warning

#### 6. **GRPOTransferQRLabel**
Generated QR labels for approved items
- `qr_data`: JSON encoded label data
- `label_number`: 1 of N
- `batch_number`: For batch items

## 🔄 Workflow Steps

### Step 1: Get Series List
**Endpoint:** `GET /grpo-transfer/api/series-list`

Fetches GRPO series from SAP B1 using SQL Query `GET_GRPO_Series`

**Response:**
```json
{
  "success": true,
  "series": [
    {"SeriesID": 17, "SeriesName": "Primary"},
    {"SeriesID": 181, "SeriesName": "GRN 2324"},
    {"SeriesID": 241, "SeriesName": "GRN 2526"}
  ]
}
```

### Step 2: Get Document Numbers
**Endpoint:** `GET /grpo-transfer/api/doc-numbers/<series_id>`

Fetches open GRPO documents for selected series

**Response:**
```json
{
  "success": true,
  "documents": [
    {
      "DocEntry": 7840,
      "DocNum": 123450102,
      "CardName": "3D SEALS PRIVATE LIMITED",
      "DocStatus": "O"
    }
  ]
}
```

### Step 3: Get GRPO Document Details
**Endpoint:** `GET /grpo-transfer/api/grpo-details/<doc_entry>`

Fetches complete GRPO document with all line items

**Response:**
```json
{
  "success": true,
  "document": {
    "DocEntry": 7840,
    "DocNum": 123450102,
    "CardCode": "3D SPL",
    "CardName": "3D SEALS PRIVATE LIMITED",
    "DocDate": "2025-12-16",
    "DocTotal": 6072000.0
  },
  "line_items": [
    {
      "LineNum": 0,
      "ItemCode": "BOM_Item_1",
      "ItemDescription": "BOM_Item_Batch_1",
      "Quantity": 1000.0,
      "WarehouseCode": "7000-FG"
    }
  ]
}
```

### Step 4: Create Transfer Session
**Endpoint:** `POST /grpo-transfer/api/create-session`

Creates a new QC validation session

**Request:**
```json
{
  "grpo_doc_entry": 7840,
  "grpo_doc_num": "123450102",
  "series_id": 241,
  "vendor_code": "3D SPL",
  "vendor_name": "3D SEALS PRIVATE LIMITED",
  "doc_date": "2025-12-16",
  "doc_total": 6072000.0
}
```

**Response:**
```json
{
  "success": true,
  "session_id": 1,
  "session_code": "GRPO-7840-20260125120000"
}
```

### Step 5: Validate Item Type
**Endpoint:** `GET /grpo-transfer/api/validate-item/<item_code>`

Validates if item is batch-managed, serial-managed, or non-managed

**Response:**
```json
{
  "success": true,
  "item_code": "BOM_Item_1",
  "item_name": "BOM_Item_Batch_1",
  "is_batch_item": true,
  "is_serial_item": false,
  "is_non_managed": false
}
```

### Step 6: Get Batch Numbers
**Endpoint:** `GET /grpo-transfer/api/batch-numbers/<doc_entry>`

Fetches batch numbers for batch-managed items in GRPO

**Response:**
```json
{
  "success": true,
  "batches": [
    {
      "BatchNum": "20251216-BOM_Item_1",
      "Quantity": 1000.0,
      "ExpDate": "20270108",
      "ItemCode": "BOM_Item_1"
    }
  ]
}
```

### Step 7: Get Warehouses
**Endpoint:** `GET /grpo-transfer/api/warehouses`

Fetches all warehouses from SAP B1

**Response:**
```json
{
  "success": true,
  "warehouses": [
    {"WarehouseCode": "7000-FG", "WarehouseName": "Finished Goods"},
    {"WarehouseCode": "QHG-AVS", "WarehouseName": "Quality Hold Goods - AVS"}
  ]
}
```

### Step 8: Get Bin Codes
**Endpoint:** `GET /grpo-transfer/api/bin-codes/<warehouse_code>`

Fetches bin locations for selected warehouse

**Response:**
```json
{
  "success": true,
  "bins": [
    {"BinCode": "7000-FG-A103", "AbsEntry": 2, "Warehouse": "7000-FG"},
    {"BinCode": "7000-FG-J-830", "AbsEntry": 4, "Warehouse": "7000-FG"}
  ]
}
```

### Step 9: Add Item to Session
**Endpoint:** `POST /grpo-transfer/api/session/<session_id>/add-item`

Adds item to transfer session

**Request:**
```json
{
  "line_num": 0,
  "item_code": "BOM_Item_1",
  "item_name": "BOM_Item_Batch_1",
  "is_batch_item": true,
  "received_quantity": 1000,
  "from_warehouse": "7000-FG",
  "sap_base_entry": 7840,
  "sap_base_line": 0
}
```

### Step 10: QC Approval with Splits
**Endpoint:** `POST /grpo-transfer/api/session/<session_id>/qc-approve`

QC team approves/rejects items with optional quantity splits

**Request:**
```json
{
  "items": [
    {
      "item_id": 1,
      "approved_quantity": 600,
      "rejected_quantity": 400,
      "qc_status": "partial",
      "to_warehouse": "QHG-AVS",
      "to_bin_code": "QHG-AVS-BIN-1",
      "splits": [
        {
          "split_number": 1,
          "quantity": 600,
          "status": "OK",
          "from_warehouse": "7000-FG",
          "from_bin_code": "7000-FG-A103",
          "to_warehouse": "QHG-AVS",
          "to_bin_code": "QHG-AVS-BIN-1",
          "batch_number": "20251216-BOM_Item_1"
        },
        {
          "split_number": 2,
          "quantity": 400,
          "status": "NOTOK",
          "from_warehouse": "7000-FG",
          "from_bin_code": "7000-FG-A103",
          "to_warehouse": "REJ-AVS",
          "to_bin_code": "REJ-AVS-BIN-1",
          "batch_number": "20251216-BOM_Item_1",
          "notes": "Quality issues detected"
        }
      ]
    }
  ]
}
```

### Step 11: Generate QR Labels
**Endpoint:** `POST /grpo-transfer/api/session/<session_id>/generate-qr-labels`

Generates QR labels for approved items (same format as Multi-GRN module)

**Response:**
```json
{
  "success": true,
  "labels_generated": 600,
  "labels": [
    {
      "session_code": "GRPO-7840-20260125120000",
      "item_code": "BOM_Item_1",
      "quantity": 1,
      "label": "1 of 600",
      "from_warehouse": "7000-FG",
      "to_warehouse": "QHG-AVS",
      "batch_number": "20251216-BOM_Item_1"
    }
  ]
}
```

### Step 12: Post Stock Transfer to SAP B1
**Endpoint:** `POST /grpo-transfer/api/session/<session_id>/post-transfer`

Posts approved items as stock transfer to SAP B1

**SAP B1 Request:**
```json
{
  "DocDate": "2025-12-16",
  "Comments": "QC Approved WMS Transfer GRPO-7840-20260125120000 by Admin",
  "FromWarehouse": "7000-FG",
  "ToWarehouse": "QHG-AVS",
  "StockTransferLines": [
    {
      "LineNum": 0,
      "ItemCode": "BOM_Item_1",
      "Quantity": 600,
      "WarehouseCode": "QHG-AVS",
      "FromWarehouseCode": "7000-FG",
      "BaseEntry": 7840,
      "BaseLine": 0,
      "BaseType": "1250000001",
      "BatchNumbers": [
        {
          "BatchNumber": "20251216-BOM_Item_1",
          "Quantity": 600
        }
      ],
      "StockTransferLinesBinAllocations": [
        {
          "BinActionType": "batFromWarehouse",
          "BinAbsEntry": 2,
          "Quantity": 600,
          "SerialAndBatchNumbersBaseLine": 0
        },
        {
          "BinActionType": "batToWarehouse",
          "BinAbsEntry": 1,
          "Quantity": 600,
          "SerialAndBatchNumbersBaseLine": 0
        }
      ]
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "sap_doc_entry": 12345,
  "sap_doc_num": "ST-001",
  "message": "Stock transfer posted to SAP B1 successfully"
}
```

## 📊 Database Schema

### Tables Created

1. **grpo_transfer_sessions** - Main QC sessions
2. **grpo_transfer_items** - Items in sessions
3. **grpo_transfer_batches** - Batch numbers
4. **grpo_transfer_splits** - Quantity splits
5. **grpo_transfer_logs** - Audit trail
6. **grpo_transfer_qr_labels** - Generated labels

### Relationships

```
GRPOTransferSession (1) ──→ (N) GRPOTransferItem
                         ──→ (N) GRPOTransferLog
                         ──→ (N) GRPOTransferQRLabel

GRPOTransferItem (1) ──→ (N) GRPOTransferBatch
                     ──→ (N) GRPOTransferSplit
```

## 🚀 Installation & Migration

### Run Migration

```bash
# Create GRPO Transfer tables only
python migrations/add_grpo_transfer_module.py

# Create all WMS tables (consolidated)
python migrations/mysql_consolidated_migration_v2.py

# Rollback
python migrations/add_grpo_transfer_module.py --rollback
```

### Register Blueprint

Add to `main.py`:
```python
from modules.grpo_transfer.routes import grpo_transfer_bp
app.register_blueprint(grpo_transfer_bp)
```

## 🔐 Security & Permissions

- All endpoints require `@login_required`
- QC approval requires QC role
- Transfer posting requires admin role
- All activities logged with user ID and timestamp

## 📝 Audit Trail

Every action is logged in `grpo_transfer_logs`:
- Session creation
- Item additions
- QC approvals
- Rejections
- SAP B1 transfers
- Errors and warnings

## 🔗 Integration Points

### SAP B1 APIs Used

1. **SQL Queries:**
   - `GET_GRPO_Series` - Get series list
   - `GET_GRPO_DocEntry_By_Series` - Get documents
   - `ItemCode_Batch_Serial_Val` - Validate item type
   - `Get_Batches_By_DocEntry` - Get batch numbers

2. **OData Endpoints:**
   - `PurchaseDeliveryNotes` - Get GRPO details
   - `Warehouses` - Get warehouse list
   - `BinLocations` - Get bin codes
   - `StockTransfers` - Post transfers

## 📈 Future Enhancements

- Serial number tracking for serial items
- Multi-warehouse approval workflows
- Batch expiry date validation
- Automatic rejection rules
- Integration with QC dashboard
- Mobile app support
- Barcode scanning integration

## 🐛 Troubleshooting

### Common Issues

1. **SAP B1 Connection Error**
   - Check SAP B1 service is running
   - Verify API credentials in environment

2. **Batch Numbers Not Found**
   - Ensure item is batch-managed in SAP B1
   - Check GRPO document has batch allocations

3. **Warehouse Not Found**
   - Verify warehouse code in SAP B1
   - Check user has access to warehouse

## 📞 Support

For issues or questions, check:
- Application logs in `/tmp/wms_logs/`
- Database audit trail in `grpo_transfer_logs`
- SAP B1 API responses in logs