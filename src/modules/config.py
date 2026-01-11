import os
import json
from pathlib import Path
from modules.logger import get_logger

logger = get_logger(__name__)

# Support development mode: check for local config first, then system config
DEV_CONFIG_FILE = Path(__file__).parent.parent.parent / "config" / "zero2.conf"
SYSTEM_CONFIG_FILE = Path("/opt/zero2_controller/config/zero2.conf")

# Use local config if it exists (development), otherwise use system config
if DEV_CONFIG_FILE.exists() and os.environ.get("ZERO2_USE_SYSTEM_CONFIG") != "1":
    CONFIG_FILE = DEV_CONFIG_FILE
else:
    CONFIG_FILE = SYSTEM_CONFIG_FILE

# Default configuration values
DEFAULT_CONFIG = {
    # Feature Flags
    'ENABLE_LOW_BAT': True,
    'ENABLE_DISPLAY': True,
    'ENABLE_SSH_BT': True,
    'ENABLE_USB_OTG': True,
    'ENABLE_WIFI_HOTSPOT': True,

    # Power Management
    'POWER_GPIO_PIN': 25,
    'POWER_THRESHOLD': 30,  # Seconds low battery must persist before shutdown
    'POWER_WARNING_TIME': 30,  # Seconds to warn user before shutdown
    'POWER_NOTIFY_TERMINALS': True,  # Send wall messages to all terminals

    # Display Settings
    'DISPLAY_UPDATE_INTERVAL': 2,  # Seconds between display updates

    # Network Settings
    'BT_IP': '10.10.10.1',
    'USB_IP': '10.10.20.1',

    # Logging
    'LOG_LEVEL': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'LOG_FILE': '/var/log/zero2-controller.log',
    'LOG_MAX_BYTES': 10 * 1024 * 1024,  # 10 MB
    'LOG_BACKUP_COUNT': 5,
}

def read_config():
    """
    Read configuration from centralized config file.
    Falls back to defaults and environment variables.

    Returns:
        dict: Configuration dictionary
    """
    config = DEFAULT_CONFIG.copy()

    # Try reading from config file
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                file_config = {}

                # Support both JSON and key=value formats
                content = f.read().strip()
                if content.startswith('{'):
                    # JSON format
                    file_config = json.loads(content)
                else:
                    # Key=value format (backward compatible)
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and not line.startswith('#'):
                            if '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip()

                                # Try to parse as appropriate type
                                if value.lower() in ('true', '1', 'yes', 'on'):
                                    file_config[key] = True
                                elif value.lower() in ('false', '0', 'no', 'off'):
                                    file_config[key] = False
                                elif value.isdigit():
                                    file_config[key] = int(value)
                                else:
                                    file_config[key] = value

                # Merge file config into defaults
                for key, value in file_config.items():
                    if key in config:
                        # Type conversion for known keys
                        if isinstance(config[key], bool) and not isinstance(value, bool):
                            config[key] = str(value).lower() in ('true', '1', 'yes', 'on')
                        elif isinstance(config[key], int) and not isinstance(value, int):
                            try:
                                config[key] = int(value)
                            except (ValueError, TypeError):
                                logger.warning(f"Invalid integer value for {key}: {value}")
                        else:
                            config[key] = value
                    else:
                        config[key] = value

                logger.debug(f"Loaded config from {CONFIG_FILE}")
        except Exception as e:
            logger.warning(f"Failed to read config file: {e}")
    else:
        logger.info(f"Config file not found at {CONFIG_FILE}, using defaults")

    # Override with environment variables (for backward compatibility)
    for key in DEFAULT_CONFIG.keys():
        env_key = key
        if env_key in os.environ:
            value = os.environ[env_key]
            # Type conversion
            if isinstance(DEFAULT_CONFIG[key], bool):
                config[key] = value.lower() in ('true', '1', 'yes', 'on')
            elif isinstance(DEFAULT_CONFIG[key], int):
                try:
                    config[key] = int(value)
                except ValueError:
                    logger.warning(f"Invalid integer value for {key} in environment: {value}")
            else:
                config[key] = value
            logger.debug(f"Config {key} overridden by environment variable: {config[key]}")

    return config

def get_config(key, default=None):
    """
    Get a specific configuration value.

    Args:
        key: Configuration key
        default: Default value if key not found

    Returns:
        Configuration value or default
    """
    config = read_config()
    return config.get(key, default)
