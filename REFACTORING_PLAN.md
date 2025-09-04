# MonarchMoney God Class Refactoring Plan

## Current State
- **File**: `monarchmoney/monarchmoney.py`
- **Size**: 5,583 lines of code  
- **Methods**: 106+ methods
- **Anti-pattern**: God Class - single class with too many responsibilities

## Problem Statement
The `MonarchMoney` class violates the Single Responsibility Principle by handling:
1. Authentication & session management
2. Account CRUD operations  
3. Transaction processing & rules
4. Investment tracking
5. Budget & goal management
6. Financial analysis & reporting
7. System settings & configuration
8. GraphQL infrastructure

This creates maintenance challenges, testing difficulties, and tight coupling.

## Refactoring Goals
1. **Single Responsibility** - Each class handles one business domain
2. **Loose Coupling** - Services communicate through well-defined interfaces
3. **High Cohesion** - Related functionality grouped together
4. **Testability** - Isolated components easier to unit test
5. **Maintainability** - Smaller, focused classes easier to understand
6. **Backward Compatibility** - Existing API preserved during transition

## Target Architecture

### Service-Oriented Architecture
```
MonarchMoney (Orchestrator)
├── AuthenticationService
├── AccountService  
├── TransactionService
│   ├── TransactionRulesManager
│   ├── TransactionCategoryManager
│   └── TransactionTagManager
├── InvestmentService
├── BudgetService
├── InsightService
├── SettingsService
└── GraphQLClient (Infrastructure)
```

## Detailed Service Breakdown

### 1. AuthenticationService (14 methods)
**Responsibility**: Handle all authentication, MFA, and session lifecycle

**Methods**:
- `login()` - Primary login method
- `interactive_login()` - Interactive CLI login
- `multi_factor_authenticate()` - Handle MFA challenges
- `validate_session()` - Check session validity
- `ensure_valid_session()` - Validate or refresh session
- `save_session()` - Persist session to storage
- `load_session()` - Load session from storage  
- `delete_session()` - Remove session
- `is_session_stale()` - Check if session needs refresh
- `get_session_info()` - Get session metadata
- Private helpers: `_login_user()`, `_login_user_graphql()`, etc.

### 2. AccountService (13 methods)
**Responsibility**: Account lifecycle, balances, and refresh coordination

**Methods**:
- `get_accounts()` - Retrieve account list
- `create_manual_account()` - Add manual account
- `update_account()` - Modify account details
- `delete_account()` - Remove account
- `get_account_type_options()` - Available account types
- `get_recent_account_balances()` - Current balance data
- `get_account_history()` - Historical balance data
- `upload_account_balance_history()` - Import historical data
- `request_accounts_refresh()` - Trigger institution sync
- `is_accounts_refresh_complete()` - Check sync status
- `request_accounts_refresh_and_wait()` - Sync with polling
- `get_net_worth_history()` - Net worth trends
- `get_account_snapshots_by_type()` - Account groupings

### 3. TransactionService (29 methods)
**Responsibility**: Transaction operations and categorization

**Core Methods**:
- `get_transactions()` - Query transactions
- `get_transactions_summary()` - Transaction summaries
- `create_transaction()` - Add new transaction
- `update_transaction()` - Modify transaction
- `delete_transaction()` - Remove transaction
- `get_recurring_transactions()` - Recurring transaction patterns

**Sub-Managers**:
- `TransactionRulesManager` (12 methods) - Rule creation and management
- `TransactionCategoryManager` (6 methods) - Category operations  
- `TransactionTagManager` (5 methods) - Tag management

### 4. InvestmentService (6 methods)
**Responsibility**: Investment holdings and performance tracking

**Methods**:
- `get_account_holdings()` - Investment positions
- `create_manual_holding()` - Add manual investment
- `delete_manual_holding()` - Remove investment
- `get_security_details()` - Security information
- `get_investment_performance()` - Performance analytics

### 5. BudgetService (6 methods)
**Responsibility**: Budget and financial goal management

**Methods**:
- `get_budgets()` - Retrieve budgets
- `set_budget_amount()` - Update budget limits
- `get_goals()` - Financial goals
- `create_goal()` - Add new goal
- `update_goal()` - Modify goal
- `delete_goal()` - Remove goal

### 6. InsightService (6 methods)
**Responsibility**: Financial analysis and reporting

**Methods**:
- `get_cashflow()` - Cash flow analysis
- `get_cashflow_summary()` - Cash flow summary
- `get_insights()` - Financial insights
- `get_credit_score()` - Credit information
- `get_aggregate_snapshots()` - Account aggregations
- `get_bills()` - Bill tracking

