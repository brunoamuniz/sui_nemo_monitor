"""
Telegram notification management for SUI Monitor
"""

import logging
import threading
import asyncio
from typing import Dict, Optional
from telethon import TelegramClient

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Manages Telegram notifications using personal API"""

    def __init__(self, telegram_config: Dict):
        self.enabled = telegram_config.get("enabled", False)
        self.api_id = telegram_config.get("api_id", "")
        self.api_hash = telegram_config.get("api_hash", "")
        self.phone = telegram_config.get("phone", "")
        self.session_name = telegram_config.get("session_name", "user_session")
        chat_id = telegram_config.get("chat_id", "")
        
        # Convert chat_id to int if it's a string representation of a number
        try:
            if chat_id and isinstance(chat_id, str):
                # Try to convert to int (for group/channel IDs like "-1002949141078")
                self.chat_id = int(chat_id) if chat_id.lstrip('-').isdigit() else chat_id
            else:
                self.chat_id = chat_id
        except (ValueError, AttributeError):
            self.chat_id = chat_id

        # Thread lock to prevent concurrent access to session file
        self._lock = threading.Lock()

        if self.enabled and self.api_id and self.api_hash and self.phone and self.chat_id:
            logger.info("Telegram configured successfully")
        else:
            self.enabled = False
            logger.warning("Telegram disabled - incomplete configuration")

    def send_alert(self, message: str, alert_type: str = "INFO"):
        """Send alert via Telegram - creates new client for each message"""
        if not self.enabled:
            logger.info(f"Telegram Alert (disabled): {message}")
            return False

        try:
            # Format message with emoji based on type
            emoji_map = {
                "LARGE_TRANSFER": "💰",
                "FAILED_TRANSACTION": "⚠️",
                "NEW_ACTIVITY": "🆕",
                "LOW_SUCCESS_RATE": "🔴",
                "INFO": "ℹ️",
                "STARTUP": "🚀",
                "CACHE_MISS": "🔍"
            }

            emoji = emoji_map.get(alert_type, "ℹ️")
            formatted_message = f"{emoji} **SUI MONITOR**\n\n{message}"

            logger.info(f"Attempting to send Telegram message: {alert_type}")

            # Use threading to execute async function with lock to prevent concurrent access
            result = [False]

            def send_async():
                # Use lock to prevent multiple clients from accessing session file simultaneously
                with self._lock:
                    loop = None
                    try:
                        # Create a new loop in the thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        result[0] = loop.run_until_complete(
                            self._send_telegram_notification(formatted_message))
                    except Exception as e:
                        logger.error(f"Error in Telegram thread: {e}")
                        result[0] = False
                    finally:
                        # Properly cleanup async tasks before closing loop
                        if loop and not loop.is_closed():
                            try:
                                # Cancel all pending tasks
                                pending = [t for t in asyncio.all_tasks(loop) if not t.done()]
                                if pending:
                                    for task in pending:
                                        task.cancel()
                                    # Wait for tasks to be cancelled (with timeout)
                                    try:
                                        loop.run_until_complete(
                                            asyncio.wait_for(
                                                asyncio.gather(*pending, return_exceptions=True),
                                                timeout=2.0
                                            ))
                                    except asyncio.TimeoutError:
                                        logger.debug("Some Telegram tasks didn't cancel in time")
                            except Exception as cleanup_error:
                                logger.debug(f"Error during cleanup: {cleanup_error}")
                            finally:
                                try:
                                    loop.close()
                                except Exception:
                                    pass

            # Execute in separate thread
            thread = threading.Thread(target=send_async, daemon=True)
            thread.start()
            thread.join(timeout=15)  # 15 second timeout

            if not thread.is_alive():
                if result[0]:
                    logger.info(f"Telegram alert sent successfully: {alert_type}")
                else:
                    logger.warning(f"Failed to send Telegram message: {alert_type}")
            else:
                logger.warning(f"Telegram send timeout after 15 seconds: {alert_type}")
                result[0] = False

            return result[0]

        except Exception as e:
            logger.error(f"Unexpected error sending Telegram: {e}")
            return False

    async def _send_telegram_notification(self, message):
        """Send notification to Telegram using the same logic as telegram_automation.py"""
        client = None
        try:
            # Create Telegram client
            client = TelegramClient(self.session_name, self.api_id, self.api_hash)
            await client.start(phone=self.phone)

            # Try to send message - handle both int and string chat_id
            try:
                await client.send_message(self.chat_id, message, parse_mode='markdown')
            except ValueError as ve:
                # If chat_id is not found, try to get the entity first
                logger.warning(f"Direct chat_id lookup failed: {ve}. Trying to resolve entity...")
                try:
                    # Try to get the entity by ID
                    entity = await client.get_entity(self.chat_id)
                    await client.send_message(entity, message, parse_mode='markdown')
                except Exception as e2:
                    logger.error(f"Error resolving chat entity: {e2}")
                    raise ve  # Re-raise original error

            logger.info("Notification sent to Telegram successfully!")
            return True

        except Exception as e:
            error_msg = str(e)
            if "Cannot find any entity" in error_msg:
                logger.error(f"Chat ID '{self.chat_id}' not found. Please verify:")
                logger.error("  1. The chat_id is correct")
                logger.error("  2. You have access to the chat/group/channel")
                logger.error("  3. The bot/user is a member of the group/channel")
            elif "database is locked" in error_msg.lower():
                logger.error("Telegram session database is locked. Another instance may be using it.")
            else:
                logger.error(f"Error sending notification to Telegram: {e}")
            return False
        finally:
            # Ensure client is properly disconnected
            if client:
                try:
                    await client.disconnect()
                except Exception as e:
                    logger.debug(f"Error disconnecting client: {e}")

