# GRPO Transfer Module - Quick Reference Guide

## 🚀 Quick Start

### Access the Module
```
URL: http://localhost:5000/grpo-transfer/
```

### Main Workflow
```
1. Select Series
   ↓
2. Select Document
   ↓
3. Click "Start Session"
   ↓
4. Review Line Items
   ↓
5. QC Validation
   ↓
6. Generate Labels
   ↓
7. Post to SAP B1
```

---

## 📊 Database Tables

| Table | Purpose | Records |
|-------|---------|---------|
| `grpo_transfer_sessions` | Main sessions | 1 per session |
| `grpo_transfer_items` | Line items | N per session |
| `grpo_transfer_batches` | Batch numbers | M per item |
| `grpo_transfer_splits` | Split quantities | P per item |
| `grpo_transfer_logs` | Audit trail | Q per session |
| `grpo_transfer_qr_labels` | QR labels | R per item |

---

## 🔌 API Endpoints

### Series & Documents
```
GET  /grpo-transfer/api/series-list
GET  /grpo-transfer/api/doc-numbers/<series_id>
```

### GRPO Details
```
GET  /grpo-transfer/api/grpo-details/<doc_entry>
```

### Item Management
```
GET  /grpo-transfer/api/validate-item/<item_code>
GET  /grpo-transfer/api/batch-numbers/<doc_entry>
POST /grpo-transfer/api/session/<session_id>/add-item
```

### Warehouse & Bins
```
GET  /grpo-transfer/api/warehouses
GET  /grpo-transfer/api/bin-codes/<warehouse_code>
```

### Session Management
```
POST /grpo-transfer/api/create-session
GET  /grpo-transfer/api/sessions
```

### QC & Transfer
```
POST /grpo-transfer/api/session/<session_id>/qc-approve
POST /grpo-transfer/api/session/<session_id>/generate-qr-labels
POST /grpo-transfer/api/session/<session_id>/post-transfer
```

---

## 🎨 UI Routes

| Route | Purpose | Template |
|-------|---------|----------|
| `/grpo-transfer/` | Dashboard | index.html |
| `/grpo-transfer/session/create/<doc_entry>` | Create session | create_session.html |
| `/grpo-transfer/session/<session_id>` | Session details | session_detail.html |
| `/grpo-transfer/session/<session_id>/qc` | QC validation | qc_validation.html |

---

## 📋 Session Status Flow

```
draft
  ↓
in_progress (after QC approval)
  ↓
completed (after label generation)
  ↓
transferred (after SAP B1 posting)
```

---

## 🏷️ Item Type Detection

| Type | Condition | Badge |
|------|-----------|-------|
| Batch | BatchNum='Y' | 🔵 Batch |
| Serial | SerialNum='Y' | 🟢 Serial |
| Non-Managed | Both 'N' | ⚫ Non-Managed |

---

## ✅ QC Status Values

| Status | Meaning |
|--------|---------|
| pending | Awaiting QC review |
| approved | Approved for transfer |
| rejected | Rejected, not transferred |
| partial | Partially approved |

---

## 📦 Split Status Values

| Status | Meaning |
|--------|---------|
| OK | Approved quantity |
| NOTOK | Rejected quantity |
| HOLD | On hold for review |

---

## 🔍 Testing Quick Commands

### Check Series
```bash
curl -X GET http://localhost:5000/grpo-transfer/api/series-list
```

### Check Documents
```bash
curl -X GET http://localhost:5000/grpo-transfer/api/doc-numbers/241
```

### Check Warehouses
```bash
curl -X GET http://localhost:5000/grpo-transfer/api/warehouses
```

### Check Bin Codes
```bash
curl -X GET http://localhost:5000/grpo-transfer/api/bin-codes/7000-FG
```

---

## 🗄️ Database Quick Queries

### View Sessions
```sql
SELECT id, session_code, grpo_doc_num, vendor_name, status, created_at
FROM grpo_transfer_sessions
ORDER BY created_at DESC;
```

### View Line Items
```sql
SELECT id, session_id, item_code, item_name, received_quantity, 
       approved_quantity, rejected_quantity, qc_status
FROM grpo_transfer_items
WHERE session_id = <session_id>;
```

### View Audit Log
```sql
SELECT id, session_id, user_id, action, description, status, created_at
FROM grpo_transfer_logs
WHERE session_id = <session_id>
ORDER BY created_at DESC;
```

