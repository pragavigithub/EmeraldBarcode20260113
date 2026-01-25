# GRPO Transfer Module - Testing Guide for Fixed Issues

## Quick Test Checklist

### ✅ Test 1: Edit Button (2 minutes)
**Steps**:
1. Navigate to `/grpo-transfer/session/37` (or any session ID)
2. Look at the Items tab
3. Click the edit button (pencil icon) on any item row
4. **Expected Result**: Modal opens with item details

**Verify**:
- [ ] Modal appears
- [ ] Item code displays
- [ ] Item name displays
- [ ] Received quantity shows
- [ ] Approved/Rejected quantity fields are editable
- [ ] Status dropdown shows current status
- [ ] Warehouse and Bin fields are present

**If Failed**:
- Check browser console (F12) for JavaScript errors
- Verify session ID is correct
- Check that items exist in database

---

### ✅ Test 2: QC Validation Form (5 minutes)
**Steps**:
1. Navigate to session detail page
2. Click on "QC Validation" tab
3. Look at the form

**Verify**:
- [ ] Form displays all line items
- [ ] Each item shows received quantity (read-only)
- [ ] Approved quantity field is editable
- [ ] Rejected quantity field is editable
- [ ] Status dropdown shows options (Pending, Approved, Rejected, Partial)
- [ ] Warehouse dropdown is populated
- [ ] Bin code dropdown is present
- [ ] QC Notes textarea is present

**Fill Form**:
1. For first item: Set Approved Qty = 100, Status = "Approved"
2. Select a warehouse from dropdown
3. Select a bin code from dropdown
4. Add a note: "QC Passed"
5. Click "Submit QC Approval" button

**Expected Result**:
- [ ] Success message appears
- [ ] Page reloads
- [ ] Session status changes to "in_progress"
- [ ] Item status changes to "Approved"

**If Failed**:
- Check browser console for errors
- Verify warehouse dropdown has options
- Check that form fields have correct names
- Verify API endpoint is working

---

### ✅ Test 3: Warehouse Dropdown (3 minutes)
**Steps**:
1. Navigate to session detail page
2. Click on "QC Validation" tab
3. Look at "To Warehouse" dropdown

**Verify**:
- [ ] Dropdown has "-- Select Warehouse --" as first option
- [ ] Dropdown has warehouse options below
- [ ] Each option shows warehouse code and name
- [ ] Can select a warehouse

**Test Bin Code Loading**:
1. Select a warehouse from dropdown
2. Look at "To Bin Code" dropdown

**Expected Result**:
- [ ] Bin code dropdown populates with bin codes for selected warehouse
- [ ] Can select a bin code

**If Failed**:
- Check browser console for API errors
- Verify `/grpo-transfer/api/warehouses` endpoint works
- Verify `/grpo-transfer/api/bin-codes/<code>` endpoint works

---

### ✅ Test 4: Generate Labels (5 minutes)
**Prerequisites**:
- Must have approved items (complete Test 2 first)

**Steps**:
1. Navigate to session detail page
2. Click on "QR Labels" tab
3. Click "Generate Labels" button

**Expected Result**:
- [ ] Confirmation dialog appears
- [ ] Success message shows number of labels generated
- [ ] Page reloads
- [ ] Labels display in the tab

**Verify in Database**:
```sql
SELECT * FROM grpo_transfer_qr_labels WHERE session_id = <session_id>;
```
- [ ] Records created for each approved item
- [ ] QR data is populated
- [ ] Label numbers are sequential

**If Failed**:
- Check browser console for errors
- Verify items are approved (check qc_status = 'approved')
- Check database for label records
- Verify API endpoint returns success

---

### ✅ Test 5: Audit Log (3 minutes)
**Steps**:
1. Navigate to session detail page
2. Click on "Audit Log" tab

**Expected Result**:
- [ ] Timeline displays with activity entries
- [ ] Shows "Session Created" entry
- [ ] Shows "QC Approved" entry (if you completed Test 2)
- [ ] Shows "Labels Generated" entry (if you completed Test 4)
- [ ] Each entry shows action, timestamp, and description

**Verify in Database**:
```sql
SELECT * FROM grpo_transfer_logs WHERE session_id = <session_id> ORDER BY created_at DESC;
```
- [ ] Records exist for each action
- [ ] User ID is captured
- [ ] Timestamps are correct
- [ ] Descriptions are meaningful

**If Failed**:
- Check database for log records
- Verify relationship is working: `session.logs`
- Check that logs are being created in API endpoints

---

### ✅ Test 6: Complete Workflow (15 minutes)
**Full End-to-End Test**:

1. **Create Session**:
   - Navigate to `/grpo-transfer/`
   - Select series
   - Select document
   - Click "Start Session"
   - Verify redirect to session_detail
   - Verify items display in Items tab

