# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.0.2] - 2024-12-19

### Added

- Cognito token authentication support with automatic refresh
- Bearer token authentication for enhanced security
- `TokenManager` class for token lifecycle management
- `fetch_cognito_token()` function for Cognito integration
- `get_auth_headers()` utility for authentication headers
- Comprehensive test coverage for authentication features
- Example scripts demonstrating token usage
- Updated documentation for authentication configuration

### Changed

- Enhanced `SubmitDagByID` action to support multiple authentication methods
- Added `httpx` dependency for modern HTTP client functionality
- Maintained backward compatibility with existing basic auth

### Security

- Replaced basic authentication with more secure Bearer token authentication
- Added automatic token refresh to prevent authentication failures
- Implemented token caching to reduce API calls to Cognito

## [0.0.1] - 2022-MM-DD

### Added

-
-
-
