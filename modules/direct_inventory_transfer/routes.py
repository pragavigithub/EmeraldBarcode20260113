from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from datetime import datetime
import logging
import json
from pathlib import Path

from app import db
from models import DirectInventoryTransfer, DirectInventoryTransferItem, DocumentNumberSeries
from sap_integration import SAPIntegration

# Use absolute path for template_folder to support PyInstaller .exe builds
direct_inventory_transfer_bp = Blueprint('direct_inventory_transfer', __name__, 
                                         url_prefix='/direct-inventory-transfer',
                                         template_folder=str(Path(__file__).resolve().parent / 'templates'))


def generate_direct_transfer_number():
    """Generate unique transfer number for Direct Inventory Transfer"""
    return DocumentNumberSeries.get_next_number('DIRECT_INVENTORY_TRANSFER')

@direct_inventory_transfer_bp.route('/', methods=['GET'])
@login_required
def index():
    """Direct Inventory Transfer main page with filtering, search, and pagination"""
    if not current_user.has_permission('direct_inventory_transfer'):
        flash('Access denied - Direct Inventory Transfer permissions required', 'error')
        return redirect(url_for('dashboard'))

    # -------------------------------
    # JSON OR HTML DETECTION
    # -------------------------------
    is_json_request = (
        request.is_json or
        'application/json' in request.headers.get('Content-Type', '') or
        'application/json' in request.headers.get('Accept', '')
    )

    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search_term = request.args.get('search', '').strip()
    from_date = request.args.get('from_date', '').strip()
    to_date = request.args.get('to_date', '').strip()
    status_filter = request.args.get('status', '').strip()

    if per_page not in [5, 10, 25, 50, 100]:
        per_page = 10

    query = DirectInventoryTransfer.query

    if current_user.role not in ['admin', 'manager']:
        query = query.filter_by(user_id=current_user.id)

    if search_term:
        search_pattern = f'%{search_term}%'
        query = query.filter(
            db.or_(
                DirectInventoryTransfer.transfer_number.ilike(search_pattern),
                DirectInventoryTransfer.from_warehouse.ilike(search_pattern),
                DirectInventoryTransfer.to_warehouse.ilike(search_pattern),
                DirectInventoryTransfer.notes.ilike(search_pattern)
            )
        )

    if status_filter:
        query = query.filter(DirectInventoryTransfer.status == status_filter)

    if from_date:
        query = query.filter(DirectInventoryTransfer.created_at >= from_date)

    if to_date:
        query = query.filter(DirectInventoryTransfer.created_at <= f"{to_date} 23:59:59")

    query = query.order_by(DirectInventoryTransfer.created_at.desc())
    transfers_paginated = query.paginate(page=page, per_page=per_page, error_out=False)

    # -------------------------------
    # JSON RESPONSE (FOR FLUTTER)
    # -------------------------------
    if is_json_request:
        return jsonify({
            "success": True,
            "pagination": {
                "page": transfers_paginated.page,
                "per_page": transfers_paginated.per_page,
                "total_pages": transfers_paginated.pages,
                "total_records": transfers_paginated.total,
                "has_next": transfers_paginated.has_next,
                "has_prev": transfers_paginated.has_prev
            },
            "data": [
                {
                    "id": t.id,
                    "transfer_number": t.transfer_number,
                    "from_warehouse": t.from_warehouse,
                    "to_warehouse": t.to_warehouse,
                    "from_bin": t.from_bin,
                    "to_bin": t.to_bin,
                    "notes": t.notes,
                    "status": t.status,
                    "created_at": t.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                    "created_by": t.user_id
                }
                for t in transfers_paginated.items
            ]
        }), 200

    # -------------------------------
    # HTML RESPONSE (UNCHANGED)
    # -------------------------------
    return render_template(
        'direct_inventory_transfer/index.html',
        transfers=transfers_paginated.items,
        pagination=transfers_paginated,
        per_page=per_page,
        search_term=search_term,
        from_date=from_date,
        to_date=to_date,
        status_filter=status_filter,
        current_user=current_user
    )


# @direct_inventory_transfer_bp.route('/', methods=['GET'])
# @login_required
# def index():
#     """Direct Inventory Transfer main page with filtering, search, and pagination"""
#     if not current_user.has_permission('direct_inventory_transfer'):
#         flash('Access denied - Direct Inventory Transfer permissions required', 'error')
#         return redirect(url_for('dashboard'))
#
#     page = request.args.get('page', 1, type=int)
#     per_page = request.args.get('per_page', 10, type=int)
#     search_term = request.args.get('search', '').strip()
#     from_date = request.args.get('from_date', '').strip()
#     to_date = request.args.get('to_date', '').strip()
#     status_filter = request.args.get('status', '').strip()
#
#     if per_page not in [5, 10, 25, 50, 100]:
#         per_page = 10
#
#     query = DirectInventoryTransfer.query
#
#     if current_user.role not in ['admin', 'manager']:
#         query = query.filter_by(user_id=current_user.id)
#
#     if search_term:
#         search_pattern = f'%{search_term}%'
#         query = query.filter(
#             db.or_(
#                 DirectInventoryTransfer.transfer_number.ilike(search_pattern),
#                 DirectInventoryTransfer.from_warehouse.ilike(search_pattern),
#                 DirectInventoryTransfer.to_warehouse.ilike(search_pattern),
#                 DirectInventoryTransfer.notes.ilike(search_pattern)
#             )
#         )
#
#     if status_filter:
#         query = query.filter(DirectInventoryTransfer.status == status_filter)
#
#     if from_date:
#         query = query.filter(DirectInventoryTransfer.created_at >= from_date)
#
#     if to_date:
#         query = query.filter(DirectInventoryTransfer.created_at <= f"{to_date} 23:59:59")
#
#     query = query.order_by(DirectInventoryTransfer.created_at.desc())
#     transfers_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
#
#     return render_template('direct_inventory_transfer/index.html',
#                            transfers=transfers_paginated.items,
#                            pagination=transfers_paginated,
#                            per_page=per_page,
#                            search_term=search_term,
#                            from_date=from_date,
#                            to_date=to_date,
#                            status_filter=status_filter,
#                            current_user=current_user)

