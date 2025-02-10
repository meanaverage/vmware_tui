import requests
import time
import traceback
from typing import Optional
from vmware_manager.utils.logging import log_message
from vmware_manager.config.settings import (
    VMWARE_API_URL,
    VMWARE_USERNAME,
    VMWARE_PASSWORD,
    menu_lock
)

def vm_action(vm_id: str, action: str, force: bool = False, menu=None) -> bool:
    """
    Perform power action on VM with timeout and proper error handling.
    
    Args:
        vm_id: The ID of the VM
        action: The action to perform (start, stop, suspend)
        force: Whether to force the action
        menu: The VM menu instance for API message display
    
    Returns:
        bool: True if action was successful, False otherwise
    """
    try:
        # Map our action names to API expectations
        action_map = {
            "start": "on",
            "stop": "off",
            "shutdown": "shutdown",
            "suspend": "suspend"
        }
        
        api_action = action_map.get(action)
        if not api_action:
            # Use timeout to prevent deadlock
            if menu_lock.acquire(timeout=1.0):
                try:
                    log_message(f"Invalid power action requested: {action}", "ERROR")
                finally:
                    menu_lock.release()
            return False

        url = f"{VMWARE_API_URL}/{vm_id}/power"
        headers = {
            'Accept': 'application/vnd.vmware.vmw.rest-v1+json',
            'Content-Type': 'application/vnd.vmware.vmw.rest-v1+json'
        }
        
        # The API expects the operation directly in the body
        api_data = api_action
        
        # Log complete API request
        api_msg = [
            f"Request: PUT {url}",
            f"Headers: {headers}",
            f"Body: {api_data}"
        ]
        
        log_message(f"API Request details:")
        for msg in api_msg:
            log_message(msg)
            if menu:
                menu.add_api_message(msg)
        
        log_message(f"API CALL: PUT /vms/{vm_id}/power action={action} force={force}")
        response = requests.put(
            url,
            headers=headers,
            data=api_data,
            auth=(VMWARE_USERNAME, VMWARE_PASSWORD),
            verify=False,
            timeout=10
        )
        
        # Log API response
        response_msg = f"Response: {response.status_code} - {response.text if response.text else 'No content'}"
        log_message(f"API {response_msg}")
        if menu:
            menu.add_api_message(response_msg)
        
        # VMware API returns 204 for accepted requests
        if response.status_code in [200, 204]:  # Accept both success codes
            if menu_lock.acquire(timeout=1.0):
                try:
                    log_message(f"Power {action} request accepted by API")
                finally:
                    menu_lock.release()
            
            # Return True immediately for successful request
            # The background refresh will update the status
            return True
            
        if menu_lock.acquire(timeout=1.0):
            try:
                log_message(f"Failed to {action} VM. Status code: {response.status_code}", "ERROR")
            finally:
                menu_lock.release()
        return False

    except requests.Timeout:
        if menu_lock.acquire(timeout=1.0):
            try:
                log_message("Request timed out while attempting power action", "ERROR")
            finally:
                menu_lock.release()
        return False
    except requests.RequestException as e:
        if menu_lock.acquire(timeout=1.0):
            try:
                log_message(f"Network error during power action: {str(e)}", "ERROR")
            finally:
                menu_lock.release()
        return False
    except Exception as e:
        if menu_lock.acquire(timeout=1.0):
            try:
                log_message(f"Error during {action} operation: {str(e)}", "ERROR")
            finally:
                menu_lock.release()
        return False 