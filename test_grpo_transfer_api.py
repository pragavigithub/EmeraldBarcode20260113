#!/usr/bin/env python3
"""
GRPO Transfer Module - API Testing Script
Tests all API endpoints to verify they're working correctly
"""

import requests
import json
import sys
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:5000"
GRPO_TRANSFER_API = f"{BASE_URL}/grpo-transfer/api"

# Colors for terminal output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_header(text):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"{text}")
    print(f"{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✓ {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}✗ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ {text}{Colors.END}")

def test_series_list():
    """Test: Get Series List"""
    print_header("TEST 1: Get Series List")
    
    try:
        url = f"{GRPO_TRANSFER_API}/series-list"
        print_info(f"Endpoint: GET {url}")
        
        response = requests.get(url)
        print_info(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            series = data.get('series', [])
            if series:
                print_success(f"Found {len(series)} series")
                for s in series:
                    print(f"  - {s.get('SeriesName')} (ID: {s.get('SeriesID')})")
                return True, series
            else:
                print_warning("No series found (this might be OK if no GRPO series exist in SAP B1)")
                return True, []
        else:
            print_error(f"API returned error: {data.get('error', 'Unknown error')}")
            return False, None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False, None

def test_doc_numbers(series_id):
    """Test: Get Documents by Series"""
    print_header(f"TEST 2: Get Documents for Series {series_id}")
    
    try:
        url = f"{GRPO_TRANSFER_API}/doc-numbers/{series_id}"
        print_info(f"Endpoint: GET {url}")
        
        response = requests.get(url)
        print_info(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            docs = data.get('documents', [])
            if docs:
                print_success(f"Found {len(docs)} documents")
                for d in docs:
                    print(f"  - Doc #{d.get('DocNum')} (Entry: {d.get('DocEntry')}) - {d.get('CardName')}")
                return True, docs
            else:
                print_warning("No documents found for this series")
                return True, []
        else:
            print_error(f"API returned error: {data.get('error', 'Unknown error')}")
            return False, None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False, None

def test_validate_item(item_code):
    """Test: Validate Item"""
    print_header(f"TEST 3: Validate Item {item_code}")
    
    try:
        url = f"{GRPO_TRANSFER_API}/validate-item/{item_code}"
        print_info(f"Endpoint: GET {url}")
        
        response = requests.get(url)
        print_info(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            print_success(f"Item validated: {data.get('item_name')}")
            print(f"  - Batch Item: {data.get('is_batch_item')}")
            print(f"  - Serial Item: {data.get('is_serial_item')}")
            print(f"  - Non-Managed: {data.get('is_non_managed')}")
            return True, data
        else:
            print_error(f"API returned error: {data.get('error', 'Unknown error')}")
            return False, None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False, None

def test_batch_numbers(doc_entry):
    """Test: Get Batch Numbers"""
    print_header(f"TEST 4: Get Batch Numbers for Document {doc_entry}")
    
    try:
        url = f"{GRPO_TRANSFER_API}/batch-numbers/{doc_entry}"
        print_info(f"Endpoint: GET {url}")
        
        response = requests.get(url)
        print_info(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            batches = data.get('batches', [])
            if batches:
                print_success(f"Found {len(batches)} batch numbers")
                for b in batches:
                    print(f"  - {b.get('BatchNumber')} (Qty: {b.get('Quantity')})")
                return True, batches
            else:
                print_warning("No batch numbers found")
                return True, []
        else:
            print_error(f"API returned error: {data.get('error', 'Unknown error')}")
            return False, None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False, None

def test_warehouses():
    """Test: Get Warehouses"""
    print_header("TEST 5: Get Warehouses")
    
    try:
        url = f"{GRPO_TRANSFER_API}/warehouses"
        print_info(f"Endpoint: GET {url}")
        
        response = requests.get(url)
        print_info(f"Status Code: {response.status_code}")
        
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        if response.status_code == 200 and data.get('success'):
            warehouses = data.get('warehouses', [])
            if warehouses:
                print_success(f"Found {len(warehouses)} warehouses")
                for w in warehouses:
                    print(f"  - {w.get('WarehouseName')} ({w.get('WarehouseCode')})")
                return True, warehouses
            else:
                print_warning("No warehouses found")
                return True, []
        else:
            print_error(f"API returned error: {data.get('error', 'Unknown error')}")
            return False, None
            
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False, None

def main():
    """Run all tests"""
    print_header("GRPO Transfer Module - API Testing")
    print_info(f"Base URL: {BASE_URL}")
    print_info(f"Timestamp: {datetime.now().isoformat()}")
    
    # Test 1: Series List
    success1, series = test_series_list()
    
    if not success1:
        print_error("Series list test failed. Cannot continue with other tests.")
        sys.exit(1)
    
    if not series:
        print_warning("No series found. Skipping dependent tests.")
        print_header("SUMMARY")
        print_warning("No GRPO series configured in SAP B1")
        print_info("Please create at least one GRPO series in SAP B1 to test further")
        return
    
    # Test 2: Documents by Series
    series_id = series[0]['SeriesID']
    success2, docs = test_doc_numbers(series_id)
    
    if success2 and docs:
        # Test 3: Validate Item (if we have documents)
        doc_entry = docs[0]['DocEntry']
        
        # For item validation, we need an actual item code
        # This is optional - skip if no documents
        print_warning("Skipping item validation test (requires specific item code)")
        
        # Test 4: Batch Numbers
        test_batch_numbers(doc_entry)
    
    # Test 5: Warehouses
    test_warehouses()
    
    # Summary
    print_header("SUMMARY")
    print_success("API testing completed")
    print_info("Check results above for any failures")

if __name__ == '__main__':
    main()
