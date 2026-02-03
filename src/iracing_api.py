diff --git a/src/iracing_api.py b/src/iracing_api.py
index b77f01d539c4061376a95a0135dfff85278d6599..a0082516143cb6eb69db33b00f1dc83e2b68155a 100644
--- a/src/iracing_api.py
+++ b/src/iracing_api.py
@@ -1,55 +1,60 @@
 """iRacing data server client helpers."""
 
 from __future__ import annotations
 
 import logging
 from dataclasses import dataclass
 from typing import Any, Dict, Optional
 
 import requests
 
 LOGGER = logging.getLogger(__name__)
 
 
 @dataclass
 class IRacingConfig:
     base_url: str
-    access_token: str
+    access_token: Optional[str] = None
+    session: Optional[requests.Session] = None
 
 
 class IRacingAPI:
     """Client for iRacing data server endpoints."""
 
     def __init__(self, config: IRacingConfig) -> None:
         self._config = config
-        self._session = requests.Session()
-        self._session.headers.update(
-            {
-                "Authorization": f"Bearer {self._config.access_token}",
-                "Accept": "application/json",
-            }
-        )
+        self._session = self._config.session or requests.Session()
+        self._session.headers.update({"Accept": "application/json"})
+        if self._config.access_token:
+            self._session.headers.update({"Authorization": f"Bearer {self._config.access_token}"})
+        elif not self._config.session:
+            raise ValueError("IRacingAPI requires an access token or an authenticated session.")
 
     def get_session_results(self, session_id: str) -> Dict[str, Any]:
         """Fetch session results for the provided subsession/session id."""
         endpoint = f"{self._config.base_url}/data/results/get"
         LOGGER.debug("Requesting session results from %s", endpoint)
         response = self._session.get(endpoint, params={"subsession_id": session_id}, timeout=30)
         response.raise_for_status()
         payload = response.json()
         link = payload.get("link")
         if not link:
             raise ValueError("Results response did not include a data link.")
         LOGGER.debug("Fetching results payload from %s", link)
         results_response = self._session.get(link, timeout=30)
         results_response.raise_for_status()
         return results_response.json()
 
 
 def build_base_url() -> str:
     return "https://members-ng.iracing.com"
 
 
 def build_api(access_token: str, base_url: Optional[str] = None) -> IRacingAPI:
     config = IRacingConfig(base_url=base_url or build_base_url(), access_token=access_token)
     return IRacingAPI(config)
+
+
+def build_api_with_session(session: requests.Session, base_url: Optional[str] = None) -> IRacingAPI:
+    config = IRacingConfig(base_url=base_url or build_base_url(), session=session)
+    return IRacingAPI(config)
