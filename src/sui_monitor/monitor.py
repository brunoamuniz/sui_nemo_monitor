"""
Main monitoring class for SUI Monitor
"""

import requests
import time
import logging
from datetime import datetime
from typing import Dict, List

from .config import load_config
from .cache import CacheManager
from .telegram import TelegramNotifier
from .detector import ChangeDetector
from .utils import (
    format_timestamp, 
    extract_transaction_value, 
    check_large_transfer,
    extract_package_changes,
    extract_created_objects,
    is_package_transaction
)

logger = logging.getLogger(__name__)


class SuiProtocolMonitor:
    """Main monitoring class for Sui blockchain protocols"""

    def __init__(self):
        """Initialize monitor with configuration"""
        self.config = load_config()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'SuiProtocolMonitor/1.0'
        })

        # Initialize system components
        self.cache_manager = CacheManager(self.config.get("cache", {}))
        self.telegram_notifier = TelegramNotifier(self.config.get("telegram", {}))
        self.change_detector = ChangeDetector(self.cache_manager, self.telegram_notifier)

        # Connect to Telegram on initialization
        self._initialize_telegram()
        
        # Check last package on startup if account monitoring is enabled
        if self.config.get("account_monitoring", {}).get("enabled", False):
            self._check_last_package_on_startup()

    def _initialize_telegram(self):
        """Initialize Telegram and send startup message"""
        if not self.telegram_notifier.enabled:
            return

        try:
            # Send simplified startup message
            startup_message = f"🚀 **SUI MONITOR ACTIVE**\n\n"
            startup_message += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            startup_message += f"🔍 {', '.join(self.config['protocols'].keys()).upper()}\n"
            startup_message += f"⏰ Every {self.config['monitoring']['check_interval_minutes']} min"

            self.telegram_notifier.send_alert(startup_message, "STARTUP")
            logger.info("Startup message sent to Telegram")

        except Exception as e:
            logger.error(f"Error initializing Telegram: {e}")
            logger.info("Continuing without Telegram notifications")

    def get_recent_transactions(self, package_id: str, limit: int = 50) -> List[Dict]:
        """Fetch recent transactions for a specific package"""
        try:
            # Using Sui RPC to fetch transactions
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "suix_queryTransactionBlocks",
                "params": [
                    {
                        "filter": {
                            "MoveFunction": {
                                "package": package_id
                            }
                        },
                        "options": {
                            "showInput": True,
                            "showEffects": True,
                            "showEvents": True,
                            "showObjectChanges": True,
                            "showBalanceChanges": True
                        }
                    },
                    None,  # cursor
                    limit,
                    True   # descending order
                ]
            }

            response = self.session.post(
                self.config["sui_rpc_url"],
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if "result" in result:
                return result["result"]["data"]
            else:
                logger.error(f"Error in RPC response: {result}")
                return []

        except Exception as e:
            logger.error(f"Error fetching transactions for {package_id}: {e}")
            return []

    def get_account_transactions(self, account_address: str, limit: int = 50) -> List[Dict]:
        """Fetch recent transactions from a specific account address"""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "suix_queryTransactionBlocks",
                "params": [
                    {
                        "filter": {
                            "FromAddress": account_address
                        },
                        "options": {
                            "showInput": True,
                            "showEffects": True,
                            "showEvents": True,
                            "showObjectChanges": True,
                            "showBalanceChanges": True
                        }
                    },
                    None,  # cursor
                    limit,
                    True   # descending order
                ]
            }

            response = self.session.post(
                self.config["sui_rpc_url"],
                json=payload,
                timeout=30
            )
            response.raise_for_status()

            result = response.json()
            if "result" in result:
                return result["result"]["data"]
            else:
                logger.error(f"Error in RPC response: {result}")
                return []

        except Exception as e:
            logger.error(f"Error fetching transactions for account {account_address}: {e}")
            return []

    def _check_last_package_on_startup(self):
        """Check if last reported package is in cache, if not, notify again"""
        account_config = self.config.get("account_monitoring", {})
        account_address = account_config.get("address", "")
        
        if not account_address:
            logger.info("Account monitoring enabled but no address configured")
            return
        
        try:
            logger.info(f"Checking last package for account {account_address[:20]}... on startup")
            last_package = self.cache_manager.get_last_package(account_address)
            
            if last_package:
                package_id = last_package.get("package_id", "")
                logger.info(f"Found last reported package: {package_id[:20]}...")
                
                # Check if this package is still in the cached packages list
                cached_packages = self.cache_manager.get_cached_packages(account_address)
                logger.info(f"Found {len(cached_packages)} packages in cache")
                
                # Check if package is in cache
                package_in_cache = any(
                    pkg.get("package_id", "") == package_id 
                    for pkg in cached_packages
                )
                
                if not package_in_cache:
                    # Package not in cache, send notification again
                    logger.info(f"⚠️ Last reported package {package_id[:20]}... not in cache, sending notification again")
                    self._send_package_notification(last_package, account_address)
                    # Save back to cache
                    if last_package not in cached_packages:
                        cached_packages.append(last_package)
                        self.cache_manager.save_packages(account_address, cached_packages)
                        logger.info(f"Last package saved back to cache")
                else:
                    logger.info(f"✅ Last reported package {package_id[:20]}... is in cache")
            else:
                logger.info("No last package found in cache (first run or cache cleared)")
        except Exception as e:
            logger.error(f"Error checking last package on startup: {e}", exc_info=True)

    def _send_package_notification(self, package_info: Dict, account_address: str):
        """Send notification about package publish/upgrade"""
        package_type = package_info.get("type", "")
        package_id = package_info.get("package_id", "")
        timestamp = format_timestamp(package_info.get("timestamp", 0))
        tx_hash = package_info.get("transaction_digest", "")
        
        if package_type == "published":
            message = f"📦 **NEW PACKAGE PUBLISHED**\n\n"
            message += f"**Account:** `{account_address[:20]}...`\n"
            message += f"**Package ID:** `{package_id[:20]}...`\n"
            message += f"**Version:** {package_info.get('version', 'N/A')}\n"
            message += f"**Time:** {timestamp}\n"
            message += f"**Transaction:** `{tx_hash[:20]}...`"
        elif package_type == "upgraded":
            message = f"🔄 **PACKAGE UPGRADED**\n\n"
            message += f"**Account:** `{account_address[:20]}...`\n"
            message += f"**Package ID:** `{package_id[:20]}...`\n"
            prev_version = package_info.get("previous_version", "N/A")
            version = package_info.get("version", "N/A")
            message += f"**Version:** {prev_version} → {version}\n"
            message += f"**Time:** {timestamp}\n"
            message += f"**Transaction:** `{tx_hash[:20]}...`"
        else:
            return
        
        self.telegram_notifier.send_alert(message, "NEW_ACTIVITY")

    def _send_object_notification(self, object_info: Dict, account_address: str):
        """Send notification about new object created"""
        obj_id = object_info.get("object_id", "")
        object_type = object_info.get("object_type", "")
        timestamp = format_timestamp(object_info.get("timestamp", 0))
        tx_hash = object_info.get("transaction_digest", "")
        
        message = f"🆕 **NEW OBJECT CREATED**\n\n"
        message += f"**Account:** `{account_address[:20]}...`\n"
        message += f"**Object ID:** `{obj_id[:20]}...`\n"
        message += f"**Type:** {object_type}\n"
        message += f"**Time:** {timestamp}\n"
        message += f"**Transaction:** `{tx_hash[:20]}...`"
        
        self.telegram_notifier.send_alert(message, "NEW_ACTIVITY")

    def monitor_account(self, account_address: str) -> Dict:
        """Monitor account for package and object changes"""
        logger.info(f"Monitoring account: {account_address}")
        
        # Get account monitoring config
        account_config = self.config.get("account_monitoring", {})
        limit = account_config.get("max_transactions_per_check", 50)
        
        # Fetch recent transactions from account
        current_transactions = self.get_account_transactions(account_address, limit)
        
        if not current_transactions:
            logger.warning(f"No transactions found for account {account_address}")
            return {
                "packages_published": 0,
                "packages_upgraded": 0,
                "objects_created": 0,
                "has_changes": False
            }
        
        logger.info(f"Found {len(current_transactions)} transactions for account {account_address}")
        
        # Get cached packages and objects
        cached_packages = self.cache_manager.get_cached_packages(account_address)
        cached_objects = self.cache_manager.get_cached_objects(account_address)
        
        # Track changes
        new_packages = []
        upgraded_packages = []
        new_objects = []
        
        # Process transactions to find package and object changes
        for tx in current_transactions:
            # Check for package changes
            package_change = extract_package_changes(tx, account_address)
            if package_change:
                package_id = package_change.get("package_id", "")
                tx_digest = package_change.get("transaction_digest", "")
                
                # Check if this package is already in cache
                package_in_cache = any(
                    pkg.get("package_id", "") == package_id and 
                    pkg.get("transaction_digest", "") == tx_digest
                    for pkg in cached_packages
                )
                
                if not package_in_cache:
                    if package_change.get("type") == "published":
                        new_packages.append(package_change)
                        logger.info(f"New package published: {package_id}")
                    elif package_change.get("type") == "upgraded":
                        upgraded_packages.append(package_change)
                        logger.info(f"Package upgraded: {package_id}")
                    
                    # Add to cache
                    cached_packages.append(package_change)
                    # Save as last package
                    self.cache_manager.save_last_package(account_address, package_change)
            
            # Check for new objects created
            created_objects = extract_created_objects(tx, account_address)
            for obj_info in created_objects:
                obj_id = obj_info.get("object_id", "")
                tx_digest = obj_info.get("transaction_digest", "")
                
                # Check if this object is already in cache
                object_in_cache = any(
                    obj.get("object_id", "") == obj_id and
                    obj.get("transaction_digest", "") == tx_digest
                    for obj in cached_objects
                )
                
                if not object_in_cache:
                    new_objects.append(obj_info)
                    logger.info(f"New object created: {obj_id}")
                    cached_objects.append(obj_info)
        
        # Save updated cache
        if new_packages or upgraded_packages:
            self.cache_manager.save_packages(account_address, cached_packages)
        if new_objects:
            self.cache_manager.save_objects(account_address, cached_objects)
        
        # Send notifications
        for package in new_packages:
            self._send_package_notification(package, account_address)
        
        for package in upgraded_packages:
            self._send_package_notification(package, account_address)
        
        for obj_info in new_objects:
            self._send_object_notification(obj_info, account_address)
        
        # Update last check time
        self.cache_manager.save_last_check_time_account(account_address, datetime.now())
        
        has_changes = len(new_packages) > 0 or len(upgraded_packages) > 0 or len(new_objects) > 0
        
        return {
            "packages_published": len(new_packages),
            "packages_upgraded": len(upgraded_packages),
            "objects_created": len(new_objects),
            "has_changes": has_changes
        }

    def analyze_transaction(self, tx: Dict) -> Dict:
        """Analyze a transaction and extract relevant information"""
        analysis = {
            "digest": tx.get("digest", ""),
            "timestamp": tx.get("timestampMs", 0),
            "success": tx.get("effects", {}).get("status", {}).get("status") == "success",
            "gas_used": tx.get("effects", {}).get("gasUsed", {}).get("computationCost", 0),
            "balance_changes": [],
            "events": [],
            "large_transfers": []
        }

        # Analyze balance changes
        balance_changes = tx.get("balanceChanges", [])
        for change in balance_changes:
            amount = abs(int(change.get("amount", 0)))
            if amount > 0:
                analysis["balance_changes"].append({
                    "owner": change.get("owner", {}).get("AddressOwner", ""),
                    "coin_type": change.get("coinType", ""),
                    "amount": amount
                })

                # Detect large transfers (assuming USDC = $1)
                if "usdc" in change.get("coinType", "").lower() and amount > self.config["monitoring"]["large_transfer_threshold_usd"] * 1000000:
                    analysis["large_transfers"].append({
                        "amount_usd": amount / 1000000,
                        "coin_type": change.get("coinType", ""),
                        "owner": change.get("owner", {}).get("AddressOwner", ""),
                        "timestamp": analysis["timestamp"]
                    })

        # Analyze events
        events = tx.get("events", [])
        for event in events:
            analysis["events"].append({
                "type": event.get("type", ""),
                "package_id": event.get("packageId", ""),
                "module": event.get("transactionModule", ""),
                "sender": event.get("sender", "")
            })

        return analysis

    def check_protocol_health(self, protocol_name: str, protocol_config: Dict) -> Dict:
        """Check health of a specific protocol"""
        logger.info(f"Checking health for protocol: {protocol_name}")

        package_id = protocol_config["package_id"]
        transactions = self.get_recent_transactions(package_id)

        logger.info(f"Found {len(transactions)} transactions for protocol {protocol_name}")

        health_report = {
            "protocol": protocol_name,
            "package_id": package_id,
            "timestamp": datetime.now().isoformat(),
            "total_transactions": len(transactions),
            "successful_transactions": 0,
            "failed_transactions": 0,
            "large_transfers": [],
            "suspicious_activity": [],
            "last_activity": None
        }

        for tx in transactions:
            analysis = self.analyze_transaction(tx)

            # Convert timestamp to readable date/time
            try:
                timestamp = analysis["timestamp"]
                if timestamp and str(timestamp).isdigit() and int(timestamp) > 0:
                    # timestampMs is already in milliseconds, so divide by 1000 for seconds
                    tx_datetime = datetime.fromtimestamp(
                        int(timestamp) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                else:
                    tx_datetime = "No timestamp"
            except (ValueError, TypeError, OSError) as e:
                tx_datetime = f"Error: {str(e)[:20]}"
            tx_digest = analysis["digest"][:12] + "..." if len(analysis["digest"]) > 12 else analysis["digest"]

            # Log processed transaction
            logger.info(
                f"Processing transaction {tx_digest} at {tx_datetime} - Success: {analysis['success']}")

            if analysis["success"]:
                health_report["successful_transactions"] += 1
            else:
                health_report["failed_transactions"] += 1
                health_report["suspicious_activity"].append({
                    "digest": analysis["digest"],
                    "reason": "Transaction failed",
                    "timestamp": analysis["timestamp"]
                })
                logger.warning(f"Failed transaction detected: {tx_digest} at {tx_datetime}")

            # Add large transfers
            if analysis["large_transfers"]:
                for transfer in analysis["large_transfers"]:
                    logger.info(
                        f"Large transfer detected: ${transfer['amount_usd']:,.2f} {transfer['coin_type']} at {tx_datetime}")

            health_report["large_transfers"].extend(analysis["large_transfers"])

            # Update last activity
            if not health_report["last_activity"] or analysis["timestamp"] > health_report["last_activity"]:
                health_report["last_activity"] = analysis["timestamp"]

        # Calculate success rate
        if health_report["total_transactions"] > 0:
            health_report["success_rate"] = health_report["successful_transactions"] / health_report["total_transactions"]
        else:
            health_report["success_rate"] = 0

        return health_report

    def _log_latest_transactions(self, protocol_name: str, transactions: List[Dict]):
        """Log latest transactions for monitoring verification"""
        if not transactions:
            return

        logger.info(f"=== LATEST TRANSACTIONS - {protocol_name.upper()} ===")
        logger.info(f"Total transactions found: {len(transactions)}")

        # Log the 5 most recent transactions
        for i, tx in enumerate(transactions[:5]):
            tx_hash = tx.get("digest", "")
            timestamp = format_timestamp(tx.get("timestampMs", 0))
            success = tx.get("effects", {}).get("status", {}).get("status") == "success"
            status_emoji = "SUCCESS" if success else "FAILED"

            # Check if it's a large transfer
            large_transfers = check_large_transfer(tx)
            if large_transfers:
                transfer_info = " | LARGE TRANSFER: "
                for coin, amount in large_transfers.items():
                    if coin == "USDC":
                        transfer_info += f"${amount:.2f} {coin} "
                    else:
                        transfer_info += f"{amount:.6f} {coin} "
            else:
                transfer_info = ""

            logger.info(f"  {i+1}. {status_emoji} {tx_hash} | {timestamp}{transfer_info}")

        # Log the most recent transaction with more details
        if transactions:
            latest_tx = transactions[0]
            latest_hash = latest_tx.get("digest", "")
            latest_timestamp = format_timestamp(latest_tx.get("timestampMs", 0))
            latest_success = latest_tx.get("effects", {}).get("status", {}).get("status") == "success"
            latest_status = "SUCCESS" if latest_success else "FAILED"

            logger.info(f"LATEST TRANSACTION: {latest_hash} | {latest_timestamp} | {latest_status}")

            # If it's a large transfer, show details
            latest_large_transfers = check_large_transfer(latest_tx)
            if latest_large_transfers:
                for coin, amount in latest_large_transfers.items():
                    if coin == "USDC":
                        logger.info(f"LARGE TRANSFER DETECTED: ${amount:,.2f} {coin}")
                    else:
                        logger.info(f"LARGE TRANSFER DETECTED: {amount:,.6f} {coin}")

        logger.info(f"=== END TRANSACTIONS {protocol_name.upper()} ===\n")

    def _send_latest_transaction_notification(self, protocol_name: str, latest_tx: Dict):
        """Send notification of latest transaction via Telegram"""
        try:
            tx_hash = latest_tx.get("digest", "")
            timestamp = format_timestamp(latest_tx.get("timestampMs", 0))

            # Extract transaction values in all currencies
            transaction_values = extract_transaction_value(latest_tx)

            # Check if there are large transfers
            large_transfers = check_large_transfer(latest_tx)

            # Build value information
            value_info = ""
            if large_transfers:
                # Show large transfers
                for coin, amount in large_transfers.items():
                    if coin == "USDC":
                        value_info += f"\n🚨 **LARGE TRANSFER:** ${amount:,.2f} {coin}"
                    else:
                        value_info += f"\n🚨 **LARGE TRANSFER:** {amount:,.6f} {coin}"
            elif transaction_values:
                # Show normal values
                for coin, amount in transaction_values.items():
                    if coin == "USDC":
                        value_info += f"\n💰 **{coin}:** ${amount:,.2f}"
                    else:
                        value_info += f"\n💰 **{coin}:** {amount:,.6f}"
            else:
                value_info = f"\n💰 **Value:** No currency movement"

            message = f"🆕 **NEW TRANSACTION DETECTED**\n\n"
            message += f"**Protocol:** {protocol_name.upper()}\n"
            message += f"**Hash:** {tx_hash}\n"
            message += f"**Time:** {timestamp}{value_info}\n\n"
            message += f"🕐 **Monitored at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

            self.telegram_notifier.send_alert(message, "INFO")

        except Exception as e:
            logger.error(f"Error sending latest transaction notification: {e}")

    def generate_report(self, health_reports: List[Dict]) -> str:
        """Generate health report for protocols"""
        report = f"=== Sui Protocol Health Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n\n"

        for health in health_reports:
            report += f"Protocol: {health['protocol'].upper()}\n"
            report += f"Package ID: {health['package_id']}\n"
            report += f"Total Transactions: {health['total_transactions']}\n"
            report += f"Success Rate: {health['success_rate']:.2%}\n"
            report += f"Large Transfers: {len(health['large_transfers'])}\n"

            if health['large_transfers']:
                report += "  Large Transfers Detected:\n"
                for transfer in health['large_transfers'][:5]:  # Top 5
                    # Convert timestamp to readable date/time
                    try:
                        if transfer.get('timestamp') and str(transfer['timestamp']).isdigit() and int(transfer['timestamp']) > 0:
                            transfer_datetime = datetime.fromtimestamp(
                                int(transfer['timestamp']) / 1000).strftime('%Y-%m-%d %H:%M:%S')
                        else:
                            transfer_datetime = "No timestamp"
                    except (ValueError, TypeError, OSError):
                        transfer_datetime = "Timestamp error"

                    report += f"    - ${transfer['amount_usd']:,.2f} ({transfer['coin_type']}) at {transfer_datetime}\n"

            if health['suspicious_activity']:
                report += f"  Suspicious Activity: {len(health['suspicious_activity'])} failed transactions\n"

            if health['last_activity']:
                try:
                    if isinstance(health['last_activity'], str):
                        last_activity = datetime.fromisoformat(
                            health['last_activity'].replace('Z', '+00:00'))
                    else:
                        last_activity = datetime.fromtimestamp(
                            health['last_activity'] / 1000)
                    report += f"  Last Activity: {last_activity.strftime('%Y-%m-%d %H:%M:%S')}\n"
                except Exception as e:
                    report += f"  Last Activity: {health['last_activity']}\n"

            report += "\n" + "="*50 + "\n\n"

        return report

    def run_monitoring_cycle(self):
        """Execute a complete monitoring cycle based on changes"""
        logger.info("Starting monitoring cycle")

        changes_detected = 0
        protocols_checked = 0

        for protocol_name, protocol_config in self.config["protocols"].items():
            try:
                protocols_checked += 1
                logger.info(f"Checking protocol: {protocol_name}")

                # Fetch current transactions
                package_id = protocol_config["package_id"]
                current_transactions = self.get_recent_transactions(package_id)

                if not current_transactions:
                    logger.warning(f"No transactions found for {protocol_name}")
                    continue

                # ALWAYS log latest transactions for verification
                self._log_latest_transactions(protocol_name, current_transactions)

                # Detect changes by comparing with cache
                changes = self.change_detector.detect_changes(protocol_name, current_transactions)

                if changes["has_changes"]:
                    changes_detected += 1
                    logger.info(
                        f"Changes detected for {protocol_name}: {len(changes['new_transactions'])} new transactions")

                    # Send notification of latest new transaction
                    if changes["new_transactions"]:
                        # First new transaction (most recent)
                        latest_new_tx = changes["new_transactions"][0]
                        self._send_latest_transaction_notification(protocol_name, latest_new_tx)

                    # Send Telegram notifications for large transfers and failures
                    self.change_detector.send_notifications(protocol_name, changes)

                    # Update cache with current transactions
                    self.cache_manager.save_transactions(protocol_name, current_transactions)
                    self.cache_manager.save_last_check_time(protocol_name, datetime.now())
                else:
                    logger.info(f"No changes detected for {protocol_name}")
                    # Update only the last check timestamp
                    self.cache_manager.save_last_check_time(protocol_name, datetime.now())

            except Exception as e:
                logger.error(f"Error monitoring {protocol_name}: {e}")

        # Monitor account if enabled
        account_config = self.config.get("account_monitoring", {})
        if account_config.get("enabled", False):
            try:
                account_address = account_config.get("address", "")
                if account_address:
                    account_result = self.monitor_account(account_address)
                    
                    if account_result["has_changes"]:
                        changes_detected += 1
                        logger.info(
                            f"Account monitoring results: "
                            f"{account_result['packages_published']} packages published, "
                            f"{account_result['packages_upgraded']} packages upgraded, "
                            f"{account_result['objects_created']} objects created"
                        )
                    else:
                        logger.info("No changes detected for monitored account")
            except Exception as e:
                logger.error(f"Error monitoring account: {e}")

        logger.info(
            f"Monitoring cycle completed - {protocols_checked} protocols checked, {changes_detected} with changes")

        return {
            "protocols_checked": protocols_checked,
            "changes_detected": changes_detected,
            "timestamp": datetime.now().isoformat()
        }

    def run_continuous_monitoring(self):
        """Execute continuous monitoring"""
        logger.info("Starting continuous monitoring")
        interval = self.config["monitoring"]["check_interval_minutes"] * 60

        try:
            while True:
                try:
                    self.run_monitoring_cycle()
                    logger.info(f"Sleeping for {interval} seconds")
                    time.sleep(interval)
                except KeyboardInterrupt:
                    logger.info("Monitoring stopped by user")
                    break
                except Exception as e:
                    logger.error(f"Error in monitoring cycle: {e}")
                    time.sleep(60)  # Wait 1 minute before retrying
        finally:
            # Close cache when program ends
            self.cache_manager.close()

    def close(self):
        """Close monitor resources"""
        self.cache_manager.close()