@direct_inventory_transfer_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create():
    """Create new Direct Inventory Transfer - Step 1: Choose warehouses and bins"""
    if not current_user.has_permission('direct_inventory_transfer'):
        flash('Access denied - Direct Inventory Transfer permissions required', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        try:
            # -------------------------------
            # JSON OR FORM DETECTION
            # -------------------------------
            is_json_request = request.is_json or 'application/json' in request.headers.get('Content-Type', '')
            data = request.get_json() if is_json_request else request.form

            # -------------------------------
            # STEP 1: CREATE DOCUMENT WITH WAREHOUSES
            # -------------------------------
            from_warehouse = data.get('from_warehouse')
            to_warehouse = data.get('to_warehouse')
            from_bin = data.get('from_bin', '')
            to_bin = data.get('to_bin', '')
            notes = data.get('notes', '')

            # -------------------------------
            # BASIC VALIDATIONS
            # -------------------------------
            if not all([from_warehouse, to_warehouse]):
                msg = 'From Warehouse and To Warehouse are required'
                if is_json_request:
                    return jsonify({'success': False, 'error': msg}), 400
                flash(msg, 'error')
                return render_template('direct_inventory_transfer/create.html')

            if from_warehouse == to_warehouse:
                msg = 'From Warehouse and To Warehouse must be different'
                if is_json_request:
                    return jsonify({'success': False, 'error': msg}), 400
                flash(msg, 'error')
                return render_template('direct_inventory_transfer/create.html')

            # -------------------------------
            # CREATE TRANSFER DOCUMENT
            # -------------------------------
            transfer_number = generate_direct_transfer_number()
            
            transfer = DirectInventoryTransfer(
                transfer_number=transfer_number,
                user_id=current_user.id,
                from_warehouse=from_warehouse,
                to_warehouse=to_warehouse,
                from_bin=from_bin,
                to_bin=to_bin,
                notes=notes,
                status='draft'
            )

            db.session.add(transfer)
            db.session.commit()

            # -------------------------------
            # RESPONSE
            # -------------------------------
            if is_json_request:
                return jsonify({
                    'success': True,
                    'transfer_id': transfer.id,
                    'transfer_number': transfer_number,
                    'message': 'Transfer document created successfully. Now add serial numbers.'
                }), 201

            flash(f'Direct Inventory Transfer {transfer_number} created successfully. Now add serial numbers.', 'success')
            return redirect(url_for('direct_inventory_transfer.detail', transfer_id=transfer.id))

        except Exception as e:
            db.session.rollback()
            logging.error(f"Error creating direct inventory transfer: {str(e)}")

            if is_json_request:
                return jsonify({'success': False, 'error': str(e)}), 500

            flash(f'Error creating transfer: {str(e)}', 'error')
            return render_template('direct_inventory_transfer/create.html')

    return render_template('direct_inventory_transfer/create.html')


# @direct_inventory_transfer_bp.route('/create', methods=['GET', 'POST'])
# @login_required
# def create():
#     """Create new Direct Inventory Transfer with first item included"""
#     if not current_user.has_permission('direct_inventory_transfer'):
#         flash('Access denied - Direct Inventory Transfer permissions required', 'error')
#         return redirect(url_for('dashboard'))
#
#     if request.method == 'POST':
#         try:
#             transfer_number = generate_direct_transfer_number()
#             print("transfer_number--->", transfer_number)
#             item_code = request.form.get('item_code', '').strip()
#             item_type = request.form.get('item_type', 'none')
#             quantity = float(request.form.get('quantity', 1))
#             from_warehouse = request.form.get('from_warehouse')
#             to_warehouse = request.form.get('to_warehouse')
#             from_bin = request.form.get('from_bin', '')
#             to_bin = request.form.get('to_bin', '')
#             notes = request.form.get('notes', '')
#             serial_numbers_str = request.form.get('serial_numbers', '').strip()
#             batch_number = request.form.get('batch_number', '').strip()
#
#             if not all([item_code, from_warehouse, to_warehouse]):
#                 if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
#                     return jsonify({'success': False, 'error': 'Item Code, From Warehouse and To Warehouse are required'}), 400
#                 flash('Item Code, From Warehouse and To Warehouse are required', 'error')
#                 return render_template('direct_inventory_transfer/create.html')
#
#             if from_warehouse == to_warehouse:
#                 if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
#                     return jsonify({'success': False, 'error': 'From Warehouse and To Warehouse must be different'}), 400
#                 flash('From Warehouse and To Warehouse must be different', 'error')
#                 return render_template('direct_inventory_transfer/create.html')
#
#             sap = SAPIntegration()
#             if not sap.ensure_logged_in():
#                 flash('SAP B1 authentication failed', 'error')
#                 return render_template('direct_inventory_transfer/create.html')
#
#             validation_result = sap.validate_item_for_direct_transfer(item_code)
#
#             if not validation_result.get('valid'):
#                 flash(f'Item validation failed: {validation_result.get("error", "Unknown error")}', 'error')
#                 return render_template('direct_inventory_transfer/create.html')
#
#             item_type_validated = validation_result.get('item_type', 'none')
#             is_serial_managed = validation_result.get('is_serial_managed', False)
#             is_batch_managed = validation_result.get('is_batch_managed', False)
#
#             serial_numbers_json = None
#             serial_numbers_list = []
#
#             if is_serial_managed:
#                 if not serial_numbers_str:
#                     flash('Serial numbers are required for serial-managed items', 'error')
#                     return render_template('direct_inventory_transfer/create.html')
#
#                 serial_numbers_list = [sn.strip() for sn in serial_numbers_str.split(',') if sn.strip()]
#
#                 if len(serial_numbers_list) != int(quantity):
#                     flash(f'Number of serial numbers ({len(serial_numbers_list)}) must match quantity ({int(quantity)})', 'error')
#                     return render_template('direct_inventory_transfer/create.html')
#
#                 serial_numbers_json = json.dumps(serial_numbers_list)
#
#             elif is_batch_managed:
#                 if not batch_number:
#                     flash('Batch number is required for batch-managed items', 'error')
#                     return render_template('direct_inventory_transfer/create.html')
#
#             transfer = DirectInventoryTransfer(
#                 transfer_number=transfer_number,
#                 user_id=current_user.id,
#                 from_warehouse=from_warehouse,
#                 to_warehouse=to_warehouse,
#                 from_bin=from_bin,
#                 to_bin=to_bin,
#                 notes=notes,
#                 status='draft'
#             )
#
#             db.session.add(transfer)
#             db.session.flush()
#
#             if is_serial_managed:
#                 serial_numbers_list = [sn.strip() for sn in serial_numbers_str.split(',') if sn.strip()]
#                 for serial in serial_numbers_list:
#                     transfer_item = DirectInventoryTransferItem(
#                         direct_inventory_transfer_id=transfer.id,
#                         item_code=validation_result.get('item_code'),
#                         item_description=validation_result.get('item_description'),
#                         barcode=item_code,
#                         item_type=item_type_validated,
#                         quantity=1.0,
#                         from_warehouse_code=from_warehouse,
#                         to_warehouse_code=to_warehouse,
#                         from_bin_code=from_bin,
#                         to_bin_code=to_bin,
#                         batch_number=None,
#                         serial_numbers=json.dumps([serial]),
#                         validation_status='validated',
#                         qc_status='pending'
#                     )
#                     db.session.add(transfer_item)
#             else:
#                 transfer_item = DirectInventoryTransferItem(
#                     direct_inventory_transfer_id=transfer.id,
#                     item_code=validation_result.get('item_code'),
#                     item_description=validation_result.get('item_description'),
#                     barcode=item_code,
#                     item_type=item_type_validated,
#                     quantity=quantity,
#                     from_warehouse_code=from_warehouse,
#                     to_warehouse_code=to_warehouse,
#                     from_bin_code=from_bin,
#                     to_bin_code=to_bin,
#                     batch_number=batch_number if is_batch_managed else None,
#                     serial_numbers=None,
#                     validation_status='validated',
#                     qc_status='pending'
#                 )
#                 db.session.add(transfer_item)
#
#             db.session.commit()
#
#             if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', ''):
#                 return redirect(url_for('direct_inventory_transfer.detail', transfer_id=transfer.id))
#
#             flash(f'Direct Inventory Transfer {transfer_number} created successfully with item {item_code}', 'success')
#             return redirect(url_for('direct_inventory_transfer.detail', transfer_id=transfer.id))
#
#         except Exception as e:
#             db.session.rollback()
#             logging.error(f"Error creating direct inventory transfer: {str(e)}")
#             flash(f'Error creating transfer: {str(e)}', 'error')
#             return render_template('direct_inventory_transfer/create.html')
#
#     return render_template('direct_inventory_transfer/create.html')


@direct_inventory_transfer_bp.route('/<int:transfer_id>', methods=['GET'])
@login_required
def detail(transfer_id):
    """Direct Inventory Transfer detail page"""
    transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)
    print("transfer->",transfer)
    if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager', 'qc']:
        flash('Access denied - You can only view your own transfers', 'error')
        return redirect(url_for('direct_inventory_transfer.index'))

    return render_template('direct_inventory_transfer/detail.html', transfer=transfer)



