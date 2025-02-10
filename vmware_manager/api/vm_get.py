import requests
import json
import time
import os
import re
from typing import Optional, List, Dict
from ..utils.logging import log_message
from ..config.settings import (
    VMWARE_API_URL,
    VMWARE_USERNAME,
    VMWARE_PASSWORD,
    menu_lock
)

# Cache settings and variables
CACHE_TIMEOUT = 5  # Cache VM data for 5 seconds
vm_list_cache = []
last_refresh = 0
power_state_cache = {}
vm_details_cache = {}

def clean_vm_name(path: str) -> str:
    """Extract clean VM name from path."""
    match = re.search(r'Virtual Machines[/\\]([^/\\]+)[/\\][^/\\]+\.vmx$', path)
    if match:
        return match.group(1)
    return os.path.splitext(os.path.basename(path))[0]

def get_vm_list(force: bool = False) -> list:
    """Get list of VMs from API."""
    global vm_list_cache, last_refresh  # Declare globals
    
    if not force and vm_list_cache and time.time() - last_refresh < CACHE_TIMEOUT:
        return vm_list_cache
    
    try:
        log_message("API CALL: GET /vms (List VMs)")
        response = requests.get(
            f"{VMWARE_API_URL}",
            auth=(VMWARE_USERNAME, VMWARE_PASSWORD),
            verify=False
        )
        
        if response.status_code == 200:
            vm_list = []
            for vm in response.json():
                try:
                    vm_id = vm.get('id')
                    path = vm.get('path', '')
                    name = clean_vm_name(path)
                    
                    if vm_id:
                        # Get power state from power endpoint
                        power_state = get_vm_power_state(vm_id)
                        vm['name'] = name
                        vm['power_state'] = power_state
                        vm_list.append(vm)
                except Exception as e:
                    log_message(f"Error processing VM entry: {str(e)}", "ERROR")
                    continue
            
            vm_list_cache = vm_list
            last_refresh = time.time()
            return vm_list
    except Exception as e:
        log_message(f"Error getting VM list: {str(e)}", "ERROR")
    return []

def get_vm_power_state(vm_id: str) -> str:
    """Get power state of specific VM."""
    global power_state_cache  # Declare global
    current_time = time.time()
    
    # Return cached value if fresh
    if vm_id in power_state_cache:
        cache_time, state = power_state_cache[vm_id]
        if current_time - cache_time < CACHE_TIMEOUT:
            return state

    try:
        log_message(f"API CALL: GET /vms/{vm_id}/power (Get Power State)")
        response = requests.get(
            f"{VMWARE_API_URL}/{vm_id}/power",
            auth=(VMWARE_USERNAME, VMWARE_PASSWORD),
            verify=False
        )
        if response.ok:
            data = response.json()
            state = data.get('power_state', 'UNKNOWN')
            power_state_cache[vm_id] = (current_time, state)
            return state
        return 'UNKNOWN'
    except Exception as e:
        log_message(f"Error getting VM power state: {str(e)}", "ERROR")
        return 'UNKNOWN'

def get_vm_details(vm_id: str) -> Optional[Dict]:
    """Get detailed information about a VM."""
    try:
        log_message(f"API CALL: GET /vms/{vm_id} (Get VM Details)")
        response = requests.get(
            f"{VMWARE_API_URL}/{vm_id}",
            auth=(VMWARE_USERNAME, VMWARE_PASSWORD),
            verify=False
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        log_message(f"Failed to fetch VM details for {vm_id}: {str(e)}", "ERROR")
        return None 