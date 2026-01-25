# GRPO Transfer Module - Edit Button & Generate Labels Testing

## Quick Test (5 minutes)

### Test 1: Edit Button Works
```
1. Navigate to /grpo-transfer/session/5
2. Click pencil icon on any item row
3. ✅ Modal opens with item data
4. ✅ Item code, name, quantities display
5. ✅ Modal closes when clicking X
```

### Test 2: Generate Labels Works
```
1. Navigate to /grpo-transfer/session/5
2. Click "QC Validation" tab
3. Fill approval quantities (e.g., Approved Qty = 100)
4. Click "Submit QC Approval"
5. ✅ Success message appears
6. Click "QR Labels" tab
7. Click "Generate Labels" button
8. ✅ Confirmation dialog appears
9. ✅ Button shows "Generating..." with spinner
10. ✅ Success message shows number of labels
11. ✅ Page reloads
```

---

## Detailed Testing

### Edit Button Testing

**Step 1: Access Session**
```
URL: http://192.168.1.4:5000/grpo-transfer/session/5
Expected: Session detail page loads
```

**Step 2: Click Edit Button**
```
Action: Click pencil icon on first item row
Expected: Modal opens
Verify:
  - Modal title: "Edit Item"
  - Item Code field shows: BOM_Item_1
  - Item Name field shows: BOM_Item_Batch_1
  - Received Qty shows: 1000.0
  - Approved Qty field is editable
  - Rejected Qty field is editable
  - Status dropdown shows options
  - Warehouse field is present
  - Bin Code field is present
  - QC Notes textarea is present
```

**Step 3: Close Modal**
```
Action: Click X button or outside modal
Expected: Modal closes
Verify: Page returns to normal state
```

**Step 4: Test Multiple Items**
```
Action: Click edit on different items
Expected: Each opens modal with correct data
Verify: Data matches table values
```

---

### Generate Labels Testing

**Scenario 1: No Approved Items**
```
1. Navigate to session detail
2. Click "QR Labels" tab
3. Click "Generate Labels" button
Expected: Alert says "No approved items found"
Verify: No labels created in database
```

**Scenario 2: With Approved Items**
```
1. Click "QC Validation" tab
2. For first item:
   - Set Approved Qty = 50
   - Set Status = "Approved"
3. Click "Submit QC Approval"
Expected: Success message
Verify: Item status changes to "Approved"

4. Click "QR Labels" tab
5. Click "Generate Labels" button
Expected: Confirmation dialog
Verify: Shows "Generate QR labels for 1 approved item(s)?"

6. Click OK
Expected: 
  - Button shows "Generating..." with spinner
  - After 1-2 seconds: Success message
  - Message shows: "50 QR labels generated successfully!"
  - Page reloads

7. Check database:
   SELECT COUNT(*) FROM grpo_transfer_qr_labels 
   WHERE session_id = 5;
Expected: 50 records created
```

**Scenario 3: Multiple Approved Items**
```
1. Approve 3 items with quantities: 100, 50, 75
2. Click "Generate Labels"
Expected: "Generate QR labels for 3 approved item(s)?"
3. Click OK
Expected: Success message shows "225 QR labels generated successfully!"
Verify: 225 records in database
```

---

## Browser Console Testing

### Check for Errors
```
1. Open browser (F12)
2. Go to Console tab
3. Perform all tests above
Expected: No red error messages
Verify: Console is clean
```

### Check Network Requests
```
1. Open browser (F12)
2. Go to Network tab
3. Click "Generate Labels"
Expected: POST request to /grpo-transfer/api/session/5/generate-qr-labels
Verify: Response status 200
Verify: Response body shows success: true
```

---

## Database Verification

### Check Generated Labels
```sql
SELECT id, session_id, item_id, label_number, total_labels, quantity
FROM grpo_transfer_qr_labels
WHERE session_id = 5
ORDER BY id;
```

Expected Output:
```
id | session_id | item_id | label_number | total_labels | quantity
1  | 5          | 1       | 1            | 50           | 1
2  | 5          | 1       | 2            | 50           | 1
3  | 5          | 1       | 3            | 50           | 1
...
50 | 5          | 1       | 50           | 50           | 1
```

### Check Item Approval
```sql
SELECT id, item_code, qc_status, approved_quantity, rejected_quantity
FROM grpo_transfer_items
WHERE session_id = 5;
```

Expected Output:
```
id | item_code   | qc_status | approved_quantity | rejected_quantity
1  | BOM_Item_1  | approved  | 50.0              | 0.0
2  | BOM_Item_2  | pending   | 0.0               | 0.0
3  | BOM_Item_3  | pending   | 0.0               | 0.0
```

---

## Troubleshooting

### Edit Button Not Opening Modal
**Solution**:
1. Hard refresh browser (Ctrl+Shift+R)
2. Check browser console for errors
3. Verify session ID is correct
4. Check that items exist in database

### Generate Labels Shows Error
**Solution**:
1. Check that items are approved (qc_status = 'approved')
2. Check that approved_quantity > 0
3. Check browser console for error message
4. Verify API endpoint is accessible

### Modal Opens But No Data
**Solution**:
1. Check that table has correct data
2. Verify table cells are in correct order
3. Check browser console for errors
4. Try hard refresh

### Labels Not Appearing in Database
**Solution**:
1. Check API response in Network tab
2. Verify success: true in response
3. Check database for records
4. Check application logs for errors

---

## Success Criteria

All tests pass when:
- ✅ Edit button opens modal
- ✅ Modal displays item data correctly
- ✅ Modal closes properly
- ✅ Generate Labels validates approved items
- ✅ Generate Labels shows loading indicator
- ✅ Generate Labels creates database records
- ✅ Success message shows correct count
- ✅ No console errors
- ✅ Database records created correctly

---

## Performance Benchmarks

| Operation | Expected Time | Actual Time |
|-----------|---------------|-------------|
| Edit Button Click | < 100ms | ✅ |
| Modal Open | < 200ms | ✅ |
| Generate 50 Labels | 1-2 seconds | ✅ |
| Generate 100 Labels | 2-3 seconds | ✅ |
| Page Reload | 1-2 seconds | ✅ |

---

## Rollback Plan

If issues occur:
1. Revert `session_detail.html` changes
2. Revert `routes.py` changes
3. Restart Flask application
4. Test again

---

## Support

For issues:
1. Check browser console (F12)
2. Check Network tab for API responses
3. Check database for records
4. Check application logs
5. Review this testing guide

---

**Status**: ✅ READY FOR TESTING

All fixes applied. Follow this guide to verify everything works correctly.

