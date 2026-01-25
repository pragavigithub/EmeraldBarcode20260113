import json
from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
import logging
from datetime import datetime
from app import db
from sap_integration import SAPIntegration
from modules.grpo_transfer.models import (
    GRPOTransferSession, GRPOTransferItem, GRPOTransferBatch,
    GRPOTransferSplit, GRPOTransferLog, GRPOTransferQRLabel
)

transfer_grpo_bp = Blueprint('transfer_grpo', __name__, template_folder='templates')
logger = logging.getLogger(__name__)

@transfer_grpo_bp.route('/')
@login_required
def index():
    return render_template('transfer_grpo/index.html')

@transfer_grpo_bp.route('/session/<int:session_id>')
@login_required
def session_detail(session_id):
    session = GRPOTransferSession.query.get_or_404(session_id)
    return render_template('transfer_grpo/session_detail.html', session=session)

@transfer_grpo_bp.route('/api/series', methods=['GET'])
@login_required
def get_series():
    sap = SAPIntegration()
    url = f"{sap.base_url}/b1s/v1/SQLQueries('GET_GRPO_Series')/List"
    response = sap.session.get(url, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch series"})

@transfer_grpo_bp.route('/api/documents/<series_id>', methods=['GET'])
@login_required
def get_documents(series_id):
    sap = SAPIntegration()
    url = f"{sap.base_url}/b1s/v1/SQLQueries('GET_GRPO_DocEntry_By_Series')/List"
    payload = {"ParamList": f"seriesID='{series_id}'"}
    response = sap.session.post(url, json=payload, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch documents"})

@transfer_grpo_bp.route('/api/grpo-details/<doc_entry>', methods=['GET'])
@login_required
def get_grpo_details(doc_entry):
    sap = SAPIntegration()
    url = f"{sap.base_url}/b1s/v1/$crossjoin(PurchaseDeliveryNotes,PurchaseDeliveryNotes/DocumentLines)?$expand=PurchaseDeliveryNotes($select=CardCode,CardName,DocumentStatus,DocNum,Series,DocDate,DocDueDate,DocTotal,DocEntry),PurchaseDeliveryNotes/DocumentLines($select=LineNum,ItemCode,ItemDescription,WarehouseCode,UnitsOfMeasurment,DocEntry,LineTotal,LineStatus,Quantity,Price,PriceAfterVAT)&$filter=PurchaseDeliveryNotes/DocEntry eq PurchaseDeliveryNotes/DocumentLines/DocEntry and PurchaseDeliveryNotes/DocEntry eq {doc_entry}"
    response = sap.session.get(url, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch GRPO details"})

@transfer_grpo_bp.route('/api/create-session', methods=['POST'])
@login_required
def create_session():
    try:
        data = request.json
        doc_entry = data.get('doc_entry')
        
        # Check if session already exists for this GRPO
        existing = GRPOTransferSession.query.filter_by(grpo_doc_entry=doc_entry).first()
        if existing:
            return jsonify({"success": True, "session_id": existing.id})

        sap = SAPIntegration()
        url = f"{sap.base_url}/b1s/v1/$crossjoin(PurchaseDeliveryNotes,PurchaseDeliveryNotes/DocumentLines)?$expand=PurchaseDeliveryNotes($select=CardCode,CardName,DocumentStatus,DocNum,Series,DocDate,DocDueDate,DocTotal,DocEntry),PurchaseDeliveryNotes/DocumentLines($select=LineNum,ItemCode,ItemDescription,WarehouseCode,UnitsOfMeasurment,DocEntry,LineTotal,LineStatus,Quantity,Price,PriceAfterVAT)&$filter=PurchaseDeliveryNotes/DocEntry eq PurchaseDeliveryNotes/DocumentLines/DocEntry and PurchaseDeliveryNotes/DocEntry eq {doc_entry}"
        response = sap.session.get(url, timeout=30)
        
        if response.status_code != 200:
            return jsonify({"success": False, "error": "SAP error"}), 500
            
        sap_data = response.json().get('value', [])
        if not sap_data:
            return jsonify({"success": False, "error": "No data found"}), 404
            
        header = sap_data[0]['PurchaseDeliveryNotes']
        session_code = f"GRPO-{header['DocNum']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        session = GRPOTransferSession(
            session_code=session_code,
            grpo_doc_entry=doc_entry,
            grpo_doc_num=str(header['DocNum']),
            series_id=header['Series'],
            vendor_code=header['CardCode'],
            vendor_name=header['CardName'],
            doc_date=datetime.strptime(header['DocDate'], '%Y-%m-%d').date(),
            doc_total=float(header['DocTotal']),
            status='draft'
        )
        db.session.add(session)
        db.session.flush()

        for line in sap_data:
            row = line['PurchaseDeliveryNotes/DocumentLines']
            item = GRPOTransferItem(
                session_id=session.id,
                line_num=row['LineNum'],
                item_code=row['ItemCode'],
                item_name=row['ItemDescription'],
                received_quantity=float(row['Quantity']),
                from_warehouse=row['WarehouseCode'],
                price=float(row['Price']),
                line_total=float(row['LineTotal']),
                sap_base_entry=doc_entry,
                sap_base_line=row['LineNum'],
                qc_status='pending'
            )
            db.session.add(item)
            
        db.session.commit()
        return jsonify({"success": True, "session_id": session.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@transfer_grpo_bp.route('/api/update-item', methods=['POST'])
@login_required
def update_item():
    try:
        data = request.json
        item_id = data.get('item_id')
        item = GRPOTransferItem.query.get_or_404(item_id)
        
        item.approved_quantity = float(data.get('approved_qty', 0))
        item.rejected_quantity = float(data.get('rejected_qty', 0))
        item.to_warehouse = data.get('to_warehouse')
        item.to_bin_code = data.get('to_bin')
        item.qc_notes = data.get('notes')
        item.qc_status = 'approved' if item.approved_quantity > 0 else 'pending'
        
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500

@transfer_grpo_bp.route('/api/warehouses', methods=['GET'])
@login_required
def get_warehouses():
    sap = SAPIntegration()
    url = f"{sap.base_url}/b1s/v1/Warehouses?$select=WarehouseName,WarehouseCode"
    response = sap.session.get(url, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch warehouses"})

@transfer_grpo_bp.route('/api/bin-locations/<wh_code>', methods=['GET'])
@login_required
def get_bins(wh_code):
    sap = SAPIntegration()
    url = f"{sap.base_url}/b1s/v1/BinLocations?$select=AbsEntry,BinCode,Warehouse&$filter=Warehouse eq '{wh_code}'"
    response = sap.session.get(url, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch bins"})

@transfer_grpo_bp.route('/api/generate-labels/<int:session_id>', methods=['POST'])
@login_required
def generate_labels(session_id):
    try:
        session = GRPOTransferSession.query.get_or_404(session_id)
        # Clear existing labels
        GRPOTransferQRLabel.query.filter_by(session_id=session_id).delete()
        
        for item in session.items:
            if item.qc_status == 'approved' and item.approved_quantity > 0:
                qr_data = {
                    "DocNum": session.grpo_doc_num,
                    "ItemCode": item.item_code,
                    "Qty": item.approved_quantity,
                    "Whse": item.to_warehouse,
                    "Bin": item.to_bin_code,
                    "Date": datetime.now().strftime('%Y-%m-%d')
                }
                label = GRPOTransferQRLabel(
                    session_id=session_id,
                    item_id=item.id,
                    label_number=1,
                    total_labels=1,
                    qr_data=json.dumps(qr_data),
                    quantity=item.approved_quantity,
                    from_warehouse=item.from_warehouse,
                    to_warehouse=item.to_warehouse
                )
                db.session.add(label)
        
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
