"""
MIMaaS Python API Client

Main client class for interacting with the MIMaaS REST API.
"""

import time
import requests
from pathlib import Path
from typing import List, Optional, Dict, Any

from .config import Config
from .models import User, Board, Request, Results, Plan
from .exceptions import (
    NetworkError,
    AuthenticationError,
    QuotaExceededError,
    ValidationError,
    ProcessingError,
    ResourceNotFoundError,
    TimeoutError as MIMaaSTimeoutError
)
from .auth import save_token, load_token


class MIMaaSClient:
    """
    MIMaaS API Client

    Example:
        client = MIMaaSClient()
        client.login("username", "password")
        request = client.submit_request("model.tflite", "nrf5340dk")
        results = client.wait_for_completion(request.id)
        print(results)
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        api_token: Optional[str] = None,
        token_file: Optional[str] = None,
        timeout: Optional[int] = None,
        verify_ssl: bool = True
    ):
        """
        Initialize MIMaaS API client.

        Args:
            api_url: API server URL (default: from env/config/localhost:5000)
            api_token: API token (default: from env/token file/config)
            token_file: Path to token file (default: ~/.mimaas/token)
            timeout: Request timeout in seconds (default: 120)
            verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.config = Config(
            api_url=api_url,
            api_token=api_token,
            token_file=token_file,
            timeout=timeout,
            verify_ssl=verify_ssl
        )

    def _make_request(
        self,
        method: str,
        endpoint: str,
        require_auth: bool = False,
        **kwargs
    ) -> requests.Response:
        """
        Make HTTP request to API with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., '/boards')
            require_auth: Whether authentication is required
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            NetworkError: Connection/network errors
            AuthenticationError: Auth errors
            Various MIMaaS exceptions based on response
        """
        url = f"{self.config.api_url}{endpoint}"

        # Add authentication header if required
        if require_auth:
            if not self.config.api_token:
                raise AuthenticationError(
                    "No API token found. Please login first or set MIMAAS_API_TOKEN environment variable."
                )
            kwargs.setdefault('headers', {})
            kwargs['headers']['Authorization'] = self.config.api_token

        # Set timeout
        kwargs.setdefault('timeout', self.config.timeout)

        # Set SSL verification
        kwargs['verify'] = self.config.verify_ssl

        try:
            response = requests.request(method, url, **kwargs)
            return self._handle_response(response)
        except requests.exceptions.ConnectionError as e:
            raise NetworkError(f"Failed to connect to {self.config.api_url}: {e}")
        except requests.exceptions.Timeout as e:
            raise NetworkError(f"Request timeout after {self.config.timeout}s: {e}")
        except requests.exceptions.RequestException as e:
            raise NetworkError(f"Request failed: {e}")

    def _handle_response(self, response: requests.Response) -> requests.Response:
        """
        Handle API response and convert to appropriate exceptions.

        Args:
            response: Response object

        Returns:
            Response object if successful

        Raises:
            Various MIMaaS exceptions based on status code
        """
        if response.status_code < 400:
            return response

        # Try to get error message from JSON
        try:
            error_data = response.json()
            error_message = error_data.get('message', response.text)
        except Exception:
            error_message = response.text or f"HTTP {response.status_code}"

        # Handle specific status codes
        if response.status_code == 401:
            raise AuthenticationError(error_message)
        elif response.status_code == 403:
            if "no available runs" in error_message.lower():
                raise QuotaExceededError()
            raise AuthenticationError(error_message)
        elif response.status_code == 404:
            raise ResourceNotFoundError(error_message)
        elif response.status_code == 400:
            raise ValidationError(error_message)
        elif response.status_code >= 500:
            raise NetworkError(f"Server error ({response.status_code}): {error_message}")
        else:
            raise NetworkError(f"HTTP {response.status_code}: {error_message}")

    # Authentication Methods

    def login(self, username: str, password: str, save: bool = True) -> str:
        """
        Login and retrieve API token.

        Args:
            username: Username
            password: Password
            save: Whether to save token to file (default: True)

        Returns:
            API token

        Raises:
            AuthenticationError: Invalid credentials
        """
        response = self._make_request(
            'POST',
            '/login',
            json={'username': username, 'password': password}
        )

        data = response.json()
        token = data['api_token']

        # Update config with new token
        self.config.api_token = token

        # Save token to file if requested
        if save:
            save_token(token, self.config.token_file)

        return token

    def register(
        self,
        username: str,
        email: str,
        first_name: str,
        surname: str,
        password: str,
        invite_token: str,
        plan: str = "free",
        save: bool = True
    ) -> str:
        """
        Register a new user account.

        Args:
            username: Unique username
            email: User's email address
            first_name: User's first name
            surname: User's surname/last name
            password: Account password
            invite_token: Single-use invite token provided by an admin
            plan: Subscription plan name (default: "free")
            save: Whether to save token to file (default: True)

        Returns:
            API token for the new user

        Raises:
            ValidationError: If user already exists, invalid plan, or invalid invite token
            NetworkError: If connection fails

        Example:
            >>> client = MIMaaSClient()
            >>> token = client.register(
            ...     username="johndoe",
            ...     email="john@example.com",
            ...     first_name="John",
            ...     surname="Doe",
            ...     password="secure_password",
            ...     invite_token="abc123..."
            ... )
            >>> print(f"Registered with token: {token[:16]}...")
        """
        response = self._make_request(
            'POST',
            '/register',
            json={
                'username': username,
                'email': email,
                'first_name': first_name,
                'surname': surname,
                'password': password,
                'invite_token': invite_token,
                'plan': plan
            }
        )

        data = response.json()
        token = data['api_token']

        # Update config with new token
        self.config.api_token = token

        # Save token to file if requested
        if save:
            save_token(token, self.config.token_file)

        return token

    def get_profile(self) -> User:
        """
        Get current user profile.

        Returns:
            User object

        Raises:
            AuthenticationError: Invalid or missing token
        """
        response = self._make_request('GET', '/me', require_auth=True)
        return User.from_dict(response.json())

    # Board Methods

    def list_boards(self) -> List[Board]:
        """
        List all available boards.

        Returns:
            List of Board objects
        """
        response = self._make_request('GET', '/boards')
        data = response.json()
        return [Board.from_dict(board) for board in data['boards']]

    def get_board(self, board_name: str) -> Board:
        """
        Get specific board details.

        Args:
            board_name: Board identifier (e.g., "nrf5340dk")

        Returns:
            Board object

        Raises:
            ResourceNotFoundError: Board not found
        """
        response = self._make_request('GET', f'/boards/{board_name}')
        return Board.from_dict(response.json())

    def get_board_status(self, board_name: str) -> Dict[str, Any]:
        """
        Get board availability status.

        Args:
            board_name: Board identifier

        Returns:
            Dictionary with status information
        """
        response = self._make_request('GET', f'/boards/{board_name}/status')
        return response.json()

    # Request Methods

    def submit_request(
        self,
        model_path: str,
        board: str,
        quantize: bool = False,
        build_mode: str = 'pristine'
    ) -> Request:
        """
        Submit model for evaluation.

        Args:
            model_path: Path to TFLite model file
            board: Board type (e.g., "nrf5340dk")
            quantize: Whether to quantize the model (default: False)
            build_mode: Build mode, 'pristine' or 'fast' (default: 'pristine')

        Returns:
            Request object

        Raises:
            QuotaExceededError: No available runs
            ValidationError: Invalid inputs
            FileNotFoundError: Model file not found
        """
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        with open(model_file, 'rb') as f:
            files = {'network': (model_file.name, f, 'application/octet-stream')}
            data = {
                'board': board,
                'quantize': str(quantize).lower(),
                'build_mode': build_mode
            }

            response = self._make_request(
                'POST',
                '/requests/',
                require_auth=True,
                files=files,
                data=data
            )

        return Request.from_dict(response.json())

    def update_request(
        self,
        request_id: int,
        board: Optional[str] = None,
        quantize: Optional[bool] = None,
        model_path: Optional[str] = None
    ) -> Request:
        """
        Update a pending request.

        Args:
            request_id: Request ID
            board: New board name (optional)
            quantize: New quantize setting (optional)
            model_path: Path to replacement TFLite model file (optional)

        Returns:
            Updated Request object

        Raises:
            ResourceNotFoundError: Request not found
        """
        data = {}
        if board is not None:
            data['board'] = board
        if quantize is not None:
            data['quantize'] = str(quantize).lower()

        files = None
        if model_path is not None:
            model_file = Path(model_path)
            if not model_file.exists():
                raise FileNotFoundError(f"Model file not found: {model_path}")
            files = {'network': (model_file.name, open(model_file, 'rb'), 'application/octet-stream')}

        try:
            response = self._make_request(
                'PATCH',
                f'/requests/{request_id}',
                require_auth=True,
                files=files,
                data=data if data else None
            )
        finally:
            if files:
                files['network'][1].close()

        return Request.from_dict(response.json())

    def get_request(self, request_id: int) -> Request:
        """
        Get request details.

        Args:
            request_id: Request ID

        Returns:
            Request object

        Raises:
            ResourceNotFoundError: Request not found
        """
        response = self._make_request('GET', f'/requests/{request_id}', require_auth=True)
        return Request.from_dict(response.json())

    def list_requests(
        self,
        status: Optional[str] = None,
        board: Optional[str] = None
    ) -> List[Request]:
        """
        List user's requests with optional filters.

        Args:
            status: Filter by status (pending/processing/done/error)
            board: Filter by board name

        Returns:
            List of Request objects
        """
        params = {}
        if status:
            params['status'] = status
        if board:
            params['board'] = board

        response = self._make_request(
            'GET',
            '/requests/',
            require_auth=True,
            params=params
        )
        return [Request.from_dict(req) for req in response.json()]

    def delete_request(self, request_id: int) -> bool:
        """
        Delete a request.

        Args:
            request_id: Request ID

        Returns:
            True if deleted successfully
        """
        self._make_request('DELETE', f'/requests/{request_id}', require_auth=True)
        return True

    def wait_for_completion(
        self,
        request_id: int,
        timeout: int = 600,
        poll_interval: int = 5
    ) -> Results:
        """
        Wait for request to complete (blocking).

        Args:
            request_id: Request ID
            timeout: Maximum time to wait in seconds (default: 600)
            poll_interval: Polling interval in seconds (default: 5)

        Returns:
            Results object

        Raises:
            TimeoutError: Request didn't complete within timeout
            ProcessingError: Request failed with error
        """
        start_time = time.time()

        while True:
            request = self.get_request(request_id)

            if request.is_successful:
                if request.results:
                    return request.results
                raise ProcessingError(message="Request completed but no results available")

            if request.has_error:
                raise ProcessingError(message=request.error_message or "Unknown error")

            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > timeout:
                raise MIMaaSTimeoutError(
                    f"Request {request_id} did not complete within {timeout}s (status: {request.status})"
                )

            # Wait before next poll
            time.sleep(poll_interval)

    # Artifact Download Methods

    def download_ram_report(self, request_id: int, output_path: str, use_server_folder: bool = False) -> None:
        """Download detailed RAM usage report (ram.json)"""
        self._download_artifact(request_id, 'ram_report', output_path, use_server_folder)

    def download_rom_report(self, request_id: int, output_path: str, use_server_folder: bool = False) -> None:
        """Download detailed ROM usage report (rom.json)"""
        self._download_artifact(request_id, 'rom_report', output_path, use_server_folder)

    def download_power_summary(self, request_id: int, output_path: str, use_server_folder: bool = False) -> None:
        """Download power measurement summary (ppk2_summary.csv)"""
        self._download_artifact(request_id, 'power_summary', output_path, use_server_folder)

    def download_power_samples(self, request_id: int, output_path: str, use_server_folder: bool = False) -> None:
        """Download raw power samples (ppk2_samples.csv - may be large)"""
        self._download_artifact(request_id, 'power_samples', output_path, use_server_folder)

    def download_model(self, request_id: int, output_path: str, use_server_folder: bool = False) -> None:
        """Download original TFLite model"""
        self._download_artifact(request_id, 'model', output_path, use_server_folder)

    def download_error_log(self, request_id: int, output_path: str, use_server_folder: bool = False) -> None:
        """Download error log (error.log) for failed requests"""
        self._download_artifact(request_id, 'error_log', output_path, use_server_folder)

    def download_all_artifacts(self, request_id: int, output_path: str, use_server_folder: bool = False) -> None:
        """Download all artifacts as zip file"""
        self._download_artifact(request_id, 'all', output_path, use_server_folder)

    def _download_artifact(
        self,
        request_id: int,
        artifact_type: str,
        output_path: str,
        use_server_folder: bool = False
    ) -> None:
        """
        Download specific artifact.

        Args:
            request_id: Request ID
            artifact_type: Type of artifact
            output_path: Where to save the file
            use_server_folder: If True, prepend the server folder name to the output path
        """
        # If use_server_folder, create downloads/<folder_name>/ structure
        if use_server_folder:
            request = self.get_request(request_id)
            if request.folder_name:
                output_dir = Path(output_path).parent
                output_filename = Path(output_path).name
                output_path = str(output_dir / "downloads" / request.folder_name / output_filename)

        response = self._make_request(
            'GET',
            f'/requests/{request_id}/artifacts/{artifact_type}',
            require_auth=True,
            stream=True
        )

        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)

        with open(output_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

    # Validation Methods

    def validate_model(self, model_path: str, board: str) -> Dict[str, Any]:
        """
        Validate model without submitting (doesn't consume runs).

        Args:
            model_path: Path to TFLite model
            board: Target board name

        Returns:
            Validation result dictionary with 'valid', 'errors', 'warnings'
        """
        model_file = Path(model_path)
        if not model_file.exists():
            raise FileNotFoundError(f"Model file not found: {model_path}")

        with open(model_file, 'rb') as f:
            files = {'network': (model_file.name, f, 'application/octet-stream')}
            data = {'board': board}

            response = self._make_request(
                'POST',
                '/validate',
                require_auth=True,
                files=files,
                data=data
            )

        return response.json()

    # Plans Methods

    def list_plans(self) -> List[Plan]:
        """
        List available subscription plans.

        Returns:
            List of Plan objects
        """
        response = self._make_request('GET', '/plans')
        data = response.json()
        return [Plan.from_dict(plan) for plan in data['plans']]
