"""
GRPO Transfer Module Routes
Handles QC validation and warehouse transfers
"""

from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
import logging
import json

from app import db
from models import User
from sap_integration import SAPIntegration
from .models import (
    GRPOTransferSession, GRPOTransferItem, GRPOTransferBatch,
    GRPOTransferSplit, GRPOTransferLog, GRPOTransferQRLabel
)

# Create blueprint
grpo_transfer_bp = Blueprint('grpo_transfer', __name__, url_prefix='/grpo-transfer', template_folder='templates')

logger = logging.getLogger(__name__)

# ============================================================================
# UI ROUTES
# ============================================================================

@grpo_transfer_bp.route('/', methods=['GET'])
@login_required
def index():
    """Main GRPO Transfer dashboard"""
    return render_template('grpo_transfer/index.html')

@grpo_transfer_bp.route('/session/<int:session_id>', methods=['GET'])
@login_required
def session_detail(session_id):
    """View session details"""
    session = GRPOTransferSession.query.get_or_404(session_id)
    
    # Convert items to dictionaries for JSON serialization
    items_data = []
    for item in session.items:
        items_data.append({
            'id': item.id,
            'item_code': item.item_code,
            'item_name': item.item_name,
            'item_description': item.item_description,
            'is_batch_item': item.is_batch_item,
            'is_serial_item': item.is_serial_item,
            'is_non_managed': item.is_non_managed,
            'received_quantity': item.received_quantity,
            'approved_quantity': item.approved_quantity,
            'rejected_quantity': item.rejected_quantity,
            'from_warehouse': item.from_warehouse,
            'from_bin_code': item.from_bin_code,
            'to_warehouse': item.to_warehouse,
            'to_bin_code': item.to_bin_code,
            'unit_of_measure': item.unit_of_measure,
            'price': item.price,
            'line_total': item.line_total,
            'qc_status': item.qc_status,
            'qc_notes': item.qc_notes,
            'sap_base_entry': item.sap_base_entry,
            'sap_base_line': item.sap_base_line
        })
    
    return render_template('grpo_transfer/session_detail.html', session=session, items_json=items_data)

@grpo_transfer_bp.route('/session/<int:session_id>/qc', methods=['GET'])
@login_required
def qc_validation(session_id):
    """QC validation screen"""
    session = GRPOTransferSession.query.get_or_404(session_id)
    return render_template('grpo_transfer/qc_validation.html', session=session)

