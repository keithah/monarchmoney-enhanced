"""
Common GraphQL fragments to reduce duplication and improve maintainability.

This module extracts the 30+ duplicate fragment definitions found across the codebase
into a single source of truth.
"""

from typing import Dict, Optional


class Fragments:
    """Registry of reusable GraphQL fragments."""
    
    # Account-related fragments
    ACCOUNT_FIELDS = """
        fragment AccountFields on Account {
            id
            displayName
            syncDisabled
            deactivatedAt
            isHidden
            isAsset
            mask
            createdAt
            updatedAt
            displayLastUpdatedAt
            currentBalance
            displayBalance
            includeInNetWorth
            hideFromList
            hideTransactionsFromReports
            includeBalanceInNetWorth
            includeInGoalBalance
            dataProvider
            dataProviderAccountId
            isManual
            transactionsCount
            holdingsCount
            manualInvestmentsTrackingMethod
            order
            logoUrl
            type {
                name
                display
                __typename
            }
            subtype {
                name
                display
                __typename
            }
            credential {
                id
                updateRequired
                disconnectedFromDataProviderAt
                dataProvider
                institution {
                    id
                    plaidInstitutionId
                    name
                    status
                    __typename
                }
                __typename
            }
            institution {
                id
                name
                primaryColor
                url
                __typename
            }
            __typename
        }
    """
    
    ACCOUNT_FIELDS_BASIC = """
        fragment AccountFieldsBasic on Account {
            id
            displayName
            currentBalance
            displayBalance
            type {
                name
                display
            }
            institution {
                id
                name
            }
        }
    """
    
    ACCOUNT_FIELDS_BALANCE = """
        fragment AccountFieldsBalance on Account {
            id
            displayName
            currentBalance
            displayBalance
            includeInNetWorth
            includeBalanceInNetWorth
            includeInGoalBalance
        }
    """
    
    EDIT_ACCOUNT_FORM_FIELDS = """
        fragment EditAccountFormFields on Account {
            id
            displayName
            includeInNetWorth
            includeBalanceInNetWorth
            hideFromList
            hideTransactionsFromReports
            dataProvider
            dataProviderAccountId
            isManual
            manualInvestmentsTrackingMethod
            isAsset
            invertSignForDisplay
            icon
            logoUrl
            order
            includeInGoalBalance
            type {
                name
                display
                __typename
            }
            subtype {
                name
                display
                group
                __typename
            }
            __typename
        }
    """
    
    # User-related fragments
    USER_FIELDS = """
        fragment UserFields on User {
            birthday
            email
            id
            isSuperuser
            name
            timezone
            hasPassword
            hasMfaOn
            externalAuthProviderNames
            pendingEmailUpdateVerification {
                email
                __typename
            }
            profilePicture {
                id
                cloudinaryPublicId
                thumbnailUrl
                __typename
            }
            profilePictureUrl
            activeSupportAccountAccessGrant {
                id
                createdAt
                expiresAt
                __typename
            }
            __typename
        }
    """
    
    # Transaction-related fragments
    TRANSACTION_FIELDS = """
        fragment TransactionFields on Transaction {
            id
            amount
            pending
            date
            signedAmount
            merchantId
            merchant {
                id
                name
                logoUrl
                __typename
            }
            category {
                id
                name
                icon
                group {
                    id
                    name
                    type
                }
                __typename
            }
            account {
                id
                displayName
                institution {
                    id
                    name
                }
                __typename
            }
            tags {
                id
                name
                color
                __typename
            }
            needsReview
            isRecurring
            notes
            attachments {
                id
                publicId
                __typename
            }
            isSplitTransaction
            originalDate
            hideFromReports
            __typename
        }
    """
    
    TRANSACTION_OVERVIEW_FIELDS = """
        fragment TransactionOverviewFields on Transaction {
            id
            amount
            pending
            date
            signedAmount
            merchantId
            hasSplitTransactions
            isSplitTransaction
            notes
            isRecurring
            reviewStatus
            needsReview
            dataProviderDescription
            attachments {
                id
                publicId
                __typename
            }
            __typename
        }
    """
    
    TRANSACTIONS_LIST_FIELDS = """
        fragment TransactionsListFields on Transaction {
            id
            ...TransactionOverviewFields
            merchant {
                id
                name
                __typename
            }
            category {
                id
                __typename
            }
            account {
                id
                __typename
            }
            __typename
        }
    """
    
    # Budget-related fragments
    BUDGET_CATEGORY_FIELDS = """
        fragment BudgetCategoryFields on Category {
            id
            name
            order
            icon
            isSystemCategory
            isDisabled
            group {
                id
                name
                type
                __typename
            }
            __typename
        }
    """
    
    BUDGET_CATEGORY_GROUP_FIELDS = """
        fragment BudgetCategoryGroupFields on CategoryGroup {
            id
            name
            order
            type
            __typename
        }
    """
    
    BUDGET_DATA_FIELDS = """
        fragment BudgetDataFields on BudgetData {
            monthlyAmounts {
                ...BudgetDataMonthlyAmountsFields
                __typename
            }
            totals {
                ...BudgetDataTotalsByMonthFields
                __typename
            }
            categories {
                ...BudgetCategoryFields
                __typename
            }
            categoryGroups {
                ...BudgetCategoryGroupFields
                __typename
            }
            goals {
                ...BudgetDataGoalsV2Fields
                __typename
            }
            rolloverPeriod {
                ...BudgetRolloverPeriodFields
                __typename
            }
            __typename
        }
    """
    
    # Institution-related fragments
    INSTITUTION_STATUS_FIELDS = """
        fragment InstitutionStatusFields on Institution {
            id
            hasIssuesReported
            hasIssuesReportedMessage
            status
            __typename
        }
    """
    
    CREDENTIAL_SETTINGS_CARD_FIELDS = """
        fragment CredentialSettingsCardFields on Credential {
            id
            institution {
                ...InstitutionInfoFields
                ...InstitutionLogoWithStatusFields
                ...InstitutionStatusFields
                __typename
            }
            refreshState
            dataProvider
            id
            disconnectedFromDataProviderAt
            dataProvider
            updateRequired
            includedInNetWorth
            __typename
        }
    """
    
    # Error handling fragments
    PAYLOAD_ERROR_FIELDS = """
        fragment PayloadErrorFields on PayloadError {
            fieldErrors {
                field
                messages
                __typename
            }
            message
            code
            __typename
        }
    """
    
    # Merchant fragments
    MERCHANT_FIELDS = """
        fragment MerchantFields on Merchant {
            id
            name
            logoUrl
            displayName
            transactionCount
            __typename
        }
    """
    
    # Category fragments
    CATEGORY_FIELDS = """
        fragment CategoryFields on Category {
            id
            name
            order
            icon
            isSystemCategory
            isDisabled
            group {
                id
                name
                type
                __typename
            }
            __typename
        }
    """
    
    # Tag fragments
    TAG_FIELDS = """
        fragment TagFields on TransactionTag {
            id
            name
            color
            order
            transactionCount
            __typename
        }
    """


# Create singleton instance
FRAGMENTS = Fragments()


def get_fragment(name: str) -> str:
    """
    Get a fragment by name.
    
    Args:
        name: The name of the fragment (e.g., 'ACCOUNT_FIELDS')
    
    Returns:
        The fragment definition string
    
    Raises:
        ValueError: If the fragment name is not found
    """
    if not hasattr(FRAGMENTS, name):
        raise ValueError(f"Fragment '{name}' not found. Available fragments: {list_fragments()}")
    
    return getattr(FRAGMENTS, name)


def list_fragments() -> list:
    """
    List all available fragment names.
    
    Returns:
        List of fragment names
    """
    return [
        attr for attr in dir(FRAGMENTS) 
        if not attr.startswith('_') and isinstance(getattr(FRAGMENTS, attr), str)
    ]


def compose_fragments(*fragment_names: str) -> str:
    """
    Compose multiple fragments into a single string.
    
    Args:
        fragment_names: Names of fragments to compose
    
    Returns:
        Combined fragment definitions
    """
    return '\n'.join(get_fragment(name) for name in fragment_names)