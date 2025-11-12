# SUI Monitor

A continuous monitoring system for Sui blockchain DeFi protocols with Telegram notifications. Monitor NEMO, SCALLOP, and other Sui protocols in real-time with intelligent change detection and large transfer alerts.

## 💡 Motivation

This project was created in response to the NEMO protocol security incident. After the hack, there was a critical need to monitor the protocol's on-chain activity to detect if any new transactions would be triggered, which could indicate further unauthorized access or asset movements.

The system was designed to:
- **Track protocol activity** in real-time to detect any suspicious transactions
- **Monitor asset movements** to identify potential unauthorized transfers
- **Provide immediate alerts** via Telegram when new transactions occur
- **Enable rapid response** to any suspicious activity on monitored protocols

By continuously monitoring transaction activity, users can stay informed about protocol state changes and react quickly to any unexpected behavior, making it an essential tool for post-incident monitoring and ongoing security surveillance.

## ✨ Features

- **Continuous Monitoring** - Monitor NEMO and SCALLOP protocols automatically
- **Telegram Notifications** - Real-time alerts for new transactions and large transfers
- **Smart Caching** - Prevents duplicate notifications using persistent cache
- **Large Transfer Detection** - Alerts for significant transfers in multiple currencies (USDC, SUI, ETH, BTC)
- **Detailed Logging** - Complete transaction hashes and timestamps
- **Modular Architecture** - Clean, maintainable codebase
- **Environment-based Configuration** - Secure configuration using `.env` files

## 📋 Prerequisites

- Python 3.8 or higher
- Telegram account (for notifications)
- Telegram API credentials (api_id, api_hash)

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/sui_monitor.git
cd sui_monitor
```

### 2. Install Dependencies

**Windows:**
```batch
install.bat
```

**Linux/macOS:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure Environment

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and fill in your configuration:
   ```bash
   # Required: Telegram API credentials
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   TELEGRAM_PHONE=+1234567890
   TELEGRAM_CHAT_ID=your_chat_id
   ```

### 4. Run the Monitor

**Single run:**
```bash
python main.py
```

**Continuous monitoring:**
```bash
python main.py --continuous
```

**Windows:**
```batch
startup.bat
```

## ⚙️ Configuration

All configuration is done through environment variables in the `.env` file. See `.env.example` for all available options.

### Required Settings

- `TELEGRAM_API_ID` - Your Telegram API ID
- `TELEGRAM_API_HASH` - Your Telegram API hash
- `TELEGRAM_PHONE` - Your phone number (with country code)
- `TELEGRAM_CHAT_ID` - Target chat ID for notifications

### Optional Settings

- `CHECK_INTERVAL_MINUTES` - Monitoring interval (default: 5 minutes)
- `LARGE_TRANSFER_THRESHOLD_USD` - Threshold for large transfer alerts (default: $10,000)
- `CACHE_TTL_HOURS` - Cache expiration time (default: 24 hours)

### 🔑 Getting Telegram API Credentials

1. Visit [https://my.telegram.org/](https://my.telegram.org/)
2. Log in with your phone number
3. Go to "API development tools"
4. Create a new application
5. Copy your `api_id` and `api_hash`
6. For `chat_id`, you can use a bot like [@userinfobot](https://t.me/userinfobot) to get your chat ID

## 📊 Notification Types

- **🚀 STARTUP** - System initialization
- **🆕 NEW TRANSACTION** - New transaction detected with full hash
- **📈 ACTIVITY DETECTED** - Activity summary
- **💰 LARGE TRANSFER** - Large transfers detected
- **⚠️ FAILED TRANSACTION** - Failed transactions

## 🎯 Monitored Currencies

The system automatically detects large transfers in:

- **USDC**: Threshold $10,000
- **SUI**: Threshold 1,000 SUI
- **ETH**: Threshold 1 ETH
- **BTC**: Threshold 0.1 BTC

Thresholds can be customized via environment variables.

## 📁 Project Structure

```
sui_monitor/
├── src/
│   └── sui_monitor/
│       ├── __init__.py          # Package initialization
│       ├── config.py            # Configuration management
│       ├── cache.py              # Cache manager
│       ├── telegram.py           # Telegram notifications
│       ├── detector.py           # Change detection
│       ├── monitor.py            # Main monitor class
│       └── utils.py              # Utility functions
├── main.py                       # Entry point
├── .env.example                  # Example environment file
├── requirements.txt              # Python dependencies
├── startup.bat                   # Windows startup script
├── install.bat                   # Windows installation script
├── README.md                     # This file
└── .gitignore                    # Git ignore rules
```

## 🐍 Virtual Environment

The project uses a Python virtual environment to:
- **Isolate dependencies** from system Python
- **Avoid conflicts** with other projects
- **Ensure compatibility** across different systems

### Managing Virtual Environment

**Windows:**
- Created automatically by `install.bat`
- Activated automatically by `startup.bat`

**Linux/macOS:**
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Deactivate virtual environment
deactivate
```

## 🔧 Usage Examples

### Single Monitoring Cycle

```bash
python main.py
```

### Continuous Monitoring

```bash
python main.py --continuous
```

### Stop Monitoring

Press `Ctrl+C` or:
```bash
pkill -f main.py
```

## 📝 Logging

The system generates detailed logs in `sui_monitor.log` including:
- Complete transaction hashes
- Human-readable timestamps
- Transaction status
- Large transfers detected
- Errors and warnings

## 🚨 Troubleshooting

### Connection Error with Sui RPC

- Check your internet connection
- The RPC endpoint may be temporarily unavailable
- Verify `SUI_RPC_URL` in your `.env` file

### Telegram Authentication Error

- Verify `TELEGRAM_API_ID`, `TELEGRAM_API_HASH`, and `TELEGRAM_PHONE` are correct
- Run the script once to generate the session file
- Check that your phone number includes country code (e.g., +1234567890)

### Cache Not Working

- Ensure the `cache/` directory exists
- Check write permissions for the cache directory
- Verify `CACHE_ENABLED=true` in your `.env` file

### Module Import Errors

- Ensure you're running from the project root directory
- Verify all dependencies are installed: `pip install -r requirements.txt`
- Check that the virtual environment is activated

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is open source and available under the [MIT License](LICENSE).

## 🙏 Acknowledgments

- Built for monitoring Sui blockchain DeFi protocols
- Uses [Telethon](https://github.com/LonamiWebs/Telethon) for Telegram integration
- Uses [DiskCache](https://github.com/grantjenks/python-diskcache) for persistent caching

## 📞 Support

For issues or questions:
1. Check the logs in `sui_monitor.log`
2. Verify all dependencies are installed
3. Ensure your `.env` file is configured correctly
4. Check that Telegram credentials are valid
5. Open an issue on GitHub

---

**Made with ❤️ for the Sui blockchain community**
