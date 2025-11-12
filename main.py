#!/usr/bin/env python3
"""
SUI Monitor - Main Entry Point
Continuous monitoring system for Sui blockchain DeFi protocols
"""

import sys
import logging
from src.sui_monitor.monitor import SuiProtocolMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sui_monitor.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main function"""
    monitor = SuiProtocolMonitor()

    try:
        # Execute single cycle or continuous
        if len(sys.argv) > 1 and sys.argv[1] == "--continuous":
            monitor.run_continuous_monitoring()
        else:
            result = monitor.run_monitoring_cycle()
            logger.info(f"Single cycle completed: {result}")
    except KeyboardInterrupt:
        logger.info("Program interrupted by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        monitor.close()


if __name__ == "__main__":
    main()