@grpo_transfer_bp.route('/session/create/<int:doc_entry>', methods=['GET', 'POST'])
@login_required
def create_session_view(doc_entry):
    """Create new transfer session - display document details and add items"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            flash('SAP B1 authentication failed', 'error')
            return redirect(url_for('grpo_transfer.index'))
        
        # Get GRPO details using $crossjoin to properly join document header with line items
        url = f"{sap.base_url}/b1s/v1/$crossjoin(PurchaseDeliveryNotes,PurchaseDeliveryNotes/DocumentLines)?$expand=PurchaseDeliveryNotes($select=CardCode,CardName,DocumentStatus,DocNum,Series,DocDate,DocDueDate,DocTotal,DocEntry),PurchaseDeliveryNotes/DocumentLines($select=LineNum,ItemCode,ItemDescription,WarehouseCode,UnitsOfMeasurment,DocEntry,LineTotal,LineStatus,Quantity,Price,PriceAfterVAT)&$filter=PurchaseDeliveryNotes/DocumentStatus eq PurchaseDeliveryNotes/DocumentLines/LineStatus and PurchaseDeliveryNotes/DocEntry eq PurchaseDeliveryNotes/DocumentLines/DocEntry and PurchaseDeliveryNotes/DocumentLines/DocEntry eq {doc_entry}"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching GRPO details from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            value_list = data.get('value', [])
            
            if not value_list:
                logger.warning(f"No data found for GRPO document {doc_entry}")
                flash('No data found for this GRPO document', 'error')
                return redirect(url_for('grpo_transfer.index'))
            
            # Extract document details (same for all rows) and line items
            doc_details = None
            line_items = []
            
            for item in value_list:
                if 'PurchaseDeliveryNotes' in item and not doc_details:
                    doc_details = item['PurchaseDeliveryNotes']
                
                if 'PurchaseDeliveryNotes/DocumentLines' in item:
                    line_items.append(item['PurchaseDeliveryNotes/DocumentLines'])
            
            logger.info(f"✅ Retrieved GRPO document {doc_entry} with {len(line_items)} line items")
            
            # Create session
            session_code = f"GRPO-{doc_entry}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            session = GRPOTransferSession(
                session_code=session_code,
                grpo_doc_entry=doc_entry,
                grpo_doc_num=doc_details.get('DocNum'),
                series_id=doc_details.get('Series'),
                vendor_code=doc_details.get('CardCode'),
                vendor_name=doc_details.get('CardName'),
                doc_date=datetime.strptime(doc_details.get('DocDate', datetime.now().isoformat()), '%Y-%m-%d').date(),
                doc_due_date=datetime.strptime(doc_details.get('DocDueDate', datetime.now().isoformat()), '%Y-%m-%d').date() if doc_details.get('DocDueDate') else None,
                doc_total=float(doc_details.get('DocTotal', 0.0))
            )
            
            db.session.add(session)
            db.session.flush()  # Flush to get session.id
            
            # Add line items to session
            for line in line_items:
                item = GRPOTransferItem(
                    session_id=session.id,
                    line_num=line.get('LineNum'),
                    item_code=line.get('ItemCode'),
                    item_name=line.get('ItemDescription'),
                    item_description=line.get('ItemDescription'),
                    received_quantity=float(line.get('Quantity', 0)),
                    from_warehouse=line.get('WarehouseCode'),
                    unit_of_measure=line.get('UnitsOfMeasurment', 1),
                    price=float(line.get('Price', 0)),
                    line_total=float(line.get('LineTotal', 0)),
                    sap_base_entry=doc_entry,
                    sap_base_line=line.get('LineNum')
                )
                db.session.add(item)
            
            db.session.commit()
            
            # Log activity
            log = GRPOTransferLog(
                session_id=session.id,
                user_id=current_user.id,
                action='session_created',
                description=f'Created transfer session for GRPO {doc_details.get("DocNum")} with {len(line_items)} items'
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"✅ Created session {session.id} with {len(line_items)} items")
            
            # Redirect to session detail page
            return redirect(url_for('grpo_transfer.session_detail', session_id=session.id))
            
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            flash(f'Failed to load GRPO details: {response.status_code}', 'error')
            return redirect(url_for('grpo_transfer.index'))
            
    except Exception as e:
        logger.error(f"Error creating session view: {str(e)}")
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('grpo_transfer.index'))

# ============================================================================
# API ROUTES - Get Sessions List
# ============================================================================

@grpo_transfer_bp.route('/api/sessions', methods=['GET'])
@login_required
def get_sessions():
    """Get all active sessions"""
    try:
        sessions = GRPOTransferSession.query.filter(
            GRPOTransferSession.status.in_(['draft', 'in_progress', 'completed'])
        ).order_by(GRPOTransferSession.created_at.desc()).all()
        
        sessions_data = []
        for session in sessions:
            sessions_data.append({
                'id': session.id,
                'session_code': session.session_code,
                'grpo_doc_num': session.grpo_doc_num,
                'vendor_name': session.vendor_name,
                'status': session.status,
                'item_count': len(session.items),
                'created_at': session.created_at.isoformat()
            })
        
        return jsonify({
            'success': True,
            'sessions': sessions_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching sessions: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 1: Get Series List
# ============================================================================

@grpo_transfer_bp.route('/api/series-list', methods=['GET'])
@login_required
def get_series_list():
    """Get GRPO series list from SAP B1"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Call SAP B1 OData endpoint to get document series
        # Document Type 1250000001 = Purchase Delivery Note (GRPO)
        url = f"{sap.base_url}/b1s/v1/SQLQueries('GET_GRPO_Series')/List"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching GRPO series from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            series_data = data.get('value', [])
            
            if series_data:
                series_list = []
                for series in series_data:
                    series_list.append({
                        'SeriesID': series.get('SeriesID'),
                        'SeriesName': series.get('SeriesName'),
                        'NextNumber': series.get('NextNumber')
                    })
                
                logger.info(f"✅ Retrieved {len(series_list)} GRPO series from SAP B1")
                return jsonify({
                    'success': True,
                    'series': series_list
                })
            else:
                logger.warning("No GRPO series found in SAP B1")
                return jsonify({
                    'success': True,
                    'series': [],
                    'message': 'No GRPO series configured in SAP B1'
                })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching series list: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 2: Get Document Numbers by Series
