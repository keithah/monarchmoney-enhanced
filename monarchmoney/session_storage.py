"""
Secure session storage for MonarchMoney Enhanced.

Replaces unsafe pickle usage with secure JSON storage with optional encryption.
"""

import base64
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from cryptography.fernet import Fernet

    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    # Create a placeholder for type hints when cryptography is not available
    Fernet = None

# Try to import logger from the package, fall back to basic logging
try:
    from .logging_config import logger
except ImportError:
    import logging

    logger = logging.getLogger(__name__)


class SecureSessionStorage:
    """
    Secure session storage that replaces unsafe pickle usage.

    Supports both encrypted and plain JSON storage modes:
    - Encrypted: Uses Fernet encryption with password-derived key
    - Plain JSON: Simple JSON storage (for non-sensitive session data)
    """

    def __init__(self, password: Optional[str] = None, use_encryption: bool = True):
        """
        Initialize secure session storage.

        Args:
            password: Password for encryption (required if use_encryption=True)
            use_encryption: Whether to encrypt session data
        """
        self.use_encryption = use_encryption and CRYPTOGRAPHY_AVAILABLE
        self.cipher = None

        if self.use_encryption:
            if not password:
                # Use a default password derived from system info
                # This is better than pickle but not as secure as user-provided password
                password = self._generate_default_password()
                logger.warning(
                    "Using default password for session encryption. "
                    "Consider providing explicit password for better security."
                )

            self.cipher = self._create_cipher(password)
        elif use_encryption and not CRYPTOGRAPHY_AVAILABLE:
            logger.warning(
                "Cryptography library not available. Falling back to plain JSON. "
                "Install 'cryptography' package for secure encrypted sessions."
            )

    def _generate_default_password(self) -> str:
        """Generate a default password from system characteristics."""
        import platform

        system_info = (
            f"{platform.node()}{platform.system()}{os.getenv('USER', 'default')}"
        )
        return hashlib.sha256(system_info.encode()).hexdigest()[:32]

    def _create_cipher(self, password: str) -> "Fernet":
        """Create Fernet cipher from password."""
        # Use PBKDF2 to derive key from password
        key = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            b"monarchmoney_salt_v1",  # Fixed salt for consistency
            100000,  # iterations
        )[
            :32
        ]  # Take first 32 bytes

        # Convert to base64 for Fernet
        fernet_key = base64.urlsafe_b64encode(key)
        return Fernet(fernet_key)

    def save_session(self, session_data: Dict[str, Any], session_file: str) -> None:
        """
        Save session data securely.

        Args:
            session_data: Session data to save
            session_file: Path to session file
        """
        try:
            # Ensure directory exists
            session_path = Path(session_file)
            session_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert session data to JSON
            json_data = json.dumps(session_data, indent=2)

            if self.use_encryption and self.cipher:
                # Encrypt the JSON data
                encrypted_data = self.cipher.encrypt(json_data.encode("utf-8"))

                # Save encrypted data as binary
                with open(session_file, "wb") as f:
                    f.write(encrypted_data)

                logger.debug("Session saved with encryption", session_file=session_file)
            else:
                # Save as plain JSON
                with open(session_file, "w", encoding="utf-8") as f:
                    f.write(json_data)

                logger.debug("Session saved as plain JSON", session_file=session_file)

        except Exception as e:
            logger.error(
                "Failed to save session", session_file=session_file, exc_info=e
            )
            raise

    def load_session(self, session_file: str) -> Dict[str, Any]:
        """
        Load session data securely.

        Args:
            session_file: Path to session file

        Returns:
            Session data dictionary

        Raises:
            FileNotFoundError: If session file doesn't exist
            ValueError: If session file is corrupted or can't be decrypted
        """
        try:
            if not os.path.exists(session_file):
                raise FileNotFoundError(f"Session file not found: {session_file}")

            # First, try to determine if this is encrypted or plain JSON
            with open(session_file, "rb") as f:
                file_data = f.read()

            # Try to decrypt if we have encryption enabled
            if self.use_encryption and self.cipher:
                try:
                    # Try to decrypt
                    decrypted_data = self.cipher.decrypt(file_data)
                    json_data = decrypted_data.decode("utf-8")
                    logger.debug(
                        "Session loaded with decryption", session_file=session_file
                    )
                except Exception:
                    # If decryption fails, try as plain JSON
                    json_data = file_data.decode("utf-8")
                    logger.debug(
                        "Session loaded as plain JSON (decryption failed)",
                        session_file=session_file,
                    )
            else:
                # Load as plain JSON
                json_data = file_data.decode("utf-8")
                logger.debug("Session loaded as plain JSON", session_file=session_file)

            # Parse JSON
            session_data = json.loads(json_data)
            return session_data

        except json.JSONDecodeError as e:
            logger.error(
                "Session file corrupted (invalid JSON)",
                session_file=session_file,
                exc_info=e,
            )
            raise ValueError(f"Session file corrupted: {session_file}")
        except Exception as e:
            logger.error(
                "Failed to load session", session_file=session_file, exc_info=e
            )
            raise

    def migrate_pickle_session(self, pickle_file: str, json_file: str) -> bool:
        """
        Migrate an existing pickle session to secure JSON format.

        Args:
            pickle_file: Path to existing pickle file
            json_file: Path where to save JSON version

        Returns:
            True if migration successful, False otherwise
        """
        try:
            import pickle

            if not os.path.exists(pickle_file):
                logger.info("No pickle file to migrate", pickle_file=pickle_file)
                return False

            # Load pickle data (UNSAFE - but needed for migration)
            logger.warning(
                "Loading pickle file for migration - this is the last time!",
                pickle_file=pickle_file,
            )

            with open(pickle_file, "rb") as f:
                pickle_data = pickle.load(f)

            # Save as secure JSON
            self.save_session(pickle_data, json_file)

            # Remove pickle file for security
            os.remove(pickle_file)
            logger.info(
                "Successfully migrated pickle session to secure format",
                from_file=pickle_file,
                to_file=json_file,
            )

            return True

        except Exception as e:
            logger.error(
                "Failed to migrate pickle session", pickle_file=pickle_file, exc_info=e
            )
            return False


class LegacyPickleSession:
    """
    Compatibility layer for legacy pickle sessions.
    Provides warning and migration path.
    """

    @staticmethod
    def load_with_warning(session_file: str) -> Dict[str, Any]:
        """
        Load pickle session with security warning.

        This method should only be used for migration purposes.
        """
        import pickle

        logger.critical(
            "SECURITY WARNING: Loading pickle session file! "
            "This is unsafe and should be migrated to secure JSON format.",
            session_file=session_file,
        )

        with open(session_file, "rb") as f:
            return pickle.load(f)

    @staticmethod
    def detect_pickle_file(session_file: str) -> bool:
        """Check if a file is a pickle file."""
        try:
            with open(session_file, "rb") as f:
                # Read first few bytes
                header = f.read(10)
                # Pickle files typically start with specific bytes
                return header.startswith(b"\x80") or header.startswith(b"(")
        except:
            return False


# Global secure storage instance
_global_storage: Optional[SecureSessionStorage] = None


def get_secure_storage(
    password: Optional[str] = None, use_encryption: bool = True
) -> SecureSessionStorage:
    """Get global secure storage instance."""
    global _global_storage

    if _global_storage is None:
        _global_storage = SecureSessionStorage(password, use_encryption)

    return _global_storage
