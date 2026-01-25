# GRPO Transfer Module - API Debugging Guide

## Issue: Series Dropdown Not Loading

### Root Cause
The original API endpoints were trying to call custom SQL Queries in SAP B1 that don't exist:
- `GET_GRPO_Series` - Not configured
- `GET_GRPO_DocEntry_By_Series` - Not configured
- `ItemCode_Batch_Serial_Val` - Not configured
- `Get_Batches_By_DocEntry` - Not configured

### Solution
Updated all API endpoints to use standard SAP B1 OData endpoints instead of custom SQL queries.

---

## Fixed API Endpoints

### 1. Get Series List
**Endpoint:** `GET /grpo-transfer/api/series-list`

**What Changed:**
- ❌ OLD: `SQLQueries('GET_GRPO_Series')/List`
- ✅ NEW: `DocumentsService_DocumentSeries?$filter=DocType eq 1250000001`

**Response:**
```json
{
  "success": true,
  "series": [
    {
      "SeriesID": 1,
      "SeriesName": "GRPO-2024",
      "NextNumber": 100
    }
  ]
}
```

**Testing:**
```bash
curl -X GET "http://localhost:5000/grpo-transfer/api/series-list" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2. Get Documents by Series
**Endpoint:** `GET /grpo-transfer/api/doc-numbers/<series_id>`

**What Changed:**
- ❌ OLD: `SQLQueries('GET_GRPO_DocEntry_By_Series')/List` with ParamList
- ✅ NEW: `PurchaseDeliveryNotes?$filter=Series eq {series_id}`

**Response:**
```json
{
  "success": true,
  "documents": [
    {
      "DocEntry": 1001,
      "DocNum": "100",
      "CardCode": "C001",
      "CardName": "Vendor Name",
      "DocDate": "2024-01-15",
      "DocStatus": "O",
      "DocumentStatus": "O"
    }
  ]
}
```

**Testing:**
```bash
curl -X GET "http://localhost:5000/grpo-transfer/api/doc-numbers/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 3. Validate Item
**Endpoint:** `GET /grpo-transfer/api/validate-item/<item_code>`

**What Changed:**
- ❌ OLD: `SQLQueries('ItemCode_Batch_Serial_Val')/List` with ParamList
- ✅ NEW: `Items?$filter=ItemCode eq '{item_code}'`

**Response:**
```json
{
  "success": true,
  "item_code": "ITEM001",
  "item_name": "Product Name",
  "is_batch_item": true,
  "is_serial_item": false,
  "is_non_managed": false
}
```

**Testing:**
```bash
curl -X GET "http://localhost:5000/grpo-transfer/api/validate-item/ITEM001" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 4. Get Batch Numbers
**Endpoint:** `GET /grpo-transfer/api/batch-numbers/<doc_entry>`

**What Changed:**
- ❌ OLD: `SQLQueries('Get_Batches_By_DocEntry')/List` with ParamList
- ✅ NEW: `PurchaseDeliveryNotes({doc_entry})/DocumentLines?$expand=BatchNumbers`

**Response:**
```json
{
  "success": true,
  "batches": [
    {
      "LineNum": 1,
      "ItemCode": "ITEM001",
      "BatchNumber": "BATCH-2024-001",
      "Quantity": 100
    }
  ]
}
```

**Testing:**
```bash
curl -X GET "http://localhost:5000/grpo-transfer/api/batch-numbers/1001" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Browser Console Debugging

### Step 1: Open Developer Tools
Press `F12` in your browser and go to the **Console** tab.

### Step 2: Check Network Requests
1. Go to **Network** tab
2. Reload the page
3. Look for requests to `/grpo-transfer/api/series-list`
4. Check the response status and body

### Step 3: Common Errors

**Error: "Failed to fetch series from SAP B1"**
- Check if SAP B1 connection is active
- Verify SAP B1 credentials in `.env`
- Check SAP B1 OData service is running

**Error: "No GRPO series configured in SAP B1"**
- Create at least one GRPO series in SAP B1
- Verify the series is for Purchase Delivery Notes (GRPO)

**Error: "Item not found in SAP B1"**
- Verify the item code exists in SAP B1
- Check item code spelling and case sensitivity

---

## Manual Testing Steps

### Test 1: Series Loading
1. Navigate to `/grpo-transfer/`
2. Open browser console (F12)
3. Click on "Select Series" dropdown
4. Check console for any errors
5. Verify series list appears

**Expected Result:** Dropdown shows list of GRPO series

### Test 2: Document Loading
1. Select a series from dropdown
2. Check console for API call to `/grpo-transfer/api/doc-numbers/<series_id>`
3. Verify "Select Document" dropdown is enabled
4. Click on "Select Document" dropdown

**Expected Result:** Dropdown shows documents for selected series

### Test 3: Session Creation
1. Select a series and document
2. Click "Start Session" button
3. Verify page navigates to create session screen
4. Check console for any errors

**Expected Result:** Session creation form loads with document details

---

## API Response Validation

### Check Response Format
All API endpoints should return JSON with this structure:
```json
{
  "success": true/false,
  "data": {...},
  "error": "error message if success is false"
}
```

### Verify Data Types
- `SeriesID`: Integer
- `DocEntry`: Integer
- `Quantity`: Float
- `DocDate`: ISO 8601 date string

---

## SAP B1 OData Endpoints Used

| Endpoint | Purpose | Document Type |
|----------|---------|----------------|
| `DocumentsService_DocumentSeries` | Get series list | 1250000001 (GRPO) |
| `PurchaseDeliveryNotes` | Get GRPO documents | Purchase Delivery Note |
| `Items` | Get item details | Master data |
| `Warehouses` | Get warehouse list | Master data |
| `BinLocations` | Get bin codes | Master data |

---

## Troubleshooting Checklist

- [ ] SAP B1 connection is active
- [ ] SAP B1 OData service is running
- [ ] User has permission to access GRPO documents
- [ ] At least one GRPO series exists in SAP B1
- [ ] At least one GRPO document exists
- [ ] Browser console shows no JavaScript errors
- [ ] Network tab shows successful API responses (200 status)
- [ ] API responses contain expected data fields

---

## Performance Optimization

### Caching Series List
The series list rarely changes. Consider caching it:

```python
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@grpo_transfer_bp.route('/api/series-list', methods=['GET'])
@cache.cached(timeout=3600)  # Cache for 1 hour
def get_series_list():
    # ... existing code
```

### Pagination for Large Document Lists
If you have many documents, add pagination:

```python
@grpo_transfer_bp.route('/api/doc-numbers/<int:series_id>', methods=['GET'])
def get_doc_numbers(series_id):
    page = request.args.get('page', 1, type=int)
    page_size = request.args.get('page_size', 50, type=int)
    skip = (page - 1) * page_size
    
    response = sap.call_sap_api(
        method='GET',
        endpoint=f"PurchaseDeliveryNotes?$filter=Series eq {series_id}&$skip={skip}&$top={page_size}",
        headers={'Prefer': 'odata.maxpagesize=0'}
    )
```

---

## Files Modified

- `modules/grpo_transfer/routes.py` - Updated 4 API endpoints to use OData
- `modules/grpo_transfer/templates/grpo_transfer/index.html` - Frontend already correct

## Status
✅ **FIXED** - All API endpoints now use standard SAP B1 OData endpoints
