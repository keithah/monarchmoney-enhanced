# Changelog

All notable changes to this project will be documented in this file.

## [0.2.1] - 2025-09-02

**Package Renamed**: Published as `monarchmoney-enhanced` on PyPI to distinguish from the original `monarchmoney` package while maintaining the same import structure.

**Repository Renamed**: GitHub repository renamed to match PyPI package name.

## [0.2.0] - 2025-09-02

### 🔧 Fixed
- **Authentication 404 Errors**: Added automatic GraphQL fallback when REST endpoints return 404
- **Authentication 403 Errors**: Fixed missing HTTP headers (device-uuid, Origin, User-Agent)
- **MFA Field Detection**: Automatic detection of email OTP vs TOTP based on code format
- **GraphQL Client Bug**: Fixed execute_async parameter order compatibility
- **Token Management**: Fixed set_token() method to properly update Authorization header
- **Authentication Validation**: Improved _get_graphql_client() to properly check for authentication

### ✨ Added
- **Retry Logic**: Exponential backoff with jitter for rate limiting and transient errors
- **Test Suite**: Comprehensive pytest-based test coverage (38 tests)
  - Authentication tests (login, MFA, GraphQL fallback)
  - API method tests (accounts, transactions, error handling)
  - Integration tests (end-to-end functionality)
  - Session management tests
  - Retry logic tests
- **CI/CD Pipeline**: GitHub Actions workflow with multi-Python version testing (3.8-3.12)
- **Code Quality**: Automated linting (flake8), formatting (black), and import sorting (isort)
- **Coverage Reporting**: Integrated with Codecov for test coverage tracking
- **User Profile API**: New `get_me()` method to retrieve user information (timezone, email, name, MFA status)
- **Merchants API**: New `get_merchants()` method to retrieve merchant data with transaction counts

### 🛡️ Enhanced
- **Browser Compatibility**: Updated User-Agent to match Chrome browser
- **Header Management**: Added required headers for Monarch Money API compatibility
- **Error Handling**: Improved error messages and exception handling
- **Session Management**: Better session file handling and validation

### 📚 Documentation
- Updated README with troubleshooting section
- Added development and testing guidelines
- Documented new features and fixes
- Added this CHANGELOG

## Previous Versions

See the original repository's commit history for changes prior to this fork.