# ============================================================================

@grpo_transfer_bp.route('/api/doc-numbers/<int:series_id>', methods=['GET'])
@login_required
def get_doc_numbers(series_id):
    """Get GRPO document numbers for selected series"""
    try:
        sap = SAPIntegration()

        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500

        # SAP SQL Query Service Layer endpoint
        url = f"{sap.base_url}/b1s/v1/SQLQueries('GET_GRPO_DocEntry_By_Series')/List"

        headers = {
            'Prefer': 'odata.maxpagesize=0',
            'Content-Type': 'application/json'
        }

        # ✅ Forward series_id to body
        payload = {
            "ParamList": f"seriesID='{series_id}'"
        }

        logger.debug(f"Fetching GRPO documents for series {series_id}")
        response = sap.session.post(
            url,
            headers=headers,
            json=payload,
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            doc_data = data.get('value', [])

            doc_list = []
            for doc in doc_data:
                doc_list.append({
                    'DocEntry': doc.get('DocEntry'),
                    'DocNum': doc.get('DocNum'),
                    'CardName': doc.get('CardName'),
                    'DocStatus': doc.get('DocStatus')
                })

            logger.info(f"✅ Retrieved {len(doc_list)} GRPO documents for series {series_id}")

            return jsonify({
                'success': True,
                'documents': doc_list
            })

        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': response.text
            }), 500

    except Exception as e:
        logger.exception("Error fetching document numbers")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# STEP 3: Get GRPO Document Details
# ============================================================================

