"""Authentication service for PyQt6 GUI."""

from __future__ import annotations

import base64
import logging
import pickle

import requests
from PyQt6.QtCore import QObject, pyqtSignal

from lms_client.auth import SessionAuth, UMUSessionAuth
from lms_client.client import LMSClient
from lms_client.endpoints import UserEndpoint

logger = logging.getLogger(__name__)


def serialize_session(session: requests.Session) -> str:
    """Serialize session cookies to a base64-encoded string."""
    cookies = session.cookies.get_dict()
    return base64.b64encode(pickle.dumps(cookies)).decode("ascii")


def deserialize_session(pickled: str) -> requests.Session:
    """Reconstruct a session from serialized cookies."""
    cookies = pickle.loads(base64.b64decode(pickled))
    session = requests.Session()
    for name, value in cookies.items():
        session.cookies.set(name, value)
    return session


class AuthService(QObject):
    """Manages UMU authentication state."""

    auth_changed = pyqtSignal(bool)  # is_authenticated

    def __init__(self) -> None:
        super().__init__()
        self._username: str = ""
        self._role_type: str = ""
        self._is_admin: bool = False
        self._serialized_session: str = ""
        self._client: LMSClient | None = None

    def login(self, username: str, password: str) -> tuple[bool, str]:
        """Authenticate with UMU. Returns (success, error_message)."""
        if not username or not password:
            return False, "账号和密码不能为空"

        auth = UMUSessionAuth(username=username, password=password)
        try:
            auth.login()
        except requests.ConnectionError:
            logger.warning("Login failed: network error")
            return False, "网络连接失败，请检查网络"
        except requests.Timeout:
            logger.warning("Login failed: timeout")
            return False, "连接超时，请重试"
        except Exception as exc:
            logger.warning("Login failed: %s", exc)
            return False, "账号或密码错误"

        # Check admin status and role type
        lms_client = LMSClient(auth=auth)
        try:
            user_endpoint = UserEndpoint(lms_client)
            is_admin = user_endpoint.is_admin(username)
            role_type = user_endpoint.get_role_type(username)
        except Exception as exc:
            logger.warning("Admin check failed: %s", exc)
            is_admin = False
            role_type = ""
        finally:
            lms_client.close()

        self._username = username
        self._role_type = role_type
        self._is_admin = is_admin
        self._serialized_session = serialize_session(auth.session)

        self.auth_changed.emit(True)
        return True, ""

    def logout(self) -> None:
        """Clear authentication state."""
        self._username = ""
        self._role_type = ""
        self._is_admin = False
        self._serialized_session = ""
        if self._client is not None:
            self._client.close()
            self._client = None
        self.auth_changed.emit(False)

    def is_authenticated(self) -> bool:
        return bool(self._serialized_session)

    def is_admin(self) -> bool:
        return self._is_admin

    def get_role_type(self) -> str:
        return self._role_type

    def get_username(self) -> str:
        return self._username

    def get_serialized_session(self) -> str:
        return self._serialized_session

    def get_client(self) -> LMSClient | None:
        """Get or create an LMSClient from the current session."""
        if not self._serialized_session:
            return None
        if self._client is not None:
            return self._client

        session = deserialize_session(self._serialized_session)
        auth = SessionAuth(session=session)
        self._client = LMSClient(auth=auth)
        return self._client

    def close_client(self) -> None:
        """Close the cached client."""
        if self._client is not None:
            self._client.close()
            self._client = None
