"""
MIMaaS Python API Client Configuration

Manages configuration loading from multiple sources with priority:
1. Explicit parameters (highest priority)
2. Environment variables
3. Config file (~/.mimaas/config.yaml)
4. Defaults (lowest priority)
"""

import os
import yaml
from pathlib import Path
from typing import Optional


class Config:
    """Configuration manager for MIMaaS API client"""

    # Defaults
    DEFAULT_API_URL = "https://www.mimaas.forschung.fau.de/api"
    DEFAULT_TOKEN_FILE = "~/.mimaas/token"
    DEFAULT_CONFIG_FILE = "~/.mimaas/config.yaml"
    DEFAULT_TIMEOUT = 120  # seconds

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        token_file: Optional[str] = None,
        timeout: Optional[int] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize configuration.

        Args:
            api_url: API server URL (overrides env var and config file)
            api_token: API token (overrides env var and token file)
            token_file: Path to token file (overrides default)
            timeout: Request timeout in seconds
            verify_ssl: Whether to verify SSL certificates
        """
        self.api_url = api_url or self._get_api_url()
        self.api_token = api_token or self._get_api_token(token_file)
        self.timeout = timeout or self._get_timeout()
        self.verify_ssl = verify_ssl
        self.token_file = Path(token_file).expanduser() if token_file else Path(self.DEFAULT_TOKEN_FILE).expanduser()

    def _get_api_url(self) -> str:
        """
        Get API URL from environment variable, config file, or default.

        Priority: env var > config file > default
        """
        # Check environment variable
        env_url = os.environ.get("MIMAAS_API_URL")
        if env_url:
            return env_url.rstrip('/')

        # Check config file
        config = self._read_config_file()
        if config and 'api_url' in config:
            return config['api_url'].rstrip('/')

        # Return default
        return self.DEFAULT_API_URL

    def _get_api_token(self, token_file: Optional[str] = None) -> Optional[str]:
        """
        Get API token from environment variable, token file, or config file.

        Priority: env var > token file > config file
        """
        # Check environment variable
        env_token = os.environ.get("MIMAAS_API_TOKEN")
        if env_token:
            return env_token

        # Check token file
        token_path = Path(token_file).expanduser() if token_file else Path(self.DEFAULT_TOKEN_FILE).expanduser()
        if token_path.exists():
            try:
                with open(token_path, 'r') as f:
                    token = f.read().strip()
                    if token:
                        return token
            except Exception:
                pass  # Fall through to config file

        # Check config file
        config = self._read_config_file()
        if config and 'api_token' in config:
            return config['api_token']

        return None

    def _get_timeout(self) -> int:
        """Get request timeout from environment variable, config file, or default"""
        # Check environment variable
        env_timeout = os.environ.get("MIMAAS_TIMEOUT")
        if env_timeout:
            try:
                return int(env_timeout)
            except ValueError:
                pass

        # Check config file
        config = self._read_config_file()
        if config and 'timeout' in config:
            return config['timeout']

        return self.DEFAULT_TIMEOUT

    def _read_config_file(self) -> Optional[dict]:
        """Read configuration from YAML file"""
        config_path = Path(self.DEFAULT_CONFIG_FILE).expanduser()
        if not config_path.exists():
            return None

        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception:
            return None

    def save_config(self, **kwargs) -> None:
        """
        Save configuration to config file.

        Args:
            **kwargs: Configuration key-value pairs to save
        """
        config_path = Path(self.DEFAULT_CONFIG_FILE).expanduser()
        config_path.parent.mkdir(parents=True, exist_ok=True)

        # Load existing config or create new
        existing_config = self._read_config_file() or {}

        # Update with new values
        existing_config.update(kwargs)

        # Write back to file
        with open(config_path, 'w') as f:
            yaml.dump(existing_config, f, default_flow_style=False)

        # Set restrictive permissions
        config_path.chmod(0o600)
