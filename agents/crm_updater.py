"""
agents/crm_updater.py
---------------------
Tool 3: Legacy CRM REST API mein customer data update karna.

Challenges:
  1. API undocumented hai (endpoints guess karne padte hain / explore karne padte hain)
  2. Rate limiting: 429 Too Many Requests aata hai
  3. Intermittent failures: network timeouts, 500 errors

Solution:
  - Retry decorator with exponential backoff
  - Proper HTTP error handling
  - Timeout set karna (infinite wait mat karo)
  - Detailed logging (kab kya hua)
"""

import os
import json
import time
import requests
from requests.exceptions import RequestException, Timeout, ConnectionError
from utils.logger import get_logger
from utils.retry import retry_with_backoff

logger = get_logger("crm_updater")


class CRMUpdater:
    """
    Legacy CRM API se baat karta hai.

    Mock mode mein: ek fake local server simulate karta hai
    Real mode mein: actual CRM REST API call karta hai
    """

    def __init__(self, base_url: str = None, mock_mode: bool = False):
        self.mock_mode = mock_mode

        if mock_mode:
            self.base_url = "http://mock-crm.local"  # fake URL, real call nahi hogi
            logger.info("🧪 CRM Updater in MOCK mode")
        else:
            self.base_url = base_url or os.getenv("CRM_BASE_URL", "https://crm.example.com/api")
            self.api_key = os.getenv("CRM_API_KEY", "")
            logger.info(f"🔗 CRM Updater pointing to: {self.base_url}")

        # Request headers — undocumented APIs mein yeh guess karna padta hai
        self.headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-API-Key": getattr(self, "api_key", ""),
        }

    def create_or_update_customer(self, customer_data: dict) -> dict:
        """
        Main function: CRM mein ek customer create ya update karo.

        Pehle check karo — customer already exist karta hai?
          Yes → update (PUT)
          No  → create (POST)

        Returns: CRM ka response dict
        """
        email = customer_data.get("email")
        if not email:
            raise ValueError("Customer email required for CRM upsert")

        logger.info(f"📤 Processing customer: {email}")

        if self.mock_mode:
            return self._mock_crm_call(customer_data)

        # Step 1: Search if customer exists
        existing = self._search_customer_by_email(email)

        if existing:
            customer_id = existing.get("id")
            logger.info(f"🔄 Customer exists (id={customer_id}), updating...")
            return self._update_customer(customer_id, customer_data)
        else:
            logger.info("➕ New customer, creating...")
            return self._create_customer(customer_data)

    # ─── API Calls with Retry ──────────────────────────────────────────────────

    @retry_with_backoff(max_retries=3, base_delay=2.0, exceptions=(RequestException, Exception))
    def _search_customer_by_email(self, email: str) -> dict | None:
        """
        GET /customers?email=... → customer dhundo
        @retry_with_backoff: agar fail ho toh auto retry with exponential backoff
        """
        response = requests.get(
            f"{self.base_url}/customers",
            params={"email": email},
            headers=self.headers,
            timeout=10  # 10 second mein respond nahi kiya toh timeout
        )

        self._handle_rate_limit(response)   # 429 check
        response.raise_for_status()          # 4xx/5xx → exception

        data = response.json()
        results = data.get("results", [])
        return results[0] if results else None

    @retry_with_backoff(max_retries=3, base_delay=2.0, exceptions=(RequestException, Exception))
    def _create_customer(self, customer_data: dict) -> dict:
        """POST /customers → naya customer banao"""
        response = requests.post(
            f"{self.base_url}/customers",
            json=self._sanitize(customer_data),
            headers=self.headers,
            timeout=10
        )

        self._handle_rate_limit(response)
        response.raise_for_status()

        result = response.json()
        logger.info(f"✅ Customer created in CRM: id={result.get('id')}")
        return result

    @retry_with_backoff(max_retries=3, base_delay=2.0, exceptions=(RequestException, Exception))
    def _update_customer(self, customer_id: str, customer_data: dict) -> dict:
        """PUT /customers/{id} → existing customer update karo"""
        response = requests.put(
            f"{self.base_url}/customers/{customer_id}",
            json=self._sanitize(customer_data),
            headers=self.headers,
            timeout=10
        )

        self._handle_rate_limit(response)
        response.raise_for_status()

        result = response.json()
        logger.info(f"✅ Customer updated in CRM: id={customer_id}")
        return result

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _handle_rate_limit(self, response: requests.Response):
        """
        HTTP 429 = Too Many Requests (rate limited)
        Agar Retry-After header hai toh utna wait karo.
        Nahi toh 5 second wait karo.
        """
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 5))
            logger.warning(f"🚦 Rate limited! Waiting {retry_after}s (Retry-After header)...")
            time.sleep(retry_after)
            # Exception raise karo taaki retry_with_backoff us par retry kare
            raise Exception(f"Rate limited (429). Waited {retry_after}s.")

    def _sanitize(self, data: dict) -> dict:
        """
        CRM mein bhejne se pehle data clean karo.
        - None values hata do (undocumented API null values se crash ho sakta hai)
        - Fields rename karo agar CRM ka alag schema ho
        """
        return {k: v for k, v in data.items() if v is not None}

    def _mock_crm_call(self, customer_data: dict) -> dict:
        """
        Mock CRM response — bina actual API ke test karo.
        Real failure scenarios simulate karne ke liye MOCK_FAIL_RATE env variable.
        """
        import random

        # 20% chance of failure — retry logic test karne ke liye
        fail_rate = float(os.getenv("MOCK_FAIL_RATE", "0.0"))
        if random.random() < fail_rate:
            raise Exception("Mock CRM: Simulated failure (test retry logic)")

        # Success response simulate karo
        fake_id = f"CRM-{hash(customer_data.get('email', '')) % 100000:05d}"
        result = {
            "id": fake_id,
            "status": "created",
            "customer": customer_data,
            "message": "Customer successfully onboarded",
        }
        logger.info(f"✅ [MOCK] CRM response: id={fake_id}")
        return result
