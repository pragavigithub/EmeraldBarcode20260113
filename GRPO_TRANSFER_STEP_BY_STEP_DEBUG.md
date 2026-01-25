# GRPO Transfer Module - Step-by-Step Debugging Guide

## Quick Start: Test the Series Dropdown

### Step 1: Navigate to GRPO Transfer Page
1. Open your WMS application
2. Go to **Inventory → GRPO Transfer** (or navigate to `http://localhost:5000/grpo-transfer/`)
3. You should see the GRPO Transfer Module dashboard

### Step 2: Open Browser Developer Tools
1. Press `F12` on your keyboard
2. Go to the **Console** tab
3. You should see the page loaded without errors

### Step 3: Check the Series Dropdown
1. Look at the "Select Series" dropdown
2. Click on it to see if options appear
3. If no options appear, continue to Step 4

---

## Debugging: Series Dropdown Not Loading

### Step 4: Check Network Requests
1. In Developer Tools, go to **Network** tab
2. Reload the page (F5)
3. Look for a request to `/grpo-transfer/api/series-list`
4. Click on it to see the response

**Expected Response:**
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

**If you see an error response:**
- Note the error message
- Go to Step 5

### Step 5: Check Console for JavaScript Errors
1. In Developer Tools, go to **Console** tab
2. Look for any red error messages
3. Common errors:
   - `Uncaught TypeError: Cannot read property 'value' of undefined`
   - `Failed to fetch`
   - `401 Unauthorized`

**If you see "Failed to fetch":**
- SAP B1 connection is failing
- Go to Step 6

**If you see "401 Unauthorized":**
- User is not logged in
- Log in and try again

### Step 6: Test API Directly in Console
Copy and paste this into the browser console:

```javascript
fetch('/grpo-transfer/api/series-list')
    .then(response => {
        console.log('Status:', response.status);
        return response.json();
    })
    .then(data => {
        console.log('Response:', data);
        if (data.success) {
            console.log('Series count:', data.series.length);
            data.series.forEach(s => {
                console.log(`  - ${s.SeriesName} (ID: ${s.SeriesID})`);
            });
        } else {
            console.error('Error:', data.error);
        }
    })
    .catch(error => console.error('Fetch error:', error));
```

**Expected Console Output:**
```
Status: 200
Response: {success: true, series: Array(1)}
Series count: 1
  - GRPO-2024 (ID: 1)
```

### Step 7: Check SAP B1 Connection
If the API is returning an error, SAP B1 connection might be failing.

**Test SAP B1 Connection:**
1. Open a terminal/command prompt
2. Run: `python test_grpo_transfer_api.py`
3. Check the output for connection errors

**If SAP B1 is not responding:**
1. Verify SAP B1 is running
2. Check SAP B1 credentials in `.env` file
3. Verify network connectivity to SAP B1 server

### Step 8: Check if GRPO Series Exist in SAP B1
If the API returns `"series": []` (empty list):

1. Open SAP B1
2. Go to **Administration → Setup → Document Settings → Document Series**
3. Look for series with document type "Purchase Delivery Note" or "GRPO"
4. If none exist, create one:
   - Click "New"
   - Select "Purchase Delivery Note" as document type
   - Enter series name (e.g., "GRPO-2024")
   - Set starting number
   - Save

---

## Advanced Debugging

### Check API Response Details
In browser console, run:

```javascript
// Test series list
fetch('/grpo-transfer/api/series-list')
    .then(r => r.json())
    .then(d => {
        console.table(d.series);
    });

// Test documents for series 1
fetch('/grpo-transfer/api/doc-numbers/1')
    .then(r => r.json())
    .then(d => {
        console.table(d.documents);
    });

// Test warehouses
fetch('/grpo-transfer/api/warehouses')
    .then(r => r.json())
    .then(d => {
        console.table(d.warehouses);
    });
```

### Check Server Logs
If you're running the app locally:

1. Look at the terminal where Flask is running
2. Check for error messages
3. Look for lines starting with `ERROR` or `Exception`

**Example error log:**
```
ERROR:modules.grpo_transfer.routes:Error fetching series list: Connection refused
```

### Enable Debug Mode
Add this to your `.env` file:
```
FLASK_DEBUG=True
FLASK_ENV=development
```

Then restart the Flask app to see more detailed error messages.

