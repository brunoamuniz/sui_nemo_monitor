"""
Change detection for SUI Monitor
"""

import logging
from datetime import datetime
from typing import Dict, List
from .cache import CacheManager
from .telegram import TelegramNotifier
from .utils import format_timestamp, check_large_transfer

logger = logging.getLogger(__name__)


class ChangeDetector:
    """Detects changes in transactions by comparing with cache"""

    def __init__(self, cache_manager: CacheManager, telegram_notifier: TelegramNotifier):
        self.cache_manager = cache_manager
        self.telegram_notifier = telegram_notifier

    def detect_changes(self, protocol_name: str, current_transactions: List[Dict]) -> Dict:
        """Detect changes by comparing current transactions with cache"""
        cached_transactions = self.cache_manager.get_cached_transactions(protocol_name)

        changes = {
            "new_transactions": [],
            "large_transfers": [],
            "failed_transactions": [],
            "has_changes": False
        }

        if not cached_transactions:
            # First execution - all transactions are "new"
            changes["new_transactions"] = current_transactions
            changes["has_changes"] = True
            logger.info(
                f"First execution for {protocol_name} - {len(current_transactions)} transactions")
            return changes

        # Create set of transaction hashes from cache for fast comparison
        cached_hashes = {tx.get("digest", "") for tx in cached_transactions}
        current_hashes = {tx.get("digest", "") for tx in current_transactions}

        # Detect new transactions (that are in current but not in cache)
        new_hashes = current_hashes - cached_hashes

        if new_hashes:
            changes["has_changes"] = True
            logger.info(f"Found {len(new_hashes)} new transactions for {protocol_name}")

            # Find complete new transactions
            for tx in current_transactions:
                tx_hash = tx.get("digest", "")
                if tx_hash in new_hashes:
                    changes["new_transactions"].append(tx)

                    # Check if it's a large transfer
                    if self._is_large_transfer(tx):
                        changes["large_transfers"].append(tx)

                    # Check if it's a failed transaction
                    if not self._is_successful_transaction(tx):
                        changes["failed_transactions"].append(tx)

        return changes

    def _is_large_transfer(self, tx: Dict) -> bool:
        """Check if transaction contains large transfer"""
        large_transfers = self._check_large_transfer(tx)
        return len(large_transfers) > 0

    def _is_successful_transaction(self, tx: Dict) -> bool:
        """Check if transaction was successful"""
        return tx.get("effects", {}).get("status", {}).get("status") == "success"

    def send_notifications(self, protocol_name: str, changes: Dict):
        """Send notifications based on detected changes"""
        if not changes["has_changes"]:
            return

        # Notify large transfers
        for tx in changes["large_transfers"]:
            amount = self._extract_transfer_amount(tx)
            timestamp = format_timestamp(tx.get("timestampMs", 0))
            tx_hash = tx.get("digest", "")[:20] + "..."

            message = f"**Protocol:** {protocol_name.upper()}\n"
            message += f"**Type:** Large Transfer\n"
            message += f"**Value:** ${amount:,.2f} USDC\n"
            message += f"**Time:** {timestamp}\n"
            message += f"**Hash:** `{tx_hash}`"

            self.telegram_notifier.send_alert(message, "LARGE_TRANSFER")

        # Notify failed transactions
        for tx in changes["failed_transactions"]:
            timestamp = format_timestamp(tx.get("timestampMs", 0))
            tx_hash = tx.get("digest", "")[:20] + "..."

            message = f"**Protocol:** {protocol_name.upper()}\n"
            message += f"**Type:** Failed Transaction\n"
            message += f"**Time:** {timestamp}\n"
            message += f"**Hash:** `{tx_hash}`"

            self.telegram_notifier.send_alert(message, "FAILED_TRANSACTION")

        # Notify new activity (if there are new transactions)
        if changes["new_transactions"]:
            count = len(changes["new_transactions"])
            message = f"📈 **ACTIVITY DETECTED**\n\n"
            message += f"**Protocol:** {protocol_name.upper()}\n"
            message += f"**New transactions:** {count}\n"
            message += f"**Status:** Monitoring active"

            self.telegram_notifier.send_alert(message, "NEW_ACTIVITY")

    def _extract_transfer_amount(self, tx: Dict) -> float:
        """Extract transfer value in USD"""
        balance_changes = tx.get("balanceChanges", [])
        for change in balance_changes:
            if "usdc" in change.get("coinType", "").lower():
                amount = abs(int(change.get("amount", 0)))
                return amount / 1000000  # Convert from micro-USDC to USD
        return 0.0

    def _check_large_transfer(self, tx: Dict) -> Dict:
        """Check if transaction contains large transfers in any currency"""
        return check_large_transfer(tx)