@grpo_transfer_bp.route('/api/grpo-details/<int:doc_entry>', methods=['GET'])
@login_required
def get_grpo_details(doc_entry):
    """Get GRPO document details with line items using $crossjoin"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Use $crossjoin to properly join document header with line items
        url = f"{sap.base_url}/b1s/v1/$crossjoin(PurchaseDeliveryNotes,PurchaseDeliveryNotes/DocumentLines)?$expand=PurchaseDeliveryNotes($select=CardCode,CardName,DocumentStatus,DocNum,Series,DocDate,DocDueDate,DocTotal,DocEntry),PurchaseDeliveryNotes/DocumentLines($select=LineNum,ItemCode,ItemDescription,WarehouseCode,UnitsOfMeasurment,DocEntry,LineTotal,LineStatus,Quantity,Price,PriceAfterVAT)&$filter=PurchaseDeliveryNotes/DocumentStatus eq PurchaseDeliveryNotes/DocumentLines/LineStatus and PurchaseDeliveryNotes/DocEntry eq PurchaseDeliveryNotes/DocumentLines/DocEntry and PurchaseDeliveryNotes/DocumentLines/DocEntry eq {doc_entry}"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching GRPO details from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            value_list = data.get('value', [])
            
            if not value_list:
                logger.warning(f"No data found for GRPO document {doc_entry}")
                return jsonify({
                    'success': True,
                    'document': None,
                    'line_items': [],
                    'message': 'No data found for this document'
                })
            
            # Extract document details (same for all rows) and line items
            doc_details = None
            line_items = []
            
            for item in value_list:
                if 'PurchaseDeliveryNotes' in item and not doc_details:
                    doc_details = item['PurchaseDeliveryNotes']
                
                if 'PurchaseDeliveryNotes/DocumentLines' in item:
                    line_items.append(item['PurchaseDeliveryNotes/DocumentLines'])
            
            logger.info(f"✅ Retrieved GRPO document {doc_entry} with {len(line_items)} line items")
            return jsonify({
                'success': True,
                'document': doc_details,
                'line_items': line_items
            })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching GRPO details: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 4: Create Transfer Session
# ============================================================================

@grpo_transfer_bp.route('/api/create-session', methods=['POST'])
@login_required
def create_session():
    """Create a new GRPO transfer session"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['grpo_doc_entry', 'grpo_doc_num', 'series_id', 'vendor_code', 'vendor_name']
        if not all(field in data for field in required_fields):
            return jsonify({
                'success': False,
                'error': 'Missing required fields'
            }), 400
        
        # Generate session code
        session_code = f"GRPO-{data['grpo_doc_entry']}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Create session
        session = GRPOTransferSession(
            session_code=session_code,
            grpo_doc_entry=data['grpo_doc_entry'],
            grpo_doc_num=data['grpo_doc_num'],
            series_id=data['series_id'],
            vendor_code=data['vendor_code'],
            vendor_name=data['vendor_name'],
            doc_date=datetime.strptime(data.get('doc_date', datetime.now().isoformat()), '%Y-%m-%d').date(),
            doc_due_date=datetime.strptime(data.get('doc_due_date', datetime.now().isoformat()), '%Y-%m-%d').date() if data.get('doc_due_date') else None,
            doc_total=float(data.get('doc_total', 0.0))
        )
        
        db.session.add(session)
        db.session.commit()
        
        # Log activity
        log = GRPOTransferLog(
            session_id=session.id,
            user_id=current_user.id,
            action='session_created',
            description=f'Created transfer session for GRPO {data["grpo_doc_num"]}'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'session_id': session.id,
            'session_code': session_code
        })
        
    except Exception as e:
        logger.error(f"Error creating session: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 5: Validate Item Type (Batch/Serial/Non-Managed)
# ============================================================================

@grpo_transfer_bp.route('/api/validate-item/<item_code>', methods=['GET'])
@login_required
def validate_item(item_code):
    """Validate item type (batch, serial, or non-managed) using SQL Query"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Use SQL Query to validate item - this is the correct method for SAP B1
        url = f"{sap.base_url}/b1s/v1/SQLQueries('ItemCode_Batch_Serial_Val')/List"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        payload = {"ParamList": f"itemCode='{item_code}'"}
        
        logger.debug(f"Validating item: {item_code}")
        response = sap.session.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            items = data.get('value', [])
            
            if items:
                item_info = items[0]
                
                # Check batch and serial flags
                is_batch = item_info.get('BatchNum') == 'Y'
                is_serial = item_info.get('SerialNum') == 'Y'
                is_non_managed = not is_batch and not is_serial
                
                logger.info(f"✅ Item {item_code} validated - Batch: {is_batch}, Serial: {is_serial}")
                return jsonify({
                    'success': True,
                    'item_code': item_code,
                    'item_name': item_info.get('ItemName'),
                    'is_batch_item': is_batch,
                    'is_serial_item': is_serial,
                    'is_non_managed': is_non_managed,
                    'batch_num': item_info.get('BatchNum'),
                    'serial_num': item_info.get('SerialNum')
                })
            else:
                logger.warning(f"Item {item_code} not found in SAP B1")
                return jsonify({
                    'success': False,
                    'error': 'Item not found in SAP B1'
                }), 404
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error validating item: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 6: Get Batch Numbers for Item
# ============================================================================

@grpo_transfer_bp.route('/api/batch-numbers/<int:doc_entry>', methods=['GET'])
@login_required
def get_batch_numbers(doc_entry):
    """Get batch numbers for GRPO document using SQL Query"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Use SQL Query to get batch numbers - this is the correct method for SAP B1
        url = f"{sap.base_url}/b1s/v1/SQLQueries('Get_Batches_By_DocEntry')/List"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        payload = {"ParamList": f"docEntry='{doc_entry}'"}
        
        logger.debug(f"Fetching batch numbers for document: {doc_entry}")
        response = sap.session.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            batches = data.get('value', [])
            
            if batches:
                logger.info(f"✅ Retrieved {len(batches)} batch numbers for document {doc_entry}")
                return jsonify({
                    'success': True,
                    'batches': batches
                })
            else:
                logger.warning(f"No batch numbers found for document {doc_entry}")
                return jsonify({
                    'success': True,
                    'batches': [],
                    'message': 'No batch numbers found'
                })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching batch numbers: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 7: Get Warehouses
# ============================================================================

@grpo_transfer_bp.route('/api/warehouses', methods=['GET'])
@login_required
def get_warehouses():
    """Get list of warehouses from SAP B1"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Call SAP B1 OData endpoint
        url = f"{sap.base_url}/b1s/v1/Warehouses?$select=WarehouseName,WarehouseCode"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching warehouses from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            warehouses = data.get('value', [])
            
            logger.info(f"✅ Retrieved {len(warehouses)} warehouses from SAP B1")
            return jsonify({
                'success': True,
                'warehouses': warehouses
            })
        else:
            logger.error(f"SAP B1 API error: {response.status_code} - {response.text}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error fetching warehouses: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 8: Get Bin Codes for Warehouse
# ============================================================================

@grpo_transfer_bp.route('/api/bin-codes/<warehouse_code>', methods=['GET'])
@login_required
def get_bin_codes(warehouse_code):
    """Get bin codes for selected warehouse"""
    try:
        sap = SAPIntegration()
        
        # Ensure logged in
        if not sap.ensure_logged_in():
            return jsonify({
                'success': False,
                'error': 'SAP B1 authentication failed'
            }), 500
        
        # Call SAP B1 OData endpoint
        url = f"{sap.base_url}/b1s/v1/BinLocations?$select=AbsEntry,BinCode,Warehouse&$filter=Warehouse eq '{warehouse_code}'"
        headers = {'Prefer': 'odata.maxpagesize=0'}
        
        logger.debug(f"Fetching bin codes from: {url}")
        response = sap.session.get(url, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            bins = data.get('value', [])
            
            logger.info(f"✅ Retrieved {len(bins)} bin codes for warehouse {warehouse_code}")
            return jsonify({
                'success': True,
                'bins': bins
            })
        else:
            logger.warning(f"No bin codes found for warehouse {warehouse_code}")
            return jsonify({
                'success': True,
                'bins': [],
                'message': 'No bin codes found for warehouse'
            })
            
    except Exception as e:
        logger.error(f"Error fetching bin codes: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 9: Add Item to Session
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/add-item', methods=['POST'])
@login_required
def add_item_to_session(session_id):
    """Add item to transfer session"""
    try:
        data = request.get_json()
        session = GRPOTransferSession.query.get(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Create transfer item
        item = GRPOTransferItem(
            session_id=session_id,
            line_num=data.get('line_num'),
            item_code=data.get('item_code'),
            item_name=data.get('item_name'),
            item_description=data.get('item_description'),
            is_batch_item=data.get('is_batch_item', False),
            is_serial_item=data.get('is_serial_item', False),
            is_non_managed=data.get('is_non_managed', False),
            received_quantity=float(data.get('received_quantity', 0)),
            from_warehouse=data.get('from_warehouse'),
            unit_of_measure=data.get('unit_of_measure', '1'),
            price=float(data.get('price', 0)),
            line_total=float(data.get('line_total', 0)),
            sap_base_entry=data.get('sap_base_entry'),
            sap_base_line=data.get('sap_base_line')
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'item_id': item.id
        })
        
    except Exception as e:
        logger.error(f"Error adding item: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 10: QC Approval - Split and Approve Items
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/qc-approve', methods=['POST'])
@login_required
def qc_approve_items(session_id):
    """QC team approves/rejects items with splits"""
    try:
        data = request.get_json()
        session = GRPOTransferSession.query.get(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Process each item approval
        for item_approval in data.get('items', []):
            item = GRPOTransferItem.query.get(item_approval['item_id'])
            if not item:
                continue
            
            # Update item quantities
            item.approved_quantity = float(item_approval.get('approved_quantity', 0))
            item.rejected_quantity = float(item_approval.get('rejected_quantity', 0))
            item.qc_status = item_approval.get('qc_status', 'pending')
            item.qc_notes = item_approval.get('qc_notes')
            item.to_warehouse = item_approval.get('to_warehouse')
            item.to_bin_code = item_approval.get('to_bin_code')
            
            # Create splits if needed
            splits = item_approval.get('splits', [])
            for split_data in splits:
                split = GRPOTransferSplit(
                    item_id=item.id,
                    split_number=split_data.get('split_number'),
                    quantity=float(split_data.get('quantity', 0)),
                    status=split_data.get('status'),  # 'OK', 'NOTOK', 'HOLD'
                    from_warehouse=split_data.get('from_warehouse'),
                    from_bin_code=split_data.get('from_bin_code'),
                    to_warehouse=split_data.get('to_warehouse'),
                    to_bin_code=split_data.get('to_bin_code'),
                    batch_number=split_data.get('batch_number'),
                    notes=split_data.get('notes')
                )
                db.session.add(split)
        
        session.status = 'in_progress'
        session.qc_approved_by = current_user.id
        db.session.commit()
        
        # Log activity
        log = GRPOTransferLog(
            session_id=session_id,
            user_id=current_user.id,
            action='qc_approved',
            description='QC team approved items'
        )
        db.session.add(log)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Items approved successfully'
        })
        
    except Exception as e:
        logger.error(f"Error approving items: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 11: Get QR Labels for Session
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/labels', methods=['GET'])
@login_required
def get_session_labels(session_id):
    """Get QR labels for session"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        labels = GRPOTransferQRLabel.query.filter_by(session_id=session_id).all()
        
        labels_data = []
        for label in labels:
            labels_data.append({
                'id': label.id,
                'item_code': label.item_id,
                'label_number': label.label_number,
                'total_labels': label.total_labels,
                'qr_data': label.qr_data,
                'batch_number': label.batch_number,
                'quantity': label.quantity
            })
        
        return jsonify({
            'success': True,
            'labels': labels_data
        })
        
    except Exception as e:
        logger.error(f"Error fetching labels: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# ============================================================================
# STEP 12: Generate QR Labels for Approved Items
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/generate-qr-labels', methods=['POST'])
@login_required
def generate_qr_labels(session_id):
    """Generate QR labels for approved items"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Check if there are any approved items
        approved_items = [item for item in session.items if item.qc_status == 'approved' and item.approved_quantity > 0]
        
        if not approved_items:
            return jsonify({
                'success': False,
                'error': 'No approved items found. Please submit QC approval first.'
            }), 400
        
        labels = []
        label_count = 0
        
        for item in approved_items:
            # Generate one label per approved quantity unit
            approved_qty = int(item.approved_quantity)
            
            if approved_qty <= 0:
                continue
            
            for label_num in range(1, approved_qty + 1):
                qr_data = {
                    'session_code': session.session_code,
                    'item_code': item.item_code,
                    'item_name': item.item_name,
                    'quantity': 1,
                    'label': f'{label_num} of {approved_qty}',
                    'from_warehouse': item.from_warehouse,
                    'to_warehouse': item.to_warehouse,
                    'batch_number': item.batches[0].batch_number if item.batches else None,
                    'timestamp': datetime.now().isoformat()
                }
                
                label = GRPOTransferQRLabel(
                    session_id=session_id,
                    item_id=item.id,
                    label_number=label_num,
                    total_labels=approved_qty,
                    qr_data=json.dumps(qr_data),
                    batch_number=item.batches[0].batch_number if item.batches else None,
                    quantity=1,
                    from_warehouse=item.from_warehouse,
                    to_warehouse=item.to_warehouse
                )
                db.session.add(label)
                labels.append(qr_data)
                label_count += 1
        
        if label_count == 0:
            return jsonify({
                'success': False,
                'error': 'No labels could be generated. Check approved quantities.'
            }), 400
        
        db.session.commit()
        
        logger.info(f"✅ Generated {label_count} QR labels for session {session_id}")
        
        return jsonify({
            'success': True,
            'labels_generated': label_count,
            'labels': labels
        })
        
    except Exception as e:
        logger.error(f"Error generating QR labels: {str(e)}")
        db.session.rollback()
        return jsonify({
            'success': False,
            'error': f'Error: {str(e)}'
        }), 500

# ============================================================================
# STEP 12: Post Stock Transfer to SAP B1
# ============================================================================

@grpo_transfer_bp.route('/api/session/<int:session_id>/post-transfer', methods=['POST'])
@login_required
def post_transfer_to_sap(session_id):
    """Post stock transfer to SAP B1"""
    try:
        session = GRPOTransferSession.query.get(session_id)
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        sap = SAPIntegration()
        
        # Build stock transfer JSON
        stock_transfer = {
            'DocDate': session.doc_date.isoformat(),
            'Comments': f'QC Approved WMS Transfer {session.session_code} by {current_user.first_name}',
            'FromWarehouse': session.items[0].from_warehouse if session.items else '',
            'ToWarehouse': session.items[0].to_warehouse if session.items else '',
            'StockTransferLines': []
        }
        
        # Add line items
        for idx, item in enumerate(session.items):
            if item.qc_status != 'approved':
                continue
            
            line = {
                'LineNum': idx,
                'ItemCode': item.item_code,
                'Quantity': item.approved_quantity,
                'WarehouseCode': item.to_warehouse,
                'FromWarehouseCode': item.from_warehouse,
                'BaseEntry': item.sap_base_entry,
                'BaseLine': item.sap_base_line,
                'BaseType': '1250000001',  # GRPO document type
                'BatchNumbers': [],
                'StockTransferLinesBinAllocations': []
            }
            
            # Add batch numbers if batch item
            if item.is_batch_item and item.batches:
                for batch in item.batches:
                    line['BatchNumbers'].append({
                        'BatchNumber': batch.batch_number,
                        'Quantity': batch.approved_quantity
                    })
            
            # Add bin allocations
            if item.from_bin_code:
                line['StockTransferLinesBinAllocations'].append({
                    'BinActionType': 'batFromWarehouse',
                    'BinAbsEntry': 1,  # Get from SAP
                    'Quantity': item.approved_quantity,
                    'SerialAndBatchNumbersBaseLine': 0
                })
            
            if item.to_bin_code:
                line['StockTransferLinesBinAllocations'].append({
                    'BinActionType': 'batToWarehouse',
                    'BinAbsEntry': 1,  # Get from SAP
                    'Quantity': item.approved_quantity,
                    'SerialAndBatchNumbersBaseLine': 0
                })
            
            stock_transfer['StockTransferLines'].append(line)
        
        # Post to SAP B1
        url = f"{sap.base_url}/b1s/v1/StockTransfers"
        
        logger.debug(f"Posting stock transfer to: {url}")
        response = sap.session.post(url, json=stock_transfer, timeout=30)
        
        if response.status_code in [200, 201]:
            data = response.json()
            
            # Update session with SAP response
            session.transfer_doc_entry = data.get('DocEntry')
            session.transfer_doc_num = data.get('DocNum')
            session.status = 'transferred'
            db.session.commit()
            
            # Log activity
            log = GRPOTransferLog(
                session_id=session_id,
                user_id=current_user.id,
                action='transferred',
                description=f'Posted to SAP B1 - DocEntry: {data.get("DocEntry")}',
                sap_response=json.dumps(data)
            )
            db.session.add(log)
            db.session.commit()
            
            logger.info(f"✅ Stock transfer posted to SAP B1 - DocEntry: {data.get('DocEntry')}")
            return jsonify({
                'success': True,
                'sap_doc_entry': data.get('DocEntry'),
                'sap_doc_num': data.get('DocNum'),
                'message': 'Stock transfer posted to SAP B1 successfully'
            })
        else:
            error_msg = response.text if response.text else 'Unknown error'
            logger.error(f"SAP B1 API error: {response.status_code} - {error_msg}")
            return jsonify({
                'success': False,
                'error': f'SAP B1 API error: {response.status_code}'
            }), 500
            
    except Exception as e:
        logger.error(f"Error posting transfer to SAP: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500