---

## Common Issues and Solutions

### Issue 1: "No GRPO series configured in SAP B1"
**Symptom:** Dropdown shows "-- Select Series --" but no options

**Solution:**
1. Create a GRPO series in SAP B1 (see Step 8 above)
2. Refresh the WMS page
3. Try again

### Issue 2: "Failed to fetch series from SAP B1"
**Symptom:** Console shows error message

**Solution:**
1. Check SAP B1 is running
2. Verify SAP B1 credentials in `.env`
3. Check network connectivity
4. Run `python test_grpo_transfer_api.py` to diagnose

### Issue 3: "401 Unauthorized"
**Symptom:** API returns 401 status

**Solution:**
1. Log out and log back in
2. Check user permissions
3. Verify user has `grpo_transfer` permission

### Issue 4: Dropdown loads but documents don't
**Symptom:** Series dropdown works, but document dropdown is empty

**Solution:**
1. Check if documents exist in SAP B1 for selected series
2. Run in console: `fetch('/grpo-transfer/api/doc-numbers/1').then(r => r.json()).then(d => console.log(d))`
3. Check if documents are returned

### Issue 5: "Cannot read property 'value' of undefined"
**Symptom:** JavaScript error in console

**Solution:**
1. This means SAP B1 API response format is unexpected
2. Check SAP B1 OData service is working
3. Run `python test_grpo_transfer_api.py` to see actual response format

---

## Testing Workflow

### Complete Test Sequence
1. ✅ Series dropdown loads
2. ✅ Select a series
3. ✅ Document dropdown loads
4. ✅ Select a document
5. ✅ Start Session button is enabled
6. ✅ Click Start Session
7. ✅ Create session page loads
8. ✅ Document details are displayed
9. ✅ Can add items to session
10. ✅ Can approve items in QC
11. ✅ Can generate QR labels
12. ✅ Can post to SAP B1

---

## Performance Monitoring

### Check API Response Time
In browser console:

```javascript
console.time('series-list');
fetch('/grpo-transfer/api/series-list')
    .then(r => r.json())
    .then(d => {
        console.timeEnd('series-list');
        console.log('Series:', d.series.length);
    });
```

**Expected:** < 1 second for series list

### Monitor Network Traffic
1. Go to Network tab in Developer Tools
2. Filter by XHR (XMLHttpRequest)
3. Watch for API calls
4. Check response times and sizes

---

## Getting Help

### Information to Provide When Reporting Issues

1. **Browser Console Output**
   - Screenshot or copy of console errors
   - Network tab response for failed API call

2. **Server Logs**
   - Error messages from Flask terminal
   - Full stack trace if available

3. **Test Script Output**
   - Run: `python test_grpo_transfer_api.py`
   - Copy the output

4. **SAP B1 Configuration**
   - Screenshot of Document Series in SAP B1
   - Confirm GRPO series exists
   - Confirm GRPO documents exist

5. **Environment Details**
   - OS (Windows/Linux/Mac)
   - Python version
   - Flask version
   - SAP B1 version

---

## Quick Reference

### API Endpoints
- `GET /grpo-transfer/api/series-list` - Get series
- `GET /grpo-transfer/api/doc-numbers/<series_id>` - Get documents
- `GET /grpo-transfer/api/validate-item/<item_code>` - Validate item
- `GET /grpo-transfer/api/batch-numbers/<doc_entry>` - Get batches
- `GET /grpo-transfer/api/warehouses` - Get warehouses
- `GET /grpo-transfer/api/bin-codes/<warehouse_code>` - Get bins

### Test Commands
```bash
# Test all APIs
python test_grpo_transfer_api.py

# Test specific endpoint
curl http://localhost:5000/grpo-transfer/api/series-list

# Check Flask logs
tail -f app.log
```

### Browser Console Commands
```javascript
// Test series
fetch('/grpo-transfer/api/series-list').then(r => r.json()).then(d => console.log(d))

// Test documents
fetch('/grpo-transfer/api/doc-numbers/1').then(r => r.json()).then(d => console.log(d))

// Test warehouses
fetch('/grpo-transfer/api/warehouses').then(r => r.json()).then(d => console.log(d))
```

---

## Status
✅ **READY FOR TESTING** - All API endpoints are fixed and ready to use
