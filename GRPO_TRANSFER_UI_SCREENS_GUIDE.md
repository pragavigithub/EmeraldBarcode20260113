# GRPO Transfer Module - UI Screens & Dashboard Integration Guide

## 📱 UI Screens Created

### 1. **Main Dashboard** (`index.html`)
**Route:** `/grpo-transfer/`

**Features:**
- Quick stats (Active Sessions, Approved Items, Rejected Items, Transferred)
- Series selection dropdown
- Document selection dropdown
- Active sessions table with status badges
- Real-time session list loading

**Components:**
- Header with navigation
- Statistics cards
- Series/Document selector
- Active sessions table
- Action buttons

**JavaScript Functions:**
- `loadSeriesList()` - Fetch series from SAP B1
- `loadDocuments(seriesId)` - Fetch documents by series
- `loadActiveSessions()` - Load active sessions
- `getStatusBadge(status)` - Format status badges

---

### 2. **Session Detail Screen** (`session_detail.html`)
**Route:** `/grpo-transfer/session/<session_id>`

**Features:**
- Session information display
- GRPO document details
- Session status tracking
- Tabbed interface for different views
- Line items table
- QC validation form
- Generated QR labels
- Audit log timeline

**Tabs:**
1. **Items Tab** - View all line items with quantities and status
2. **QC Validation Tab** - QC approval form
3. **QR Labels Tab** - Generated QR labels for approved items
4. **Audit Log Tab** - Activity timeline

**Components:**
- Session header with status
- Document details card
- Session status card
- Tabbed content area
- Action buttons (Submit QC, Post Transfer, Print Labels)

**JavaScript Functions:**
- `loadQCItems()` - Load items for QC validation
- `loadLabels()` - Load generated QR labels
- `submitQCApproval()` - Submit QC approval
- `postTransfer()` - Post to SAP B1
- `generateLabels()` - Generate QR labels
- `printLabels()` - Print labels

---

### 3. **QC Validation Screen** (`qc_validation.html`)
**Route:** `/grpo-transfer/session/<session_id>/qc`

**Features:**
- Progress bar showing validation progress
- Item-by-item QC validation form
- Batch information display (for batch items)
- Warehouse and bin selection
- Quantity split management
- QC notes field
- Dynamic form validation

**Components:**
- Progress bar
- QC item cards (one per item)
- Batch information table
- Warehouse/bin selectors
- Quantity split section
- QC notes textarea
- Action buttons

**JavaScript Functions:**
- `loadWarehouses()` - Load warehouse list
- `loadBinCodes(warehouseCode, binSelect)` - Load bin codes
- `setupEventListeners()` - Setup form event listeners
- `addSplit(itemId)` - Add quantity split
- `submitQCApproval()` - Submit QC approval

**Form Features:**
- Auto-calculate rejected quantity
- Show/hide splits section based on status
- Dynamic warehouse/bin loading
- Quantity validation

---

### 4. **Create Session Screen** (`create_session.html`)
**Route:** `/grpo-transfer/session/create/<doc_entry>`

**Features:**
- Document summary display
- Line items preview table
- Session creation form
- Auto-generated session code
- Priority selection
- Description field

**Components:**
- Document details card
- Line items summary card
- Line items table
- Session creation form
- Action buttons

**JavaScript Functions:**
- `createSession()` - Create new transfer session
- Auto-generate session code on page load

---

## 🗺️ Dashboard Integration

### Navigation Menu Addition

Add to `templates/base.html` or dashboard navigation:

```html
<!-- GRPO Transfer Module Link -->
{% if current_user.has_permission('grpo_transfer') or current_user.role in ['admin', 'manager', 'qc'] %}
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('grpo_transfer.index') }}">
        <i data-feather="truck"></i> GRPO Transfer
    </a>
</li>
{% endif %}
```

### Dashboard Card Addition

Add to `templates/dashboard.html`:

```html
<!-- GRPO Transfer Card -->
{% if current_user.has_permission('grpo_transfer') or current_user.role in ['admin', 'manager', 'qc'] %}
<div class="col-md-3 col-sm-6 mb-3">
    <div class="card dashboard-card" data-url="{{ url_for('grpo_transfer.index') }}">
        <div class="card-body text-center">
            <i data-feather="truck" class="mb-3" style="width: 48px; height: 48px;"></i>
            <h3 id="grpoTransferCount">0</h3>
            <p>GRPO Transfers</p>
        </div>
    </div>
</div>
{% endif %}
```

### Dashboard Statistics Script

Add to `templates/dashboard.html` JavaScript:

```javascript
// Load GRPO Transfer stats
fetch('/grpo-transfer/api/sessions')
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            document.getElementById('grpoTransferCount').textContent = data.sessions.length;
        }
    });
```

---

## 🔗 URL Mapping

| Screen | Route | Method | Purpose |
|--------|-------|--------|---------|
| Dashboard | `/grpo-transfer/` | GET | Main dashboard |
| Session Detail | `/grpo-transfer/session/<id>` | GET | View session |
| QC Validation | `/grpo-transfer/session/<id>/qc` | GET | QC approval |
| Create Session | `/grpo-transfer/session/create/<doc_entry>` | GET | Create new session |

---

## 📊 API Endpoints Used by UI

### Dashboard Screen
- `GET /grpo-transfer/api/series-list` - Load series dropdown
- `GET /grpo-transfer/api/doc-numbers/<series_id>` - Load documents
- `GET /grpo-transfer/api/sessions` - Load active sessions

### Session Detail Screen
- `GET /grpo-transfer/api/session/<id>/labels` - Load QR labels
- `POST /grpo-transfer/api/session/<id>/qc-approve` - Submit QC
- `POST /grpo-transfer/api/session/<id>/post-transfer` - Post to SAP
- `POST /grpo-transfer/api/session/<id>/generate-qr-labels` - Generate labels

