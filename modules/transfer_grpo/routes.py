from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required
import logging
from sap_integration import SAPIntegration

transfer_grpo_bp = Blueprint('transfer_grpo', __name__, template_folder='templates')
logger = logging.getLogger(__name__)

@transfer_grpo_bp.route('/')
@login_required
def index():
    return render_template('transfer_grpo/index.html')

@transfer_grpo_bp.route('/api/series', methods=['GET'])
@login_required
def get_series():
    sap = SAPIntegration()
    # Step 1: GET_GRPO_Series
    url = f"{sap.base_url}/b1s/v1/SQLQueries('GET_GRPO_Series')/List"
    response = sap.session.get(url, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch series"})

@transfer_grpo_bp.route('/api/documents/<series_id>', methods=['GET'])
@login_required
def get_documents(series_id):
    sap = SAPIntegration()
    # Step 2: GET_GRPO_DocEntry_By_Series
    url = f"{sap.base_url}/b1s/v1/SQLQueries('GET_GRPO_DocEntry_By_Series')/List"
    payload = {"ParamList": f"seriesID='{series_id}'"}
    response = sap.session.post(url, json=payload, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch documents"})

@transfer_grpo_bp.route('/api/grpo-details/<doc_entry>', methods=['GET'])
@login_required
def get_grpo_details(doc_entry):
    sap = SAPIntegration()
    # Step 3: Get GRPO Document Details using crossjoin
    url = f"{sap.base_url}/b1s/v1/$crossjoin(PurchaseDeliveryNotes,PurchaseDeliveryNotes/DocumentLines)?$expand=PurchaseDeliveryNotes($select=CardCode,CardName,DocumentStatus,DocNum,Series,DocDate,DocDueDate,DocTotal,DocEntry),PurchaseDeliveryNotes/DocumentLines($select=LineNum,ItemCode,ItemDescription,WarehouseCode,UnitsOfMeasurment,DocEntry,LineTotal,LineStatus,Quantity,Price,PriceAfterVAT)&$filter=PurchaseDeliveryNotes/DocEntry eq PurchaseDeliveryNotes/DocumentLines/DocEntry and PurchaseDeliveryNotes/DocEntry eq {doc_entry}"
    response = sap.session.get(url, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch GRPO details"})

@transfer_grpo_bp.route('/api/warehouses', methods=['GET'])
@login_required
def get_warehouses():
    sap = SAPIntegration()
    # Step 4: Get Warehouses
    url = f"{sap.base_url}/b1s/v1/Warehouses?$select=WarehouseName,WarehouseCode"
    response = sap.session.get(url, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch warehouses"})

@transfer_grpo_bp.route('/api/bin-locations/<wh_code>', methods=['GET'])
@login_required
def get_bins(wh_code):
    sap = SAPIntegration()
    # Step 5: Get Bin Locations
    url = f"{sap.base_url}/b1s/v1/BinLocations?$select=AbsEntry,BinCode,Warehouse&$filter=Warehouse eq '{wh_code}'"
    response = sap.session.get(url, timeout=30)
    return jsonify(response.json() if response.status_code == 200 else {"error": "Failed to fetch bins"})
