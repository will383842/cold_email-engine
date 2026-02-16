"""MailWizz API Client - Enhanced version."""

import requests
from typing import Optional


class MailWizzClient:
    """
    MailWizz API Client for subscriber and campaign management.

    Docs: https://api-docs.mailwizz.com/
    """

    def __init__(self, base_url: str, public_key: str, private_key: str):
        """
        Initialize MailWizz client.

        Args:
            base_url: MailWizz instance URL (e.g., https://mailwizz-sos-expat.example.com)
            public_key: API public key
            private_key: API private key
        """
        self.base_url = base_url.rstrip("/")
        self.public_key = public_key
        self.private_key = private_key

    def _request(self, method: str, endpoint: str, data: Optional[dict] = None) -> dict:
        """
        Make API request.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., /lists)
            data: Optional request data

        Returns:
            Response JSON

        Raises:
            requests.HTTPError: If request fails
        """
        url = f"{self.base_url}/api{endpoint}"
        headers = {
            "X-MW-PUBLIC-KEY": self.public_key,
            "X-MW-PRIVATE-KEY": self.private_key,
        }

        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    # =========================================================================
    # LISTS
    # =========================================================================

    def get_lists(self) -> list[dict]:
        """
        Get all lists.

        Returns:
            List of list dicts
        """
        response = self._request("GET", "/lists")
        return response.get("data", {}).get("records", [])

    def create_list(self, name: str, defaults: dict) -> dict:
        """
        Create new list.

        Args:
            name: List name
            defaults: Dict with from_name, from_email, reply_to, subject

        Returns:
            Created list dict
        """
        data = {
            "general": {
                "name": name,
                "description": f"List for {name}",
            },
            "defaults": defaults,
        }
        response = self._request("POST", "/lists", data)
        return response.get("data", {}).get("record", {})

    # =========================================================================
    # SUBSCRIBERS
    # =========================================================================

    def create_subscriber(self, list_id: str, subscriber: dict) -> dict:
        """
        Create/update subscriber in list.

        Args:
            list_id: MailWizz list UID
            subscriber: Dict with EMAIL (required) and optional fields (FNAME, LNAME, etc.)

        Returns:
            Subscriber dict with subscriber_uid

        Example:
            client.create_subscriber(
                list_id="ab123cd4ef",
                subscriber={
                    "EMAIL": "test@example.com",
                    "FNAME": "Jean",
                    "LNAME": "Dupont",
                    "COMPANY": "ACME Corp",
                }
            )
        """
        response = self._request("POST", f"/lists/{list_id}/subscribers", subscriber)
        return response.get("data", {}).get("record", {})

    def update_subscriber(self, list_id: str, subscriber_uid: str, data: dict) -> dict:
        """
        Update subscriber.

        Args:
            list_id: MailWizz list UID
            subscriber_uid: Subscriber UID
            data: Fields to update

        Returns:
            Updated subscriber dict
        """
        response = self._request(
            "PUT",
            f"/lists/{list_id}/subscribers/{subscriber_uid}",
            data,
        )
        return response.get("data", {}).get("record", {})

    def get_subscriber(self, list_id: str, subscriber_uid: str) -> Optional[dict]:
        """
        Get subscriber by UID.

        Args:
            list_id: MailWizz list UID
            subscriber_uid: Subscriber UID

        Returns:
            Subscriber dict or None
        """
        try:
            response = self._request(
                "GET",
                f"/lists/{list_id}/subscribers/{subscriber_uid}",
            )
            return response.get("data", {}).get("record")
        except requests.HTTPError as e:
            if e.response.status_code == 404:
                return None
            raise

    def search_subscriber_by_email(self, list_id: str, email: str) -> Optional[dict]:
        """
        Search subscriber by email.

        Args:
            list_id: MailWizz list UID
            email: Email address

        Returns:
            Subscriber dict or None
        """
        response = self._request(
            "GET",
            f"/lists/{list_id}/subscribers/search-by-email",
            {"EMAIL": email},
        )
        data = response.get("data", {})
        if data.get("status") == "success":
            return data.get("record")
        return None

    def unsubscribe(self, list_id: str, subscriber_uid: str) -> bool:
        """
        Unsubscribe subscriber.

        Args:
            list_id: MailWizz list UID
            subscriber_uid: Subscriber UID

        Returns:
            True if successful
        """
        try:
            self._request(
                "PUT",
                f"/lists/{list_id}/subscribers/{subscriber_uid}/unsubscribe",
            )
            return True
        except requests.HTTPError:
            return False

    # =========================================================================
    # CAMPAIGNS
    # =========================================================================

    def create_campaign(
        self,
        list_id: str,
        name: str,
        subject: str,
        from_name: str,
        from_email: str,
        reply_to: str,
        html_content: str,
        plain_content: Optional[str] = None,
    ) -> dict:
        """
        Create campaign.

        Args:
            list_id: MailWizz list UID
            name: Campaign name
            subject: Email subject
            from_name: From name
            from_email: From email
            reply_to: Reply-to email
            html_content: HTML content
            plain_content: Optional plain text content

        Returns:
            Campaign dict with campaign_uid
        """
        data = {
            "name": name,
            "type": "regular",  # or "autoresponder"
            "from_name": from_name,
            "from_email": from_email,
            "reply_to": reply_to,
            "subject": subject,
            "list_uid": list_id,
            "template": {
                "content": html_content,
                "inline_css": "yes",
            },
        }

        if plain_content:
            data["template"]["plain_text"] = plain_content

        response = self._request("POST", "/campaigns", data)
        return response.get("data", {}).get("record", {})

    def send_campaign(self, campaign_uid: str) -> bool:
        """
        Send campaign immediately.

        Args:
            campaign_uid: Campaign UID

        Returns:
            True if successful
        """
        try:
            self._request("PUT", f"/campaigns/{campaign_uid}/send", {})
            return True
        except requests.HTTPError:
            return False

    def get_campaign_stats(self, campaign_uid: str) -> dict:
        """
        Get campaign statistics.

        Args:
            campaign_uid: Campaign UID

        Returns:
            Stats dict with counts (processed, sent, delivered, opened, clicked, bounced, etc.)
        """
        response = self._request("GET", f"/campaigns/{campaign_uid}/stats")
        return response.get("data", {})

    # =========================================================================
    # HEALTH CHECK
    # =========================================================================

    def health_check(self) -> bool:
        """
        Check if MailWizz API is reachable.

        Returns:
            True if healthy
        """
        try:
            self._request("GET", "/lists")
            return True
        except Exception:
            return False
