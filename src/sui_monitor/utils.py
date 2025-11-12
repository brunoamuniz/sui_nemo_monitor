"""
Utility functions for SUI Monitor
"""

from datetime import datetime
from typing import Dict


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

