"""
Locust load test for the datacenter-sim FastAPI server.

Run with (from the project root, with venv activated and the server already
running on port 8000):

    locust -f locustfile.py --host=http://localhost:8000

Then open http://localhost:8089 in your browser to start the test
(pick number of users + spawn rate).
"""

import random
from locust import HttpUser, task, between


class APIUser(HttpUser):
    # Each simulated user waits 1-3 seconds between tasks (realistic pacing)
    wait_time = between(1, 3)

    def on_start(self):
        """Runs once per simulated user, right when they 'start' — log in here."""
        username, password, role = random.choice([
            ("webuser_0", "pass", "web"),
            ("mobileuser_1", "pass", "mobile"),
            ("apiuser_2", "pass", "api"),
        ])
        self.role = role

        response = self.client.post(
            "/login",
            json={"username": username, "password": password},
            name="/login",
        )

        if response.status_code == 200:
            self.token = response.json().get("token") or response.json().get("access_token")
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            # Login failed (e.g. hit the rate limiter) — mark no token so
            # tasks below skip gracefully instead of crashing.
            self.token = None
            self.headers = {}

    @task(3)
    def get_me(self):
        if not self.token:
            return
        self.client.get("/me", headers=self.headers, name="/me")

    @task(2)
    def get_api_data(self):
        if not self.token:
            return
        self.client.get("/api/data", headers=self.headers, name="/api/data")

    @task(1)
    def update_profile(self):
        if not self.token:
            return
        self.client.post(
            "/profile/update",
            json={"bio": "load test user"},
            headers=self.headers,
            name="/profile/update",
        )

    @task(1)
    def health_check(self):
        # No auth needed
        self.client.get("/health", name="/health")

    def on_stop(self):
        """Runs once when the simulated user 'stops' — log out cleanly."""
        if self.token:
            self.client.post("/logout", headers=self.headers, name="/logout")