@direct_inventory_transfer_bp.route('/api/get-bin-code', methods=['GET'])
@login_required
def get_bin_code():
    """Get bin code by AbsEntry from SAP B1"""
    try:
        abs_entry = request.args.get('abs_entry')
        if not abs_entry:
            return jsonify({'success': False, 'error': 'AbsEntry is required'}), 400

        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        url = f"{sap.base_url}/b1s/v1/BinLocations({abs_entry})?$select=BinCode"
        response = sap.session.get(url, timeout=30)
        
        if response.status_code == 200:
            return jsonify({'success': True, 'value': [response.json()]})
        else:
            return jsonify({'success': False, 'error': f'SAP API error: {response.status_code}'}), 500
    except Exception as e:
        logging.error(f"Error fetching bin code: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@direct_inventory_transfer_bp.route('/api/get-warehouses', methods=['GET'])
@login_required
def get_warehouses():
    """Get warehouse list from SAP B1"""
    try:
        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        warehouses = sap.get_warehouses()
        return jsonify({'success': True, 'warehouses': warehouses})

    except Exception as e:
        logging.error(f"Error fetching warehouses: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/api/get-bins', methods=['GET'])
@login_required
def get_bins():
    """Get bin list for a warehouse from SAP B1"""
    try:
        warehouse_code = request.args.get('warehouse_code')
        
        if not warehouse_code:
            return jsonify({'success': False, 'error': 'Warehouse code is required'}), 400

        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        bins = sap.get_bins(warehouse_code)
        return jsonify({'success': True, 'bins': bins})

    except Exception as e:
        logging.error(f"Error fetching bins: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/api/get-bin-locations', methods=['GET'])
@login_required
def get_bin_locations():
    """Get bin locations for a warehouse using BinLocations API"""
    try:
        warehouse_code = request.args.get('warehouse_code')
        
        if not warehouse_code:
            return jsonify({'success': False, 'error': 'Warehouse code is required'}), 400

        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        # Use direct BinLocations API call
        try:
            url = f"{sap.base_url}/b1s/v1/BinLocations?$select=AbsEntry,BinCode,Warehouse&$filter=Warehouse eq '{warehouse_code}'"
            headers = {"Prefer": "odata.maxpagesize=0"}
            response = sap.session.get(url,headers=headers, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                bins = data.get('value', [])
                logging.info(f"✅ Retrieved {len(bins)} bin locations for warehouse {warehouse_code}")
                return jsonify({'success': True, 'bins': bins})
            else:
                logging.error(f"❌ Failed to get bin locations: {response.status_code} - {response.text}")
                return jsonify({'success': False, 'error': f'SAP API error: {response.status_code}'}), 500
                
        except Exception as api_error:
            logging.error(f"❌ Error calling BinLocations API: {str(api_error)}")
            return jsonify({'success': False, 'error': str(api_error)}), 500

    except Exception as e:
        logging.error(f"Error fetching bin locations: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/api/validate-item', methods=['POST'])
@login_required
def validate_item():
    """Validate item by barcode/item code and get serial/batch management info"""
    try:
        item_code = request.form.get('item_code', '').strip()
        
        if not item_code:
            return jsonify({'success': False, 'error': 'Item code is required'}), 400

        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        validation_result = sap.validate_item_for_direct_transfer(item_code)
        
        if not validation_result.get('valid'):
            return jsonify({
                'success': False,
                'error': validation_result.get('error', 'Item validation failed')
            }), 400

        return jsonify({
            'success': True,
            'item_code': validation_result.get('item_code'),
            'item_description': validation_result.get('item_description'),
            'item_type': validation_result.get('item_type'),  # 'serial', 'batch', or 'none'
            'is_serial_managed': validation_result.get('is_serial_managed'),
            'is_batch_managed': validation_result.get('is_batch_managed')
        })

    except Exception as e:
        logging.error(f"Error validating item: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/<int:transfer_id>/add_serial', methods=['POST'])
@login_required
def add_serial(transfer_id):
    """Add serial number to Direct Inventory Transfer - Step 2: Add serial numbers one by one"""
    try:
        transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)
        
        if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        if transfer.status != 'draft':
            return jsonify({'success': False, 'error': 'Cannot add serials to non-draft transfer'}), 400

        # -------------------------------
        # JSON OR FORM DETECTION
        # -------------------------------
        is_json_request = request.is_json or 'application/json' in request.headers.get('Content-Type', '')
        data = request.get_json() if is_json_request else request.form
        print("data/data-->",data)
        serial_number = (data.get('serial_number') or '').strip()

        if not serial_number:
            return jsonify({'success': False, 'error': 'Serial number is required'}), 400

        # -------------------------------
        # SAP VALIDATION
        # -------------------------------
        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        # Get serial number location and item details
        serial_location = sap.get_serial_current_location(serial_number)
        
        if not serial_location.get('success'):
            return jsonify({
                'success': False,
                'error': serial_location.get('error', 'Serial number not found or invalid')
            }), 400

        serial_data = serial_location.get('data', {})
        item_code = serial_data.get('ItemCode')
        
        if not item_code:
            return jsonify({'success': False, 'error': 'Could not determine item code for serial number'}), 400

        # Validate that serial is in the FROM warehouse
        current_warehouse = serial_data.get('WhsCode')
        if current_warehouse != transfer.from_warehouse:
            return jsonify({
                'success': False, 
                'error': f'Serial {serial_number} is in warehouse {current_warehouse}, but transfer is from {transfer.from_warehouse}'
            }), 400

        # Check if serial already exists in this transfer
        existing_item = DirectInventoryTransferItem.query.filter_by(
            direct_inventory_transfer_id=transfer.id,
            item_code=item_code
        ).first()

        if existing_item:
            # Check if serial already exists
            existing_serials = json.loads(existing_item.serial_numbers) if existing_item.serial_numbers else []
            if serial_number in existing_serials:
                return jsonify({'success': False, 'error': f'Serial {serial_number} already added to this transfer'}), 400
            
            # Add serial to existing item
            existing_serials.append(serial_number)
            existing_item.serial_numbers = json.dumps(existing_serials)
            existing_item.quantity = len(existing_serials)
            existing_item.updated_at = datetime.utcnow()
        else:
            # Create new item line
            transfer_item = DirectInventoryTransferItem(
                direct_inventory_transfer_id=transfer.id,
                item_code=item_code,
                item_description=serial_data.get('itemName', ''),
                barcode=item_code,
                item_type='serial',
                quantity=1,
                from_warehouse_code=transfer.from_warehouse,
                to_warehouse_code=transfer.to_warehouse,
                from_bin_code=transfer.from_bin,
                to_bin_code=transfer.to_bin,
                serial_numbers=json.dumps([serial_number]),
                validation_status='validated',
                qc_status='pending'
            )
            db.session.add(transfer_item)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': f'Serial {serial_number} added successfully',
            'item_code': item_code,
            'item_description': serial_data.get('itemName', ''),
            'current_location': f"{current_warehouse} - {serial_data.get('BinCode', 'No Bin')}"
        })

    except Exception as e:
        logging.error(f"Error adding serial: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/<int:transfer_id>/submit_for_qc', methods=['POST'])
@login_required
def submit_for_qc_approval(transfer_id):
    """Submit Direct Inventory Transfer for QC approval - Step 2 final action"""
    try:
        transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)

        if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        if transfer.status != 'draft':
            return jsonify({'success': False, 'error': 'Only draft transfers can be submitted for QC'}), 400

        if not transfer.items:
            return jsonify({'success': False, 'error': 'Cannot submit transfer without serial numbers'}), 400

        # Update status to submitted for QC approval
        transfer.status = 'submitted'
        transfer.submitted_at = datetime.utcnow()
        transfer.updated_at = datetime.utcnow()

        # Update all items to pending QC status
        for item in transfer.items:
            item.qc_status = 'pending'

        db.session.commit()

        logging.info(f"📤 Direct Inventory Transfer {transfer_id} submitted for QC approval")
        return jsonify({
            'success': True, 
            'message': f'Transfer {transfer.transfer_number} submitted for QC approval',
            'transfer_number': transfer.transfer_number,
            'items_count': len(transfer.items)
        })

    except Exception as e:
        logging.error(f"Error submitting transfer for QC: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/<int:transfer_id>/add_item', methods=['POST'])
@login_required
def add_item(transfer_id):
    """Add item to Direct Inventory Transfer with SAP validation"""
    try:
        transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)
        print("transfer_idtransfer_id---->",transfer)
        if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        if transfer.status != 'draft':
            return jsonify({'success': False, 'error': 'Cannot add items to non-draft transfer'}), 400

        item_code = request.form.get('item_code', '').strip()
        item_type = request.form.get('item_type', 'none')
        quantity = float(request.form.get('quantity', 1))
        serial_numbers_str = request.form.get('serial_numbers', '').strip()
        batch_number = request.form.get('batch_number', '').strip()

        if not item_code:
            return jsonify({'success': False, 'error': 'Item code is required'}), 400

        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        validation_result = sap.validate_item_for_direct_transfer(item_code)
        
        if not validation_result.get('valid'):
            return jsonify({
                'success': False,
                'error': validation_result.get('error', 'Item validation failed')
            }), 400

        item_type_validated = validation_result.get('item_type', 'none')
        is_serial_managed = validation_result.get('is_serial_managed', False)
        is_batch_managed = validation_result.get('is_batch_managed', False)

        if is_serial_managed:
            if not serial_numbers_str:
                return jsonify({'success': False, 'error': 'Serial numbers are required for serial-managed items'}), 400
            
            serial_numbers_list = [sn.strip() for sn in serial_numbers_str.split(',') if sn.strip()]
            
            if len(serial_numbers_list) != int(quantity):
                return jsonify({'success': False, 'error': f'Number of serial numbers ({len(serial_numbers_list)}) must match quantity ({int(quantity)})'}), 400
            
            # Check if an entry for this item already exists in this transfer
            transfer_item = DirectInventoryTransferItem.query.filter_by(
                direct_inventory_transfer_id=transfer.id,
                item_code=validation_result.get('item_code'),
                from_warehouse_code=transfer.from_warehouse,
                to_warehouse_code=transfer.to_warehouse,
                from_bin_code=transfer.from_bin,
                to_bin_code=transfer.to_bin
            ).first()

            if transfer_item:
                # Append serial numbers to existing line
                existing_serials = json.loads(transfer_item.serial_numbers) if transfer_item.serial_numbers else []
                # Filter out duplicates
                new_serials = [s for s in serial_numbers_list if s not in existing_serials]
                if not new_serials:
                    return jsonify({'success': False, 'error': 'All serial numbers already exist in this transfer'}), 400
                
                existing_serials.extend(new_serials)
                transfer_item.serial_numbers = json.dumps(existing_serials)
                transfer_item.quantity = float(len(existing_serials))
            else:
                # Create a new line with all serials
                transfer_item = DirectInventoryTransferItem(
                    direct_inventory_transfer_id=transfer.id,
                    item_code=validation_result.get('item_code'),
                    item_description=validation_result.get('item_description', ''),
                    barcode=item_code,
                    item_type=item_type_validated,
                    quantity=quantity,
                    from_warehouse_code=transfer.from_warehouse,
                    to_warehouse_code=transfer.to_warehouse,
                    from_bin_code=transfer.from_bin,
                    to_bin_code=transfer.to_bin,
                    batch_number=None,
                    serial_numbers=json.dumps(serial_numbers_list),
                    validation_status='validated'
                )
                db.session.add(transfer_item)
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'{len(serial_numbers_list)} serials added to the item line',
                'transfer_id': transfer.id
            })
        
        elif is_batch_managed:
            if not batch_number:
                return jsonify({'success': False, 'error': 'Batch number is required for batch-managed items'}), 400

            transfer_item = DirectInventoryTransferItem(
                direct_inventory_transfer_id=transfer.id,
                item_code=validation_result.get('item_code'),
                item_description=validation_result.get('item_description', ''),
                barcode=item_code,
                item_type=item_type_validated,
                quantity=quantity,
                from_warehouse_code=transfer.from_warehouse,
                to_warehouse_code=transfer.to_warehouse,
                from_bin_code=transfer.from_bin,
                to_bin_code=transfer.to_bin,
                batch_number=batch_number,
                serial_numbers=None,
                validation_status='validated'
            )
            db.session.add(transfer_item)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Batch {batch_number} added successfully'
            })
        
        else:
            # Non-serial, non-batch
            transfer_item = DirectInventoryTransferItem(
                direct_inventory_transfer_id=transfer.id,
                item_code=validation_result.get('item_code'),
                item_description=validation_result.get('item_description', ''),
                barcode=item_code,
                item_type=item_type_validated,
                quantity=quantity,
                from_warehouse_code=transfer.from_warehouse,
                to_warehouse_code=transfer.to_warehouse,
                from_bin_code=transfer.from_bin,
                to_bin_code=transfer.to_bin,
                batch_number=None,
                serial_numbers=None,
                validation_status='validated'
            )
            db.session.add(transfer_item)
            db.session.commit()

            return jsonify({
                'success': True,
                'message': f'Item {item_code} added successfully'
            })

    except Exception as e:
        logging.error(f"Error adding item: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/items/<int:item_id>/edit', methods=['POST'])
@login_required
def edit_item(item_id):
    """Edit item in transfer"""
    try:
        item = DirectInventoryTransferItem.query.get_or_404(item_id)
        transfer = item.direct_inventory_transfer

        if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        if transfer.status != 'draft':
            return jsonify({'success': False, 'error': 'Cannot edit items in non-draft transfer'}), 400

        quantity = float(request.form.get('quantity', item.quantity))
        serial_numbers_str = request.form.get('serial_numbers', '').strip()
        batch_number = request.form.get('batch_number', item.batch_number).strip()

        if item.item_type == 'serial':
            if not serial_numbers_str:
                return jsonify({'success': False, 'error': 'Serial numbers are required'}), 400
            serial_numbers_list = [sn.strip() for sn in serial_numbers_str.split(',') if sn.strip()]
            if len(serial_numbers_list) != int(quantity):
                return jsonify({'success': False, 'error': f'Number of serials ({len(serial_numbers_list)}) must match quantity ({int(quantity)})'}), 400
            item.serial_numbers = json.dumps(serial_numbers_list)
        
        elif item.item_type == 'batch':
            if not batch_number:
                return jsonify({'success': False, 'error': 'Batch number is required'}), 400
            item.batch_number = batch_number

        item.quantity = quantity
        db.session.commit()

        return jsonify({'success': True, 'message': 'Item updated successfully'})

    except Exception as e:
        logging.error(f"Error editing item: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/<int:transfer_id>/delete', methods=['POST'])
@login_required
def delete_transfer(transfer_id):
    """Delete the entire transfer"""
    try:
        transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)

        if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        if transfer.status != 'draft':
            return jsonify({'success': False, 'error': 'Only draft transfers can be deleted'}), 400

        db.session.delete(transfer)
        db.session.commit()

        return jsonify({'success': True, 'message': 'Transfer deleted successfully'})

    except Exception as e:
        logging.error(f"Error deleting transfer: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/items/<int:item_id>/delete', methods=['POST'])
@login_required
def delete_item(item_id):
    """Delete item from transfer"""
    try:
        item = DirectInventoryTransferItem.query.get_or_404(item_id)
        transfer = item.direct_inventory_transfer

        if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        if transfer.status != 'draft':
            return jsonify({'success': False, 'error': 'Cannot delete items from non-draft transfer'}), 400

        transfer_id = transfer.id
        item_code = item.item_code

        db.session.delete(item)
        db.session.commit()

        logging.info(f"🗑️ Item {item_code} deleted from transfer {transfer_id}")
        return jsonify({'success': True, 'message': f'Item {item_code} deleted'})

    except Exception as e:
        logging.error(f"Error deleting item: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/<int:transfer_id>/submit', methods=['POST'])
@login_required
def submit_transfer(transfer_id):
    """Submit Direct Inventory Transfer for QC approval"""
    try:
        transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)

        if transfer.user_id != current_user.id and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'Access denied'}), 403

        if transfer.status != 'draft':
            return jsonify({'success': False, 'error': 'Only draft transfers can be submitted'}), 400

        if not transfer.items:
            return jsonify({'success': False, 'error': 'Cannot submit transfer without items'}), 400

        transfer.status = 'submitted'
        transfer.updated_at = datetime.utcnow()

        db.session.commit()

        logging.info(f"📤 Direct Inventory Transfer {transfer_id} submitted for QC approval")
        return jsonify({'success': True, 'message': 'Transfer submitted for QC approval'})

    except Exception as e:
        logging.error(f"Error submitting transfer: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/<int:transfer_id>/qc_approve', methods=['POST'])
@login_required
def qc_approve_transfer(transfer_id):
    """QC approve Direct Inventory Transfer and post to SAP B1 (called from QC dashboard)"""
    try:
        transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)

        if not current_user.has_permission('qc_dashboard') and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'QC permissions required'}), 403

        if transfer.status != 'submitted':
            return jsonify({'success': False, 'error': 'Only submitted transfers can be approved'}), 400

        qc_notes = request.form.get('qc_notes', '')

        transfer.status = 'qc_approved'
        transfer.qc_approver_id = current_user.id
        transfer.qc_approved_at = datetime.utcnow()
        transfer.qc_notes = qc_notes
        transfer.updated_at = datetime.utcnow()

        for item in transfer.items:
            item.qc_status = 'approved'

        # Prepare multi-line SAP payload
        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            db.session.rollback()
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        # Group items by ItemCode to create proper transfer lines
        items_by_code = {}
        line_num = 0
        
        for item in transfer.items:
            item_code = item.item_code
            serial_numbers = json.loads(item.serial_numbers) if item.serial_numbers else []
            
            if item_code not in items_by_code:
                items_by_code[item_code] = {
                    "LineNum": line_num,
                    "ItemCode": item_code,
                    "Quantity": 0,
                    "WarehouseCode": item.to_warehouse_code,
                    "FromWarehouseCode": item.from_warehouse_code,
                    "SerialNumbers": [],
                    "BatchNumbers": [],
                    "StockTransferLinesBinAllocations": []
                }
                line_num += 1
            
            # Add serial numbers and update quantity
            for serial in serial_numbers:
                items_by_code[item_code]["SerialNumbers"].append({
                    "InternalSerialNumber": serial,
                    "Quantity": 1
                })
                items_by_code[item_code]["Quantity"] += 1

        # Construct the multi-line SAP payload
        sap_payload = {
            "DocDate": datetime.now().strftime('%Y-%m-%d'),
            "Comments": qc_notes or f"QC Approved WMS Transfer by {current_user.username}",
            "FromWarehouse": transfer.from_warehouse,
            "ToWarehouse": transfer.to_warehouse,
            #"BPLID": 5,  # Default branch, you may want to get this from transfer data
            "StockTransferLines": list(items_by_code.values())
        }

        logging.info(f"📤 Multi-line SAP payload for transfer {transfer_id} (QC approval):")
        logging.info(json.dumps(sap_payload, indent=2))

        sap_result = sap.create_stock_transfer(sap_payload)

        if not sap_result.get('success'):
            db.session.rollback()
            sap_error = sap_result.get('error', 'Unknown SAP error')
            logging.error(f"❌ SAP B1 posting failed: {sap_error}")
            return jsonify({'success': False, 'error': f'SAP B1 posting failed: {sap_error}'}), 500

        # Extract document number from SAP response
        sap_data = sap_result.get('data', {})
        doc_num = sap_data.get('DocNum') or sap_data.get('DocEntry', '')
        
        transfer.sap_document_number = str(doc_num)
        transfer.status = 'posted'
        
        db.session.commit()

        logging.info(f"✅ Direct Inventory Transfer {transfer_id} approved by {current_user.username}")
        return jsonify({
            'success': True,
            'message': f'Transfer {transfer.transfer_number} approved and posted to SAP B1',
            'sap_document_number': transfer.sap_document_number,
            'transfer_number': transfer.transfer_number
        })

    except Exception as e:
        logging.error(f"Error approving direct transfer: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/<int:transfer_id>/approve', methods=['POST'])
@login_required
def approve_transfer(transfer_id):
    """Approve Direct Inventory Transfer and post to SAP B1 with multi-line support"""
    try:
        transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)

        if not current_user.has_permission('qc_dashboard') and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'QC permissions required'}), 403

        if transfer.status != 'submitted':
            return jsonify({'success': False, 'error': 'Only submitted transfers can be approved'}), 400

        qc_notes = request.json.get('qc_notes', '') if request.is_json else request.form.get('qc_notes', '')

        transfer.status = 'qc_approved'
        transfer.qc_approver_id = current_user.id
        transfer.qc_approved_at = datetime.utcnow()
        transfer.qc_notes = qc_notes
        transfer.updated_at = datetime.utcnow()

        for item in transfer.items:
            item.qc_status = 'approved'

        # Prepare multi-line SAP payload
        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            db.session.rollback()
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500

        # Group items by ItemCode to create proper transfer lines
        items_by_code = {}
        line_num = 0
        
        for item in transfer.items:
            item_code = item.item_code
            serial_numbers = json.loads(item.serial_numbers) if item.serial_numbers else []
            
            if item_code not in items_by_code:
                items_by_code[item_code] = {
                    "LineNum": line_num,
                    "ItemCode": item_code,
                    "Quantity": 0,
                    "WarehouseCode": item.to_warehouse_code,
                    "FromWarehouseCode": item.from_warehouse_code,
                    "SerialNumbers": [],
                    "BatchNumbers": [],
                    "StockTransferLinesBinAllocations": []
                }
                line_num += 1
            
            # Add serial numbers and update quantity
            for serial in serial_numbers:
                items_by_code[item_code]["SerialNumbers"].append({
                    "InternalSerialNumber": serial,
                    "Quantity": 1
                })
                items_by_code[item_code]["Quantity"] += 1

        # Construct the multi-line SAP payload
        sap_payload = {
            "DocDate": datetime.now().strftime('%Y-%m-%d'),
            "Comments": qc_notes or f"QC Approved WMS Transfer by {current_user.username}",
            "FromWarehouse": transfer.from_warehouse,
            "ToWarehouse": transfer.to_warehouse,
            "BPLID": 5,  # Default branch, you may want to get this from transfer data
            "StockTransferLines": list(items_by_code.values())
        }

        logging.info(f"📤 Multi-line SAP payload for transfer {transfer_id}:")
        logging.info(json.dumps(sap_payload, indent=2))

        sap_result = sap.create_stock_transfer(sap_payload)

        if not sap_result.get('success'):
            db.session.rollback()
            sap_error = sap_result.get('error', 'Unknown SAP error')
            logging.error(f"❌ SAP B1 posting failed: {sap_error}")
            return jsonify({'success': False, 'error': f'SAP B1 posting failed: {sap_error}'}), 500

        # Extract document number from SAP response
        sap_data = sap_result.get('data', {})
        doc_num = sap_data.get('DocNum') or sap_data.get('DocEntry', '')
        
        transfer.sap_document_number = str(doc_num)
        transfer.status = 'posted'
        
        db.session.commit()

        logging.info(f"✅ Multi-line Direct Inventory Transfer {transfer_id} approved and posted to SAP B1 as {transfer.sap_document_number}")
        return jsonify({
            'success': True,
            'message': f'Multi-line transfer approved and posted to SAP B1 as {transfer.sap_document_number}',
            'sap_document_number': transfer.sap_document_number,
            'lines_count': len(items_by_code)
        })

    except Exception as e:
        logging.error(f"Error approving multi-line transfer: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/<int:transfer_id>/reject', methods=['POST'])
@login_required
def reject_transfer(transfer_id):
    """Reject Direct Inventory Transfer"""
    try:
        transfer = DirectInventoryTransfer.query.get_or_404(transfer_id)

        if not current_user.has_permission('qc_dashboard') and current_user.role not in ['admin', 'manager']:
            return jsonify({'success': False, 'error': 'QC permissions required'}), 403

        if transfer.status != 'submitted':
            return jsonify({'success': False, 'error': 'Only submitted transfers can be rejected'}), 400

        qc_notes = request.json.get('qc_notes', '') if request.is_json else request.form.get('qc_notes', '')
        
        if not qc_notes:
            return jsonify({'success': False, 'error': 'Rejection reason is required'}), 400

        transfer.status = 'rejected'
        transfer.qc_approver_id = current_user.id
        transfer.qc_approved_at = datetime.utcnow()
        transfer.qc_notes = qc_notes
        transfer.updated_at = datetime.utcnow()

        for item in transfer.items:
            item.qc_status = 'rejected'

        db.session.commit()

        logging.info(f"❌ Direct Inventory Transfer {transfer_id} rejected by {current_user.username}")
        return jsonify({'success': True, 'message': 'Transfer rejected by QC'})

    except Exception as e:
        logging.error(f"Error rejecting transfer: {str(e)}")
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/qr-scan', methods=['GET'])
@login_required
def qr_scan():
    """QR Code Scanning page for direct inventory transfer"""
    if not current_user.has_permission('direct_inventory_transfer'):
        flash('Access denied - Direct Inventory Transfer permissions required', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('direct_inventory_transfer.html')


@direct_inventory_transfer_bp.route('/api/decode-qr', methods=['POST'])
@login_required
def decode_qr():
    """Decode QR code JSON data"""
    try:
        data = request.get_json()
        qr_data_str = data.get('qr_data', '').strip()
        
        if not qr_data_str:
            return jsonify({'success': False, 'error': 'QR code data is required'}), 400
        
        qr_data = json.loads(qr_data_str)
        
        required_fields = ['item', 'qty']
        missing_fields = [field for field in required_fields if field not in qr_data]
        
        if missing_fields:
            return jsonify({
                'success': False, 
                'error': f'Missing required fields in QR code: {", ".join(missing_fields)}'
            }), 400
        
        return jsonify({
            'success': True,
            'item_code': qr_data.get('item'),
            'quantity': qr_data.get('qty'),
            'batch_number': qr_data.get('batch'),
            'po_number': qr_data.get('po'),
            'grn_id': qr_data.get('id'),
            'grn_date': qr_data.get('grn_date'),
            'exp_date': qr_data.get('exp_date'),
            'pack': qr_data.get('pack')
        })
        
    except json.JSONDecodeError as e:
        return jsonify({'success': False, 'error': f'Invalid QR code format: {str(e)}'}), 400
    except Exception as e:
        logging.error(f"Error decoding QR code: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/api/validate-item-code', methods=['POST'])
@login_required
def validate_item_code_api():
    """Validate item code and return details"""
    try:
        data = request.get_json()
        item_code = data.get('item_code', '').strip()
        
        if not item_code:
            return jsonify({'success': False, 'error': 'Item code is required'}), 400
        
        sap = SAPIntegration()
        validation_result = sap.validate_item_code(item_code)
        
        if not validation_result.get('success'):
            return jsonify({
                'success': False,
                'error': validation_result.get('error', 'Item validation failed')
            }), 404
        
        item_description = ''
        try:
            if sap.ensure_logged_in():
                url = f"{sap.base_url}/b1s/v1/Items('{item_code}')"
                response = sap.session.get(url, timeout=10)
                if response.status_code == 200:
                    item_data = response.json()
                    item_description = item_data.get('ItemName', '')
        except Exception as e:
            logging.warning(f"Could not fetch item description: {str(e)}")
        
        item_type = 'none'
        if validation_result.get('batch_required'):
            item_type = 'batch'
        elif validation_result.get('serial_required'):
            item_type = 'serial'
        
        return jsonify({
            'success': True,
            'item_code': item_code,
            'item_description': item_description,
            'item_type': item_type,
            'batch_required': validation_result.get('batch_required', False),
            'serial_required': validation_result.get('serial_required', False),
            'manage_method': validation_result.get('manage_method', 'N')
        })
        
    except Exception as e:
        logging.error(f"Error validating item code: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/api/submit-direct', methods=['POST'])
@login_required
def submit_direct_transfer():
    """Submit direct inventory transfer to SAP B1 immediately"""
    try:
        data = request.get_json()
        
        required_fields = ['from_warehouse', 'to_warehouse', 'item_code', 'quantity']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        transfer_number = f"DIT/{datetime.now().strftime('%Y%m%d')}/{DirectInventoryTransfer.query.count() + 1:010d}"
        
        transfer = DirectInventoryTransfer(
            transfer_number=transfer_number,
            user_id=current_user.id,
            from_warehouse=data.get('from_warehouse'),
            to_warehouse=data.get('to_warehouse'),
            from_bin=data.get('from_bin'),
            to_bin=data.get('to_bin'),
            notes=data.get('notes'),
            status='draft'
        )
        
        db.session.add(transfer)
        db.session.flush()
        
        transfer_item = DirectInventoryTransferItem(
            direct_inventory_transfer_id=transfer.id,
            item_code=data.get('item_code'),
            item_description=data.get('item_description'),
            quantity=float(data.get('quantity')),
            item_type=data.get('item_type'),
            from_warehouse_code=data.get('from_warehouse'),
            to_warehouse_code=data.get('to_warehouse'),
            from_bin_code=data.get('from_bin'),
            to_bin_code=data.get('to_bin'),
            batch_number=data.get('batch_number'),
            validation_status='validated'
        )
        
        db.session.add(transfer_item)
        db.session.commit()
        
        sap = SAPIntegration()
        sap_result = sap.create_stock_transfer_with_items(
            from_warehouse=data.get('from_warehouse'),
            to_warehouse=data.get('to_warehouse'),
            items=[{
                'item_code': data.get('item_code'),
                'quantity': float(data.get('quantity')),
                'from_bin': data.get('from_bin'),
                'to_bin': data.get('to_bin'),
                'batch_number': data.get('batch_number'),
                'item_description': data.get('item_description')
            }],
            comments=data.get('notes', f'Direct Transfer {transfer_number}')
        )
        
        if sap_result.get('success'):
            transfer.sap_document_number = str(sap_result.get('doc_num'))
            transfer.status = 'posted'
            db.session.commit()
            
            logging.info(f"✅ Direct transfer posted to SAP: {sap_result.get('doc_num')}")
            
            return jsonify({
                'success': True,
                'transfer_number': transfer_number,
                'sap_doc_number': sap_result.get('doc_num'),
                'message': 'Transfer posted successfully to SAP B1'
            })
        else:
            transfer.status = 'rejected'
            transfer.notes = f"SAP Error: {sap_result.get('error')}"
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': sap_result.get('error', 'Failed to post to SAP B1')
            }), 500
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error submitting direct transfer: {str(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/api/get-serial-location', methods=['GET'])
@login_required
def get_serial_location():
    """Get current location of a serial number"""
    try:
        serial_number = request.args.get('serial_number')
        print("Inventory serial_number",serial_number)
        if not serial_number:
            return jsonify({'success': False, 'error': 'Serial number required'}), 400
        
        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500
        
        result = sap.get_serial_current_location(serial_number)
        
        # Transform the result to match frontend expectations
        if result.get('success') and result.get('data'):
            return jsonify({
                'success': True,
                'value': [result['data']],  # Frontend expects array in 'value' field
                'bin_details': result.get('bin_details')
            })
        else:
            return jsonify(result)  # Return error as-is
            
    except Exception as e:
        logging.error(f"Error in get_serial_location API: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500



@direct_inventory_transfer_bp.route('/api/post-stock-transfer', methods=['POST'])
@login_required
def post_stock_transfer():
    """Post stock transfer directly to SAP B1 StockTransfers API"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['FromWarehouse', 'ToWarehouse', 'BPLID', 'StockTransferLines']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Validate StockTransferLines
        lines = data.get('StockTransferLines', [])
        if not lines:
            return jsonify({'success': False, 'error': 'No transfer lines provided'}), 400
        
        # Log the payload being sent
        logging.info(f"📤 Posting Stock Transfer to SAP B1:")
        logging.info(f"Payload: {json.dumps(data, indent=2)}")
        
        # Create transfer record in local database
        transfer_number = generate_direct_transfer_number()
        
        transfer = DirectInventoryTransfer(
            transfer_number=transfer_number,
            user_id=current_user.id,
            from_warehouse=data.get('FromWarehouse'),
            to_warehouse=data.get('ToWarehouse'),
            from_bin=data.get('from_bin_code', ''),
            to_bin=data.get('to_bin_code', ''),
            notes=data.get('Comments', ''),
            status='draft'
        )
        
        db.session.add(transfer)
        db.session.flush()
        
        # Create transfer item for each line
        for line in lines:
            serial_numbers = line.get('SerialNumbers', [])
            serial_numbers_json = json.dumps([sn.get('InternalSerialNumber') for sn in serial_numbers]) if serial_numbers else None
            
            transfer_item = DirectInventoryTransferItem(
                direct_inventory_transfer_id=transfer.id,
                item_code=line.get('ItemCode'),
                item_description=line.get('ItemDescription', ''),
                barcode=line.get('ItemCode'),
                item_type='serial' if serial_numbers else 'none',
                quantity=line.get('Quantity', 1),
                from_warehouse_code=data.get('FromWarehouse'),
                to_warehouse_code=data.get('ToWarehouse'),
                from_bin_code=data.get('from_bin_code', ''),
                to_bin_code=data.get('to_bin_code', ''),
                serial_numbers=serial_numbers_json,
                validation_status='validated',
                qc_status='approved'
            )
            
            db.session.add(transfer_item)
        
        # Post to SAP B1
        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            db.session.rollback()
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500
        
        # Send the exact payload to SAP B1
        sap_result = sap.create_stock_transfer(data)
        
        if sap_result.get('success'):
            # Extract document number from SAP response
            sap_data = sap_result.get('data', {})
            doc_num = sap_data.get('DocNum') or sap_data.get('DocEntry', '')
            
            transfer.sap_document_number = str(doc_num)
            transfer.status = 'posted'
            
            db.session.commit()
            
            logging.info(f"✅ Stock transfer posted to SAP B1: Document {doc_num}")
            
            return jsonify({
                'success': True,
                'transfer_number': transfer_number,
                'sap_doc_number': doc_num,
                'doc_num': doc_num,
                'message': 'Stock transfer posted successfully to SAP B1'
            })
        else:
            transfer.status = 'rejected'
            transfer.notes = f"SAP Error: {sap_result.get('error')}"
            db.session.commit()
            
            logging.error(f"❌ SAP B1 posting failed: {sap_result.get('error')}")
            return jsonify({
                'success': False,
                'error': sap_result.get('error', 'Failed to post to SAP B1')
            }), 500
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error posting stock transfer: {str(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/api/post-serial-stock-transfer', methods=['POST'])
@login_required
def post_serial_stock_transfer():
    """Post a serial-based stock transfer to SAP B1"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['from_warehouse', 'to_warehouse', 'item_code', 'serial_number', 'branch_id']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        # Create transfer record
        transfer_number = generate_direct_transfer_number()
        
        transfer = DirectInventoryTransfer(
            transfer_number=transfer_number,
            user_id=current_user.id,
            from_warehouse=data.get('from_warehouse'),
            to_warehouse=data.get('to_warehouse'),
            from_bin=data.get('from_bin_code', ''),
            to_bin=data.get('to_bin_code', ''),
            notes=data.get('comments', f'Serial-based transfer for {data.get("serial_number")}'),
            status='draft'
        )
        
        db.session.add(transfer)
        db.session.flush()
        
        # Create transfer item
        transfer_item = DirectInventoryTransferItem(
            direct_inventory_transfer_id=transfer.id,
            item_code=data.get('item_code'),
            item_description=data.get('item_name', ''),
            barcode=data.get('item_code'),
            item_type='serial',
            quantity=1,  # Serial items are always quantity 1
            from_warehouse_code=data.get('from_warehouse'),
            to_warehouse_code=data.get('to_warehouse'),
            from_bin_code=data.get('from_bin_code', ''),
            to_bin_code=data.get('to_bin_code', ''),
            serial_numbers=json.dumps([data.get('serial_number')]),
            validation_status='validated',
            qc_status='approved'  # Auto-approve for serial transfers
        )
        
        db.session.add(transfer_item)
        
        # Post to SAP B1
        sap = SAPIntegration()
        if not sap.ensure_logged_in():
            db.session.rollback()
            return jsonify({'success': False, 'error': 'SAP B1 authentication failed'}), 500
        
        # Prepare SAP payload according to the specification
        sap_payload = {
            "DocDate": datetime.now().strftime('%Y-%m-%d'),
            "Comments": data.get('comments', f'QC Approved WMS Transfer by {current_user.username}'),
            "FromWarehouse": data.get('from_warehouse'),
            "ToWarehouse": data.get('to_warehouse'),
            "BPLID": int(data.get('branch_id')),
            "StockTransferLines": [
                {
                    "LineNum": 0,
                    "ItemCode": data.get('item_code'),
                    "Quantity": 1,
                    "WarehouseCode": data.get('to_warehouse'),
                    "FromWarehouseCode": data.get('from_warehouse'),
                    "SerialNumbers": [
                        {
                            "InternalSerialNumber": data.get('serial_number'),
                            "Quantity": 1
                        }
                    ],
                    "BatchNumbers": [],
                    "StockTransferLinesBinAllocations": []
                }
            ]
        }
        
        sap_result = sap.create_stock_transfer(sap_payload)
        
        if sap_result.get('success'):
            # Extract document number from SAP response
            sap_data = sap_result.get('data', {})
            doc_num = sap_data.get('DocNum') or sap_data.get('DocEntry', '')
            
            transfer.sap_document_number = str(doc_num)
            transfer.status = 'posted'
            transfer_item.qc_status = 'approved'
            
            db.session.commit()
            
            logging.info(f"✅ Serial-based transfer posted to SAP: {doc_num}")
            
            return jsonify({
                'success': True,
                'transfer_number': transfer_number,
                'sap_doc_number': doc_num,
                'message': 'Serial-based transfer posted successfully to SAP B1'
            })
        else:
            transfer.status = 'rejected'
            transfer.notes = f"SAP Error: {sap_result.get('error')}"
            db.session.commit()
            
            return jsonify({
                'success': False,
                'error': sap_result.get('error', 'Failed to post to SAP B1')
            }), 500
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error posting serial stock transfer: {str(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/serial-transfer', methods=['GET'])
@login_required
def serial_transfer():
    """Serial Number Based Transfer page"""
    if not current_user.has_permission('direct_inventory_transfer'):
        flash('Access denied - Direct Inventory Transfer permissions required', 'error')
        return redirect(url_for('dashboard'))
    
    return render_template('direct_inventory_transfer/serial_transfer.html')


@direct_inventory_transfer_bp.route('/api/submit-for-qc', methods=['POST'])
@login_required
def submit_for_qc():
    """Submit multi-line transfer for QC approval"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['from_warehouse', 'to_warehouse', 'transfer_lines', 'bpl_id']
        missing_fields = [field for field in required_fields if not data.get(field)]
        
        if missing_fields:
            return jsonify({
                'success': False,
                'error': f'Missing required fields: {", ".join(missing_fields)}'
            }), 400
        
        transfer_lines = data.get('transfer_lines', [])
        if not transfer_lines:
            return jsonify({'success': False, 'error': 'No transfer lines provided'}), 400
        
        # Create transfer record
        transfer_number = generate_direct_transfer_number()
        
        transfer = DirectInventoryTransfer(
            transfer_number=transfer_number,
            user_id=current_user.id,
            from_warehouse=data.get('from_warehouse'),
            to_warehouse=data.get('to_warehouse'),
            from_bin=transfer_lines[0].get('from_bin', ''),
            to_bin=transfer_lines[0].get('to_bin', ''),
            notes=data.get('comments', f'Multi-line transfer for QC approval'),
            status='submitted'  # Directly set to submitted for QC approval
        )
        
        db.session.add(transfer)
        db.session.flush()
        
        # Create transfer items for each line
        for line_data in transfer_lines:
            serial_numbers_json = json.dumps([sn['InternalSerialNumber'] for sn in line_data.get('serial_numbers', [])])
            
            transfer_item = DirectInventoryTransferItem(
                direct_inventory_transfer_id=transfer.id,
                item_code=line_data.get('item_code'),
                item_description=line_data.get('item_description', ''),
                barcode=line_data.get('item_code'),
                item_type='serial',
                quantity=line_data.get('quantity', 1),
                from_warehouse_code=line_data.get('from_warehouse_code'),
                to_warehouse_code=line_data.get('warehouse_code'),
                from_bin_code=line_data.get('from_bin', ''),
                to_bin_code=line_data.get('to_bin', ''),
                serial_numbers=serial_numbers_json,
                validation_status='validated',
                qc_status='pending'  # Set to pending for QC approval
            )
            
            db.session.add(transfer_item)
        
        db.session.commit()
        
        logging.info(f"✅ Multi-line transfer {transfer_number} submitted for QC approval with {len(transfer_lines)} lines")
        
        return jsonify({
            'success': True,
            'transfer_number': transfer_number,
            'transfer_id': transfer.id,
            'message': f'Transfer {transfer_number} submitted for QC approval',
            'lines_count': len(transfer_lines)
        })
        
    except Exception as e:
        db.session.rollback()
        logging.error(f"Error submitting transfer for QC: {str(e)}")
        import traceback
        logging.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'success': False, 'error': str(e)}), 500


@direct_inventory_transfer_bp.route('/api/history', methods=['GET'])
@login_required
def get_transfer_history():
    """Get recent direct inventory transfers for current user"""
    try:
        transfers = DirectInventoryTransfer.query.filter_by(
            user_id=current_user.id
        ).order_by(
            DirectInventoryTransfer.created_at.desc()
        ).limit(20).all()
        
        transfer_list = []
        for transfer in transfers:
            item = transfer.items[0] if transfer.items else None
            
            transfer_list.append({
                'transfer_number': transfer.transfer_number,
                'item_code': item.item_code if item else 'N/A',
                'quantity': item.quantity if item else 0,
                'from_warehouse': transfer.from_warehouse,
                'to_warehouse': transfer.to_warehouse,
                'status': transfer.status,
                'sap_document_number': transfer.sap_document_number,
                'created_at': transfer.created_at.isoformat() if transfer.created_at else None
            })
        
        return jsonify({
            'success': True,
            'transfers': transfer_list
        })
        
    except Exception as e:
        logging.error(f"Error fetching transfer history: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