### QC Validation Screen
- `GET /grpo-transfer/api/warehouses` - Load warehouse list
- `GET /grpo-transfer/api/bin-codes/<warehouse>` - Load bin codes
- `POST /grpo-transfer/api/session/<id>/qc-approve` - Submit QC

### Create Session Screen
- `POST /grpo-transfer/api/create-session` - Create session

---

## 🎨 UI Components & Styling

### Bootstrap Classes Used
- `card` - Card containers
- `table-responsive` - Responsive tables
- `badge` - Status badges
- `btn` - Buttons
- `form-control` - Form inputs
- `nav-tabs` - Tab navigation
- `progress` - Progress bars
- `alert` - Alert messages

### Custom Styles

```css
/* QC Item Cards */
.qc-item-card {
    border-left: 4px solid #007bff;
}

.qc-item-card.approved {
    border-left-color: #28a745;
}

.qc-item-card.rejected {
    border-left-color: #dc3545;
}

.qc-item-card.partial {
    border-left-color: #ffc107;
}

/* Timeline */
.timeline {
    position: relative;
    padding: 20px 0;
}

.timeline-item {
    display: flex;
    margin-bottom: 20px;
}

.timeline-marker {
    width: 20px;
    height: 20px;
    border-radius: 50%;
    margin-right: 20px;
    margin-top: 5px;
    flex-shrink: 0;
}

.timeline-content {
    flex: 1;
}

/* Split Items */
.split-item {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 5px;
    margin-bottom: 10px;
}
```

---

## 🔐 Permission Requirements

### Required Permissions
- `grpo_transfer` - Access to GRPO Transfer module

### Role-Based Access
- **Admin:** Full access to all screens
- **Manager:** Full access to all screens
- **QC:** Access to QC validation and session detail screens
- **User:** Read-only access to dashboard

---

## 📱 Responsive Design

All screens are fully responsive:
- **Desktop:** Full layout with all columns
- **Tablet:** Adjusted column widths
- **Mobile:** Stacked layout with collapsible sections

---

## 🔄 User Workflow

### Complete Workflow Path

```
1. Dashboard (/grpo-transfer/)
   ↓
2. Select Series & Document
   ↓
3. Create Session (/grpo-transfer/session/create/<doc_entry>)
   ↓
4. Session Detail (/grpo-transfer/session/<id>)
   ↓
5. QC Validation (/grpo-transfer/session/<id>/qc)
   ↓
6. Generate QR Labels
   ↓
7. Post to SAP B1
   ↓
8. View Transferred Session
```

---

## 🎯 Key Features by Screen

### Dashboard
- ✅ Quick stats overview
- ✅ Series/document selection
- ✅ Active sessions list
- ✅ One-click session creation

### Session Detail
- ✅ Complete session information
- ✅ Tabbed interface
- ✅ Item management
- ✅ QC approval workflow
- ✅ Label generation
- ✅ Audit trail

### QC Validation
- ✅ Item-by-item validation
- ✅ Batch information display
- ✅ Warehouse/bin selection
- ✅ Quantity splitting
- ✅ Progress tracking
- ✅ Form validation

### Create Session
- ✅ Document preview
- ✅ Line items summary
- ✅ Session code generation
- ✅ Priority selection

---

## 📋 Form Validation

### QC Validation Form
- Approved quantity ≤ Received quantity
- Rejected quantity auto-calculated
- Warehouse selection required
- Bin code selection required
- Status selection required

### Create Session Form
- Auto-generated session code
- Optional description
- Priority selection
- Confirmation before creation

---

## 🔔 Status Indicators

### Session Status Badges
- **Draft** - Gray badge
- **In Progress** - Yellow badge
- **Completed** - Green badge
- **Transferred** - Blue badge

### Item Status Badges
- **Pending** - Yellow badge
- **Approved** - Green badge
- **Rejected** - Red badge
- **Partial** - Blue badge

### Item Type Badges
- **Batch** - Blue badge
- **Serial** - Green badge
- **Non-Managed** - Gray badge

---

## 🚀 Performance Optimization

### Lazy Loading
- Sessions loaded on demand
- Warehouses loaded on selection
- Bin codes loaded on warehouse change

### Caching
- Series list cached in memory
- Warehouse list cached in memory
- Session data cached until refresh

### Pagination
- Sessions table paginated (10 per page)
- Line items table paginated (20 per page)

---

## 🆘 Error Handling

### User-Friendly Error Messages
- "Failed to load series" - SAP B1 connection error
- "Session not found" - Invalid session ID
- "Missing required fields" - Form validation error
- "Error creating session" - Database error

### Error Display
- Alert dialogs for critical errors
- Inline error messages for form validation
- Toast notifications for success messages

---

## 📞 Support & Documentation

For detailed information about:
- **API Endpoints:** See `GRPO_TRANSFER_MODULE_GUIDE.md`
- **Database Models:** See `modules/grpo_transfer/models.py`
- **Routes:** See `modules/grpo_transfer/routes.py`
- **Deployment:** See `QUICK_DEPLOYMENT_GUIDE.md`

---

## ✅ Implementation Checklist

- [x] Dashboard screen created
- [x] Session detail screen created
- [x] QC validation screen created
- [x] Create session screen created
- [x] UI routes added to routes.py
- [x] API endpoints integrated
- [x] Form validation implemented
- [x] Error handling added
- [x] Responsive design implemented
- [x] Status badges created
- [x] Progress tracking added
- [x] Audit log display added

---

*Last Updated: 2026-01-25*  
*Version: 1.0*  
*Status: Complete*