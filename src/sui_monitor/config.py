"""
Configuration management for SUI Monitor
Loads configuration from .env file
"""

import os
import logging
from typing import Dict
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()


def load_config() -> Dict:
    """Load configuration from environment variables"""
    
    # Parse protocol configurations
    # Format: PROTOCOL_NAME_PACKAGE_ID, PROTOCOL_NAME_MODULES (comma-separated), PROTOCOL_NAME_ALERT_THRESHOLD
    protocols = {}
    
    # NEMO Protocol
    nemo_package_id = os.getenv("NEMO_PACKAGE_ID", "0x0f286ad004ea93ea6ad3a953b5d4f3c7306378b0dcc354c3f4ebb1d506d3b47f")
    nemo_modules = os.getenv("NEMO_MODULES", "market,py,yield_factory,sy").split(",")
    nemo_threshold = float(os.getenv("NEMO_ALERT_THRESHOLD_USD", "10000"))
    protocols["nemo"] = {
        "package_id": nemo_package_id,
        "modules": nemo_modules,
        "alert_threshold_usd": nemo_threshold
    }
    
    # SCALLOP Protocol
    scallop_package_id = os.getenv("SCALLOP_PACKAGE_ID", "0xee1ff66985a76b2c0170935fb29144b4007827ed2c4f3d6a1189578afb92bcdd")
    scallop_modules = os.getenv("SCALLOP_MODULES", "scallop").split(",")
    scallop_threshold = float(os.getenv("SCALLOP_ALERT_THRESHOLD_USD", "10000"))
    protocols["scallop"] = {
        "package_id": scallop_package_id,
        "modules": scallop_modules,
        "alert_threshold_usd": scallop_threshold
    }
    
    # Account monitoring configuration
    account_monitoring_enabled = os.getenv("ACCOUNT_MONITORING_ENABLED", "true").lower() == "true"
    account_monitoring_address = os.getenv("MONITORED_ACCOUNT_ADDRESS", "").strip()
    
    # Validate account monitoring configuration
    if account_monitoring_enabled and not account_monitoring_address:
        logger.warning("ACCOUNT_MONITORING_ENABLED is true but MONITORED_ACCOUNT_ADDRESS is not set. Disabling account monitoring.")
        account_monitoring_enabled = False
    
    account_monitoring = {
        "enabled": account_monitoring_enabled,
        "address": account_monitoring_address,
        "max_transactions_per_check": int(os.getenv("ACCOUNT_MAX_TRANSACTIONS_PER_CHECK", "50"))
    }
    
    config = {
        "sui_rpc_url": os.getenv("SUI_RPC_URL", "https://fullnode.mainnet.sui.io:443"),
        "protocols": protocols,
        "account_monitoring": account_monitoring,
        "monitoring": {
            "check_interval_minutes": int(os.getenv("CHECK_INTERVAL_MINUTES", "5")),
            "large_transfer_threshold_usd": float(os.getenv("LARGE_TRANSFER_THRESHOLD_USD", "10000")),
            "max_transactions_per_check": int(os.getenv("MAX_TRANSACTIONS_PER_CHECK", "50"))
        },
        "cache": {
            "enabled": os.getenv("CACHE_ENABLED", "true").lower() == "true",
            "max_transactions_per_protocol": int(os.getenv("MAX_TRANSACTIONS_PER_PROTOCOL", "50")),
            "cache_ttl_hours": int(os.getenv("CACHE_TTL_HOURS", "24")),
            "cache_directory": os.getenv("CACHE_DIRECTORY", "./cache")
        },
        "telegram": {
            "enabled": os.getenv("TELEGRAM_ENABLED", "true").lower() == "true",
            "api_id": os.getenv("TELEGRAM_API_ID", ""),
            "api_hash": os.getenv("TELEGRAM_API_HASH", ""),
            "phone": os.getenv("TELEGRAM_PHONE", ""),
            "session_name": os.getenv("TELEGRAM_SESSION_NAME", "user_session"),
            "chat_id": os.getenv("TELEGRAM_CHAT_ID", "")
        }
    }
    
    # Validate required Telegram settings if enabled
    if config["telegram"]["enabled"]:
        if not config["telegram"]["api_id"] or not config["telegram"]["api_hash"]:
            logger.warning("Telegram enabled but API credentials missing. Disabling Telegram.")
            config["telegram"]["enabled"] = False
        if not config["telegram"]["phone"] or not config["telegram"]["chat_id"]:
            logger.warning("Telegram enabled but phone or chat_id missing. Disabling Telegram.")
            config["telegram"]["enabled"] = False
    
    return config
