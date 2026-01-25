"""
GRPO Transfer Module Models
Handles QC validation, item splitting, and warehouse transfers
"""

from app import db
from datetime import datetime
import json

class GRPOTransferSession(db.Model):
    """QC validation session for GRPO documents"""
    __tablename__ = 'grpo_transfer_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    session_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    grpo_doc_entry = db.Column(db.Integer, nullable=False)
    grpo_doc_num = db.Column(db.String(50), nullable=False)
    series_id = db.Column(db.Integer, nullable=False)
    vendor_code = db.Column(db.String(50), nullable=False)
    vendor_name = db.Column(db.String(255), nullable=False)
    doc_date = db.Column(db.Date, nullable=False)
    doc_due_date = db.Column(db.Date, nullable=True)
    doc_total = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='draft')  # draft, in_progress, completed, transferred
    qc_approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    transfer_doc_entry = db.Column(db.Integer, nullable=True)  # SAP B1 StockTransfer DocEntry
    transfer_doc_num = db.Column(db.String(50), nullable=True)  # SAP B1 StockTransfer DocNum
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('GRPOTransferItem', backref='session', lazy=True, cascade='all, delete-orphan')
    logs = db.relationship('GRPOTransferLog', backref='session', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<GRPOTransferSession {self.session_code}>'

class GRPOTransferItem(db.Model):
    """Individual items in GRPO transfer session"""
    __tablename__ = 'grpo_transfer_items'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('grpo_transfer_sessions.id'), nullable=False)
    line_num = db.Column(db.Integer, nullable=False)
    item_code = db.Column(db.String(50), nullable=False)
    item_name = db.Column(db.String(255), nullable=False)
    item_description = db.Column(db.String(500), nullable=True)
    
    # Item type validation
    is_batch_item = db.Column(db.Boolean, default=False)
    is_serial_item = db.Column(db.Boolean, default=False)
    is_non_managed = db.Column(db.Boolean, default=False)
    
    # Quantities
    received_quantity = db.Column(db.Float, nullable=False)
    approved_quantity = db.Column(db.Float, default=0.0)
    rejected_quantity = db.Column(db.Float, default=0.0)
    
    # Warehouse and Bin information
    from_warehouse = db.Column(db.String(50), nullable=False)
    from_bin_code = db.Column(db.String(100), nullable=True)
    to_warehouse = db.Column(db.String(50), nullable=True)
    to_bin_code = db.Column(db.String(100), nullable=True)
    
    # Unit of measure
    unit_of_measure = db.Column(db.String(20), default='1')
    price = db.Column(db.Float, default=0.0)
    line_total = db.Column(db.Float, default=0.0)
    
    # Status
    qc_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, partial
    qc_notes = db.Column(db.Text, nullable=True)
    
    # SAP B1 Reference
    sap_base_entry = db.Column(db.Integer, nullable=True)
    sap_base_line = db.Column(db.Integer, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    batches = db.relationship('GRPOTransferBatch', backref='item', lazy=True, cascade='all, delete-orphan')
    splits = db.relationship('GRPOTransferSplit', backref='item', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<GRPOTransferItem {self.item_code}>'

class GRPOTransferBatch(db.Model):
    """Batch numbers for batch-managed items"""
    __tablename__ = 'grpo_transfer_batches'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('grpo_transfer_items.id'), nullable=False)
    batch_number = db.Column(db.String(100), nullable=False)
    batch_quantity = db.Column(db.Float, nullable=False)
    approved_quantity = db.Column(db.Float, default=0.0)
    rejected_quantity = db.Column(db.Float, default=0.0)
    expiry_date = db.Column(db.Date, nullable=True)
    manufacture_date = db.Column(db.Date, nullable=True)
    qc_status = db.Column(db.String(20), default='pending')  # pending, approved, rejected, partial
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<GRPOTransferBatch {self.batch_number}>'

class GRPOTransferSplit(db.Model):
    """Split quantities for items (when QC approves partial quantity)"""
    __tablename__ = 'grpo_transfer_splits'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('grpo_transfer_items.id'), nullable=False)
    split_number = db.Column(db.Integer, nullable=False)  # 1, 2, 3, etc.
    quantity = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), nullable=False)  # 'OK', 'NOTOK', 'HOLD'
    from_warehouse = db.Column(db.String(50), nullable=False)
    from_bin_code = db.Column(db.String(100), nullable=True)
    to_warehouse = db.Column(db.String(50), nullable=False)
    to_bin_code = db.Column(db.String(100), nullable=True)
    batch_number = db.Column(db.String(100), nullable=True)  # For batch items
    notes = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<GRPOTransferSplit {self.split_number}>'

class GRPOTransferLog(db.Model):
    """Audit log for GRPO transfer activities"""
    __tablename__ = 'grpo_transfer_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('grpo_transfer_sessions.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)  # 'created', 'item_added', 'qc_approved', 'transferred', etc.
    description = db.Column(db.Text, nullable=True)
    sap_response = db.Column(db.Text, nullable=True)  # Store SAP B1 API response
    status = db.Column(db.String(20), default='success')  # success, error, warning
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<GRPOTransferLog {self.action}>'

class GRPOTransferQRLabel(db.Model):
    """QR labels generated for approved items"""
    __tablename__ = 'grpo_transfer_qr_labels'
    
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('grpo_transfer_sessions.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('grpo_transfer_items.id'), nullable=False)
    label_number = db.Column(db.Integer, nullable=False)  # 1 of N
    total_labels = db.Column(db.Integer, nullable=False)  # N
    qr_data = db.Column(db.Text, nullable=False)  # JSON encoded QR data
    batch_number = db.Column(db.String(100), nullable=True)
    quantity = db.Column(db.Float, nullable=False)
    from_warehouse = db.Column(db.String(50), nullable=False)
    to_warehouse = db.Column(db.String(50), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<GRPOTransferQRLabel {self.label_number}/{self.total_labels}>'