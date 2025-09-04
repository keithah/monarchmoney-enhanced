"""
Settings service for MonarchMoney Enhanced.

Handles system settings, user preferences, and reference data operations.
"""

from typing import Any, Dict, Optional

from gql import gql

from .base_service import BaseService


class SettingsService(BaseService):
    """
    Service for managing system settings and reference data.

    This service handles:
    - User account settings and preferences
    - System reference data (merchants, institutions)
    - Notifications and alerts
    - Subscription and profile information
    """

    async def get_me(self) -> Dict[str, Any]:
        """
        Get the current user's profile information.

        Returns:
            User profile data including timezone, email, name, and authentication status
        """
        self.logger.info("Fetching user profile information")

        query = gql(
            """
            query Common_GetMe {
                me {
                    ...UserFields
                    id
                    profile {
                        id
                        hasSeenCategoriesManagementTour
                        dismissedTransactionsListUpdatesTourAt
                        viewedMarkAsReviewedUpdatesCalloutAt
                        hasDismissedWhatsNewAt
                        __typename
                    }
                    __typename
                }
            }

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
        )

        return await self._execute_query(operation="Common_GetMe", query=query)

    async def get_settings(self) -> Dict[str, Any]:
        """
        Get user account settings and preferences.

        Returns:
            User settings data including timezone, currency, and notification preferences
        """
        self.logger.info("Fetching user settings")

        query = gql(
            """
            query GetUserSettings {
                me {
                    id
                    timezone
                    settings {
                        currency
                        dateFormat
                        emailNotifications
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetUserSettings", query=query)

    async def update_settings(
        self,
        timezone: Optional[str] = None,
        currency: Optional[str] = None,
        date_format: Optional[str] = None,
        email_notifications: Optional[bool] = None,
    ) -> Dict[str, Any]:
        """
        Update user account settings and preferences.

        Args:
            timezone: User's timezone (e.g., "America/New_York")
            currency: Default currency code (e.g., "USD")
            date_format: Preferred date format
            email_notifications: Enable/disable email notifications

        Returns:
            Updated settings data
        """
        self.logger.info(
            "Updating user settings",
            settings={
                "timezone": timezone,
                "currency": currency,
                "date_format": date_format,
                "email_notifications": email_notifications,
            },
        )

        # Build variables dict with only non-None values
        variables = {}
        if timezone is not None:
            variables["timezone"] = timezone
        if currency is not None:
            variables["currency"] = currency
        if date_format is not None:
            variables["dateFormat"] = date_format
        if email_notifications is not None:
            variables["emailNotifications"] = email_notifications

        query = gql(
            """
            mutation UpdateUserSettings(
                $timezone: String,
                $currency: String,
                $dateFormat: String,
                $emailNotifications: Boolean
            ) {
                updateUserSettings(
                    timezone: $timezone,
                    currency: $currency,
                    dateFormat: $dateFormat,
                    emailNotifications: $emailNotifications
                ) {
                    me {
                        id
                        timezone
                        settings {
                            currency
                            dateFormat
                            emailNotifications
                            __typename
                        }
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self.client.gql_call(
            operation="UpdateUserSettings", graphql_query=query, variables=variables
        )

    async def get_merchants(self) -> Dict[str, Any]:
        """
        Get the list of merchants that have transactions.

        Returns:
            List of merchants with transaction data
        """
        self.logger.info("Fetching merchants list")

        query = gql(
            """
            query GetMerchants {
                merchants {
                    id
                    name
                    transactionCount
                    logoUrl
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetMerchants", query=query)

    async def get_institutions(self) -> Dict[str, Any]:
        """
        Get institution data from the account.

        Returns:
            List of financial institutions
        """
        self.logger.info("Fetching institutions list")

        query = gql(
            """
            query GetInstitutions {
                institutions {
                    id
                    name
                    url
                    logoUrl
                    primaryColor
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetInstitutions", query=query)

    async def get_notifications(self) -> Dict[str, Any]:
        """
        Get account notifications and alerts.

        Returns:
            Notifications data including unread counts and message details
        """
        self.logger.info("Fetching notifications")

        query = gql(
            """
            query GetNotifications {
                notifications {
                    id
                    title
                    message
                    type
                    isRead
                    createdAt
                    __typename
                }
            }
        """
        )

        return await self._execute_query(operation="GetNotifications", query=query)

    async def get_subscription_details(self) -> Dict[str, Any]:
        """
        Get the subscription type for the Monarch Money account.

        Returns:
            Subscription details including plan type and status
        """
        self.logger.info("Fetching subscription details")

        query = gql(
            """
            query GetSubscriptionDetails {
                me {
                    id
                    subscription {
                        id
                        planType
                        status
                        billingCycle
                        nextBillingDate
                        __typename
                    }
                    __typename
                }
            }
        """
        )

        return await self._execute_query(
            operation="GetSubscriptionDetails", query=query
        )