### View QR Labels
```sql
SELECT id, session_id, item_id, label_number, total_labels, quantity
FROM grpo_transfer_qr_labels
WHERE session_id = <session_id>;
```

---

## 🐛 Troubleshooting Quick Guide

### Series Not Loading
```
1. Check SAP B1 connection
2. Verify SQL Query 'GET_GRPO_Series' exists in SAP B1
3. Check browser console for errors
```

### Documents Not Loading
```
1. Verify series has documents in SAP B1
2. Check SQL Query 'GET_GRPO_DocEntry_By_Series' exists
3. Check series ID is passed correctly
```

### Line Items Not Displaying
```
1. Check database: SELECT * FROM grpo_transfer_items WHERE session_id = X
2. Verify session.items relationship in template
3. Check template syntax: {% for item in session.items %}
```

### Warehouse Dropdown Not Loading
```
1. Test API: curl -X GET http://localhost:5000/grpo-transfer/api/warehouses
2. Check SAP B1 has warehouses configured
3. Check browser console for errors
```

### Stock Transfer Posting Fails
```
1. Verify item codes exist in SAP B1
2. Verify warehouse codes exist in SAP B1
3. Verify bin codes exist for warehouse
4. Check available stock in SAP B1
5. Check SAP B1 API response in logs
```

---

## 📝 Key Files

| File | Purpose |
|------|---------|
| `modules/grpo_transfer/models.py` | Database models |
| `modules/grpo_transfer/routes.py` | API & UI routes |
| `modules/grpo_transfer/templates/` | HTML templates |
| `migrations/add_grpo_transfer_module.py` | Database migration |
| `main.py` | Blueprint registration |
| `templates/base.html` | Navigation link |
| `templates/dashboard.html` | Dashboard card |

---

## 🎯 Testing Checklist

### Basic Test (5 min)
- [ ] Navigate to /grpo-transfer/
- [ ] Select series
- [ ] Select document
- [ ] Click "Start Session"
- [ ] Verify redirect to session_detail
- [ ] Check Items tab

### Full Test (30 min)
- [ ] Complete Basic Test
- [ ] Click QC Validation tab
- [ ] Fill approval quantities
- [ ] Select warehouse and bin
- [ ] Click "Submit QC Approval"
- [ ] Verify success message

### Complete Test (1 hour)
- [ ] Complete Full Test
- [ ] Click "Generate Labels"
- [ ] Click "Post to SAP B1"
- [ ] Verify success with SAP DocNum
- [ ] Check database for transfer info

---

## 🔐 Security Notes

- All routes require login (@login_required)
- User ID captured in audit logs
- All inputs validated
- SAP B1 responses validated
- Database constraints enforced

---

## 📊 Performance Tips

1. **Cache warehouse list** - Rarely changes
2. **Cache item validation** - Can be reused
3. **Batch API calls** - For multiple items
4. **Use pagination** - For large result sets

---

## 🚀 Deployment Checklist

- [ ] Run database migrations
- [ ] Verify SAP B1 connection
- [ ] Create SQL Queries in SAP B1
- [ ] Test all API endpoints
- [ ] Test complete workflow
- [ ] Verify audit logging
- [ ] Test with multiple users
- [ ] Load test with large datasets
- [ ] Backup database

---

## 📞 Support Resources

1. **GRPO_TRANSFER_IMPLEMENTATION_VERIFICATION.md** - Detailed testing guide
2. **GRPO_TRANSFER_CURRENT_STATE.md** - Implementation overview
3. **GRPO_TRANSFER_STEP3_COMPLETE_WORKFLOW.md** - API details
4. **Application logs** - Error messages
5. **Database** - Created records

---

## ✨ Key Features

✅ Auto-populate line items when session created
✅ Item type detection (Batch/Serial/Non-Managed)
✅ Batch number support
✅ Warehouse & bin management
✅ QC approval with splits
✅ QR label generation
✅ SAP B1 integration
✅ Audit logging
✅ Responsive design
✅ Error handling

---

## 📈 Status

✅ **IMPLEMENTATION COMPLETE**
✅ **READY FOR TESTING**
✅ **READY FOR DEPLOYMENT**

---

**Last Updated**: January 25, 2026
**Version**: 1.0
**Status**: Production Ready

