"""
Utility functions for SUI Monitor
"""

from datetime import datetime
from typing import Dict, List, Optional


def format_timestamp(timestamp_ms) -> str:
    """Format timestamp to readable string"""
    try:
        if timestamp_ms:
            # Try different timestamp formats
            if isinstance(timestamp_ms, str) and timestamp_ms.isdigit():
                timestamp_ms = int(timestamp_ms)
            elif isinstance(timestamp_ms, (int, float)):
                pass
            else:
                return "Invalid format"

            if timestamp_ms > 0:
                # If timestamp appears to be in seconds (less than 1e12), convert to milliseconds
                if timestamp_ms < 1e12:
                    timestamp_ms = timestamp_ms * 1000

                dt = datetime.fromtimestamp(timestamp_ms / 1000)
                return dt.strftime('%Y-%m-%d %H:%M:%S')
    except (ValueError, TypeError, OSError) as e:
        return f"Error: {str(e)[:20]}"
    return "No timestamp"


def extract_transaction_value(tx: Dict) -> Dict:
    """Extract total transaction value in different currencies"""
    balance_changes = tx.get("balanceChanges", [])
    values = {}

    for change in balance_changes:
        coin_type = change.get("coinType", "").lower()
        amount = abs(int(change.get("amount", 0)))

        if amount > 0:
            if "usdc" in coin_type:
                # USDC: 6 decimals (micro-USDC)
                values["USDC"] = amount / 1000000
            elif "sui" in coin_type:
                # SUI: 9 decimals (MIST)
                values["SUI"] = amount / 1000000000
            elif "eth" in coin_type:
                # ETH: 18 decimals (wei)
                values["ETH"] = amount / 1000000000000000000
            elif "btc" in coin_type:
                # BTC: 8 decimals (satoshi)
                values["BTC"] = amount / 100000000
            else:
                # Other currencies - assume 6 decimals by default
                coin_name = coin_type.split("::")[-1] if "::" in coin_type else coin_type
                values[coin_name.upper()] = amount / 1000000

    return values


def check_large_transfer(tx: Dict) -> Dict:
    """Check if transaction contains large transfers in any currency"""
    balance_changes = tx.get("balanceChanges", [])
    large_transfers = {}

    for change in balance_changes:
        coin_type = change.get("coinType", "").lower()
        amount = abs(int(change.get("amount", 0)))

        if amount > 0:
            if "usdc" in coin_type:
                # USDC: $10k threshold
                usd_amount = amount / 1000000
                if usd_amount > 10000:
                    large_transfers["USDC"] = usd_amount
            elif "sui" in coin_type:
                # SUI: 1000 SUI threshold
                sui_amount = amount / 1000000000
                if sui_amount > 1000:
                    large_transfers["SUI"] = sui_amount
            elif "eth" in coin_type:
                # ETH: 1 ETH threshold
                eth_amount = amount / 1000000000000000000
                if eth_amount > 1:
                    large_transfers["ETH"] = eth_amount
            elif "btc" in coin_type:
                # BTC: 0.1 BTC threshold
                btc_amount = amount / 100000000
                if btc_amount > 0.1:
                    large_transfers["BTC"] = btc_amount

    return large_transfers


def extract_package_changes(tx: Dict, account_address: str) -> Optional[Dict]:
    """Extract package publish/upgrade information from transaction if from monitored account"""
    # Check if transaction is from the monitored account
    tx_sender = tx.get("transaction", {}).get("data", {}).get("sender", "")
    if tx_sender.lower() != account_address.lower():
        return None
    
    # Check transaction kind - package publish/upgrade transactions
    tx_kind = tx.get("transaction", {}).get("data", {}).get("transaction", {})
    tx_kind_name = list(tx_kind.keys())[0] if tx_kind else ""
    
    # Check object changes for published or upgraded packages
    object_changes = tx.get("objectChanges", [])
    
    # First, check for published packages
    for obj_change in object_changes:
        change_type = obj_change.get("type", "")
        
        if change_type == "published":
            # New package published
            package_id = obj_change.get("packageId", "")
            version = obj_change.get("version", "")
            
            return {
                "type": "published",
                "package_id": package_id,
                "version": version,
                "transaction_digest": tx.get("digest", ""),
                "timestamp": tx.get("timestampMs", 0),
                "sender": tx_sender
            }
    
    # Check for package upgrades
    # Upgrades can be detected by:
    # 1. Transaction kind is "upgrade" or "publish" (for upgrade)
    # 2. Object changes with type "mutated" and objectType containing "package"
    if tx_kind_name == "upgrade" or (tx_kind_name == "publish" and "upgrade" in str(tx_kind).lower()):
        for obj_change in object_changes:
            change_type = obj_change.get("type", "")
            object_type = obj_change.get("objectType", "")
            
            if change_type == "mutated" and "package" in object_type.lower():
                package_id = obj_change.get("objectId", "")
                version = obj_change.get("version", "")
                previous_version = obj_change.get("previousVersion", "")
                
                return {
                    "type": "upgraded",
                    "package_id": package_id,
                    "version": version,
                    "previous_version": previous_version,
                    "transaction_digest": tx.get("digest", ""),
                    "timestamp": tx.get("timestampMs", 0),
                    "sender": tx_sender
                }
    
    # Also check for mutated packages (alternative way upgrades might appear)
    for obj_change in object_changes:
        change_type = obj_change.get("type", "")
        object_type = obj_change.get("objectType", "")
        
        if change_type == "mutated" and "package" in object_type.lower():
            # Check if version changed (indicates upgrade)
            version = obj_change.get("version", "")
            previous_version = obj_change.get("previousVersion", "")
            
            if previous_version and version and previous_version != version:
                package_id = obj_change.get("objectId", "")
                
                return {
                    "type": "upgraded",
                    "package_id": package_id,
                    "version": version,
                    "previous_version": previous_version,
                    "transaction_digest": tx.get("digest", ""),
                    "timestamp": tx.get("timestampMs", 0),
                    "sender": tx_sender
                }
    
    return None


def extract_created_objects(tx: Dict, account_address: str) -> List[Dict]:
    """Extract objects created by the monitored account from transaction"""
    created_objects = []
    
    # Check if transaction is from the monitored account
    tx_sender = tx.get("transaction", {}).get("data", {}).get("sender", "")
    if tx_sender.lower() != account_address.lower():
        return created_objects
    
    # Check object changes for created objects
    object_changes = tx.get("objectChanges", [])
    
    for obj_change in object_changes:
        if obj_change.get("type") == "created":
            obj_id = obj_change.get("objectId", "")
            object_type = obj_change.get("objectType", "")
            version = obj_change.get("version", "")
            
            # Skip package objects (handled separately)
            if "package" not in object_type.lower():
                created_objects.append({
                    "object_id": obj_id,
                    "object_type": object_type,
                    "version": version,
                    "transaction_digest": tx.get("digest", ""),
                    "timestamp": tx.get("timestampMs", 0),
                    "sender": tx_sender
                })
    
    return created_objects


def is_package_transaction(tx: Dict) -> bool:
    """Check if transaction is related to package publish or upgrade"""
    object_changes = tx.get("objectChanges", [])
    
    for obj_change in object_changes:
        change_type = obj_change.get("type", "")
        if change_type == "published":
            return True
        elif change_type == "mutated":
            object_type = obj_change.get("objectType", "")
            if "package" in object_type.lower():
                return True
    
    return False

