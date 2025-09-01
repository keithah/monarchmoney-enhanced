# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased] - 2025-09-01

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