### 7. SettingsService (7 methods)
**Responsibility**: System settings and reference data

**Methods**:
- `get_settings()` - User preferences
- `update_settings()` - Modify preferences
- `get_merchants()` - Merchant directory
- `get_institutions()` - Financial institutions
- `get_notifications()` - System notifications
- `get_subscription_details()` - Account subscription
- `get_me()` - User profile information

### 8. GraphQLClient (Infrastructure)
**Responsibility**: Low-level GraphQL communication

**Methods**:
- `gql_call()` - Execute GraphQL operations
- `_get_graphql_client()` - GraphQL client factory
- Retry logic and error handling
- Session integration

## Migration Strategy

### Phase 1: Foundation (Current)
- [x] Create services package structure
- [x] Define service interfaces
- [x] Document refactoring plan
- [ ] Create base service class with common functionality

### Phase 2: Infrastructure Services
- [ ] Extract `GraphQLClient` 
- [ ] Extract `AuthenticationService`
- [ ] Update session management integration

### Phase 3: Business Services (High Value)
- [ ] Extract `TransactionService` and sub-managers
- [ ] Extract `AccountService`
- [ ] Extract `SettingsService`

### Phase 4: Specialized Services
- [ ] Extract `InvestmentService`
- [ ] Extract `BudgetService` 
- [ ] Extract `InsightService`

### Phase 5: Integration & Testing
- [ ] Update `MonarchMoney` class to orchestrate services
- [ ] Add backward compatibility layer
- [ ] Comprehensive testing
- [ ] Performance validation

### Phase 6: Optimization
- [ ] Remove deprecated methods
- [ ] Optimize service communication
- [ ] Documentation updates

## Implementation Guidelines

### Service Base Class
```python
class BaseService:
    \"\"\"Base class for all MonarchMoney services\"\"\"
    
    def __init__(self, client: 'GraphQLClient'):
        self.client = client
        self.logger = MonarchLogger(self.__class__.__name__)
    
    async def _execute_query(self, operation: str, query: Any) -> Dict[str, Any]:
        \"\"\"Execute GraphQL query with error handling\"\"\"
        return await self.client.gql_call(operation, query)
```

### Service Interface Pattern
```python
from abc import ABC, abstractmethod

class AuthenticationServiceInterface(ABC):
    @abstractmethod
    async def login(self, email: str, password: str) -> None: ...
    
    @abstractmethod
    async def validate_session(self) -> bool: ...
```

### Backward Compatibility
```python
class MonarchMoney:
    def __init__(self, ...):
        # Initialize services
        self._auth = AuthenticationService(...)
        self._accounts = AccountService(...)
        # ... other services
    
    # Delegate to services while maintaining original API
    async def login(self, *args, **kwargs):
        \"\"\"Backward compatibility wrapper\"\"\"
        return await self._auth.login(*args, **kwargs)
```

## Testing Strategy

### Service-Level Testing
- Unit tests for each service in isolation
- Mock dependencies and external calls
- Test error conditions and edge cases

### Integration Testing  
- Test service interactions
- Validate GraphQL query generation
- End-to-end workflow testing

### Backward Compatibility Testing
- Ensure existing client code continues to work
- Validate API contracts are preserved
- Performance regression testing

## Benefits

### Immediate Benefits
- **Reduced Complexity** - Smaller, focused classes
- **Improved Testing** - Isolated components
- **Better Error Handling** - Service-specific error management

### Long-term Benefits
- **Parallel Development** - Teams can work on different services
- **Feature Isolation** - Changes in one area don't affect others  
- **Easier Debugging** - Clear responsibility boundaries
- **Better Documentation** - Service-specific docs

## Risk Mitigation

### Breaking Changes
- Maintain backward compatibility during transition
- Use deprecation warnings for old patterns
- Provide migration guides

### Performance Impact
- Minimize service communication overhead
- Batch operations where possible
- Profile before/after performance

### Testing Coverage
- Maintain 100% test coverage during refactoring
- Add integration tests for service boundaries
- Validate all existing functionality

## Success Criteria

1. **No Functional Regressions** - All existing features work identically
2. **Improved Test Coverage** - Each service has comprehensive unit tests  
3. **Reduced Complexity** - Cyclomatic complexity reduced by 60%+
4. **Better Performance** - No performance degradation
5. **Developer Experience** - Easier to add features and fix bugs

## Next Steps

1. Complete Phase 1 foundation
2. Begin Phase 2 with GraphQLClient extraction
3. Implement comprehensive test suite for extracted services
4. Continue with high-value business services
5. Maintain backward compatibility throughout

This refactoring will transform the codebase from a monolithic God Class into a maintainable, testable, and extensible service-oriented architecture.