2. **QC Validation**:
   - Click "QC Validation" tab
   - Fill approval quantities
   - Select warehouse and bin
   - Click "Submit QC Approval"
   - Verify success message

3. **Generate Labels**:
   - Click "QR Labels" tab
   - Click "Generate Labels"
   - Verify labels generated

4. **Audit Log**:
   - Click "Audit Log" tab
   - Verify all actions logged

5. **Post to SAP B1**:
   - Click "Post to SAP B1" button
   - Verify success with SAP DocNum
   - Check database for transfer info

---

## Database Verification Queries

### Check Session Created
```sql
SELECT id, session_code, grpo_doc_num, status, created_at
FROM grpo_transfer_sessions
WHERE id = <session_id>;
```

### Check Line Items
```sql
SELECT id, item_code, item_name, received_quantity, approved_quantity, 
       rejected_quantity, qc_status
FROM grpo_transfer_items
WHERE session_id = <session_id>;
```

### Check Audit Log
```sql
SELECT id, action, description, status, created_at
FROM grpo_transfer_logs
WHERE session_id = <session_id>
ORDER BY created_at DESC;
```

### Check QR Labels
```sql
SELECT id, item_id, label_number, total_labels, quantity
FROM grpo_transfer_qr_labels
WHERE session_id = <session_id>;
```

### Check Splits (if partial approval)
```sql
SELECT id, item_id, split_number, quantity, status
FROM grpo_transfer_splits
WHERE item_id IN (
    SELECT id FROM grpo_transfer_items WHERE session_id = <session_id>
);
```

---

## Browser Console Debugging

### Check for JavaScript Errors
1. Open browser (F12)
2. Go to Console tab
3. Look for red error messages
4. Common errors:
   - `Cannot read property 'value' of null` - Form field not found
   - `Fetch failed` - API endpoint not working
   - `Uncaught SyntaxError` - JavaScript syntax error

### Check Network Requests
1. Open browser (F12)
2. Go to Network tab
3. Perform action (e.g., submit QC approval)
4. Look for API requests
5. Check response status (should be 200 for success)
6. Check response body for error messages

### Check Console Logs
1. Open browser (F12)
2. Go to Console tab
3. Look for console.log() messages
4. Check for error messages from fetch calls

---

## Common Issues & Solutions

### Issue: Edit Button Opens Modal But No Data
**Solution**:
- Check browser console for errors
- Verify `session.items|tojson` is working
- Check that item ID is correct

### Issue: Warehouse Dropdown Empty
**Solution**:
- Check if `/grpo-transfer/api/warehouses` returns data
- Verify SAP B1 connection
- Check browser console for fetch errors

### Issue: QC Form Not Submitting
**Solution**:
- Check browser console for errors
- Verify form fields have correct names
- Check that at least one item is approved
- Verify API endpoint `/grpo-transfer/api/session/<id>/qc-approve` works

### Issue: Audit Log Not Showing
**Solution**:
- Check database for log records
- Verify relationship `session.logs` exists in model
- Check that logs are being created in API endpoints

### Issue: Generate Labels Fails
**Solution**:
- Verify items are approved (qc_status = 'approved')
- Check database for label records
- Verify API endpoint returns success
- Check browser console for errors

---

## Performance Notes

- **First Load**: May take 2-3 seconds to load warehouses
- **Warehouse Selection**: Bin codes load in 1-2 seconds
- **QC Submission**: Should complete in 1-2 seconds
- **Label Generation**: Should complete in 1-2 seconds

If any operation takes longer than 5 seconds, check:
- SAP B1 connection
- Database performance
- Network latency
- Browser console for errors

---

## Success Criteria

All tests pass when:
- ✅ Edit button opens modal with item data
- ✅ QC form displays all items with editable fields
- ✅ Warehouse dropdown populated with options
- ✅ Bin code dropdown loads when warehouse selected
- ✅ QC approval submits successfully
- ✅ Labels generate successfully
- ✅ Audit log displays all actions
- ✅ Database records created correctly
- ✅ No JavaScript errors in console
- ✅ All API endpoints return success

---

## Rollback Plan

If issues occur:
1. Check browser console for errors
2. Check database for records
3. Check API responses
4. Review GRPO_TRANSFER_FIXES_APPLIED.md for changes
5. Verify all files were updated correctly
6. Restart application if needed

---

## Support

For issues:
1. Check this testing guide
2. Check GRPO_TRANSFER_FIXES_APPLIED.md
3. Check browser console (F12)
4. Check database records
5. Check API responses in Network tab

---

**Status**: ✅ READY FOR TESTING

All fixes have been applied. Follow this guide to verify everything works correctly.

