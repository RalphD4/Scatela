import os
import re
import unittest
from datetime import datetime, timedelta, timezone

from sqlalchemy import text

from backend.app import create_app
from backend.database import db
from backend.models import Alert, Bases, Child, ChildBaseStatus, Child_Log, Guardian, Users
from backend.services.distance_service import evaluate_threshold, haversine_distance_meters


class ScatelaIntegrationTests(unittest.TestCase):
    """Comprehensive integration & security test suite against PostgreSQL 17."""

    @classmethod
    def setUpClass(cls):
        if not os.getenv("DATABASE_URL"):
            raise RuntimeError(
                "Set DATABASE_URL to an isolated test database before running tests "
                "so production/seed data in scatela_db is never touched."
            )

        cls.app = create_app(
            {
                "TESTING": True,
                "SQLALCHEMY_DATABASE_URI": os.environ["DATABASE_URL"],
                "CSRF_ENABLED": True,
                "LOCATION_STALE_SECONDS": 300,
                "SECRET_KEY": "test-secret-key-for-scatela-suite",
            }
        )

    def setUp(self):
        self.ctx = self.app.app_context()
        self.ctx.push()
        db.session.execute(
            text(
                "TRUNCATE TABLE alerts, child_base_status, child_log, "
                "child_emergency_contact, emergency_contact, guardian_child, "
                "bases, child, guardian, users RESTART IDENTITY CASCADE"
            )
        )
        db.session.commit()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        self.ctx.pop()

    # ---------- Helpers ----------

    @staticmethod
    def _extract_csrf_from_html(html_text: str) -> str:
        match = re.search(r'<meta\s+name="csrf-token"\s+content="([^"]+)"', html_text)
        if not match:
            match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html_text)
        if not match:
            raise AssertionError("CSRF token not found in HTML response")
        return match.group(1)

    def _register_guardian(
        self,
        client,
        username="g_alpha",
        email="alpha@example.com",
        phone="5551001000",
        password="password123",
    ):
        page = client.get("/register")
        self.assertEqual(page.status_code, 200)
        csrf = self._extract_csrf_from_html(page.get_data(as_text=True))
        resp = client.post(
            "/register",
            data={
                "csrf_token": csrf,
                "username": username,
                "email": email,
                "phone_number": phone,
                "password": password,
                "confirm_password": password,
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        return self._extract_csrf_from_html(resp.get_data(as_text=True))

    def _login(self, client, identifier: str, password: str):
        page = client.get("/login")
        self.assertEqual(page.status_code, 200)
        csrf = self._extract_csrf_from_html(page.get_data(as_text=True))
        resp = client.post(
            "/login",
            data={
                "csrf_token": csrf,
                "identifier": identifier,
                "password": password,
            },
            follow_redirects=False,
        )
        return resp

    def _get_csrf(self, client, path="/dashboard") -> str:
        resp = client.get(path)
        self.assertEqual(resp.status_code, 200)
        return self._extract_csrf_from_html(resp.get_data(as_text=True))

    # ---------- Tests ----------

    def test_healthz_and_unauthenticated_access(self):
        resp = self.client.get("/healthz")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json(), {"status": "ok"})

        # Web routes redirect to /login
        dash = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(dash.status_code, 302)
        self.assertIn("/login", dash.headers["Location"])

        # API routes return 401
        api_loc = self.client.post("/api/location", json={"latitude": 37.3, "longitude": -121.8})
        self.assertEqual(api_loc.status_code, 401)
        api_dash = self.client.get("/api/dashboard")
        self.assertEqual(api_dash.status_code, 401)

    def test_guardian_registration_login_logout_and_csrf(self):
        csrf = self._register_guardian(self.client)
        user = Users.query.filter_by(username="g_alpha").first()
        self.assertIsNotNone(user)
        self.assertNotEqual(user.password_hash, "password123")
        self.assertIsNotNone(Guardian.query.filter_by(user_id=user.user_id).first())

        # Duplicate email/username rejected
        dup_client = self.app.test_client()
        page = dup_client.get("/register")
        dup_csrf = self._extract_csrf_from_html(page.get_data(as_text=True))
        dup_resp = dup_client.post(
            "/register",
            data={
                "csrf_token": dup_csrf,
                "username": "g_alpha",
                "email": "alpha@example.com",
                "phone_number": "5551001000",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertEqual(dup_resp.status_code, 409)

        # Missing CSRF token on state-changing API call rejected with 403
        bad_post = self.client.post("/api/location", json={"latitude": 37.3, "longitude": -121.8})
        self.assertEqual(bad_post.status_code, 403)

        # Logout with valid CSRF clears session
        logout_resp = self.client.post("/logout", data={"csrf_token": csrf}, follow_redirects=False)
        self.assertEqual(logout_resp.status_code, 302)
        self.assertIn("/login", logout_resp.headers["Location"])

        after_logout = self.client.get("/dashboard", follow_redirects=False)
        self.assertEqual(after_logout.status_code, 302)

        # Bad password fails
        bad_login = self._login(self.client, "g_alpha", "wrongpass")
        self.assertEqual(bad_login.status_code, 401)

        # Valid login via email succeeds and redirects to /dashboard
        ok_login = self._login(self.client, "alpha@example.com", "password123")
        self.assertEqual(ok_login.status_code, 302)
        self.assertIn("/dashboard", ok_login.headers["Location"])

    def test_child_creation_association_and_role_isolation(self):
        csrf = self._register_guardian(self.client, username="g_parent", email="parent@example.com")

        # Create child via /children/add
        resp = self.client.post(
            "/children/add",
            data={
                "csrf_token": csrf,
                "username": "kid_one",
                "email": "kid1@example.com",
                "phone_number": "5552002000",
                "password": "kidpassword1",
                "confirm_password": "kidpassword1",
            },
            follow_redirects=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("kid_one", resp.get_data(as_text=True))

        child_user = Users.query.filter_by(username="kid_one").first()
        self.assertIsNotNone(child_user)
        child_profile = Child.query.filter_by(user_id=child_user.user_id).first()
        self.assertIsNotNone(child_profile)
        self.assertEqual(len(child_profile.guardians), 1)
        self.assertEqual(child_profile.guardians[0].user.username, "g_parent")

        # Child logs in -> redirected to /child, blocked from guardian pages/APIs
        child_client = self.app.test_client()
        login_resp = self._login(child_client, "kid_one", "kidpassword1")
        self.assertEqual(login_resp.status_code, 302)
        self.assertIn("/child", login_resp.headers["Location"])

        self.assertEqual(child_client.get("/dashboard").status_code, 403)
        self.assertEqual(child_client.get("/children/add").status_code, 403)
        self.assertEqual(child_client.get("/api/dashboard").status_code, 403)

    def test_guardian_cannot_access_other_guardian_records(self):
        g1_csrf = self._register_guardian(self.client, username="guardian_a", email="ga@example.com")
        # Guardian A creates a child and a base
        c_resp = self.client.post(
            "/api/children",
            headers={"X-CSRF-Token": g1_csrf},
            json={
                "username": "child_a",
                "email": "ca@example.com",
                "phone_number": "5553003000",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertEqual(c_resp.status_code, 201)
        child_a_id = c_resp.get_json()["child"]["user_id"]

        b_resp = self.client.post(
            "/api/bases",
            headers={"X-CSRF-Token": g1_csrf},
            json={
                "base_name": "Home A",
                "latitude": 37.3382,
                "longitude": -121.8863,
                "warning_radius": 200,
                "danger_radius": 500,
            },
        )
        self.assertEqual(b_resp.status_code, 201)
        base_a_id = b_resp.get_json()["base"]["base_id"]

        # Guardian B logs in
        g2_client = self.app.test_client()
        g2_csrf = self._register_guardian(g2_client, username="guardian_b", email="gb@example.com")

        self.assertEqual(g2_client.get(f"/children/{child_a_id}").status_code, 403)
        self.assertEqual(g2_client.get(f"/api/children/{child_a_id}/logs").status_code, 403)
        self.assertEqual(g2_client.get(f"/api/bases/{base_a_id}").status_code, 403)
        self.assertEqual(
            g2_client.put(
                f"/api/bases/{base_a_id}",
                headers={"X-CSRF-Token": g2_csrf},
                json={
                    "base_name": "Hacked",
                    "latitude": 37.0,
                    "longitude": -121.0,
                    "warning_radius": 100,
                    "danger_radius": 200,
                },
            ).status_code,
            403,
        )
        self.assertEqual(
            g2_client.delete(
                f"/api/bases/{base_a_id}",
                headers={"X-CSRF-Token": g2_csrf},
            ).status_code,
            403,
        )

    def test_base_crud_and_radius_validation(self):
        csrf = self._register_guardian(self.client, username="g_bases", email="gbases@example.com")

        # Invalid radii (danger <= warning) rejected
        bad_base = self.client.post(
            "/api/bases",
            headers={"X-CSRF-Token": csrf},
            json={
                "base_name": "Invalid Base",
                "latitude": 37.3382,
                "longitude": -121.8863,
                "warning_radius": 500,
                "danger_radius": 400,
            },
        )
        self.assertEqual(bad_base.status_code, 400)

        # Valid base created via web form
        add_resp = self.client.post(
            "/bases/add",
            data={
                "csrf_token": csrf,
                "base_name": "School",
                "latitude": "37.338200",
                "longitude": "-121.886300",
                "warning_radius": "150",
                "danger_radius": "400",
            },
            follow_redirects=True,
        )
        self.assertEqual(add_resp.status_code, 200)
        self.assertIn("School", add_resp.get_data(as_text=True))

        base = Bases.query.filter_by(base_name="School").first()
        self.assertIsNotNone(base)

        # Edit base
        edit_resp = self.client.post(
            f"/bases/{base.base_id}/edit",
            data={
                "csrf_token": csrf,
                "base_name": "High School",
                "latitude": "37.339000",
                "longitude": "-121.887000",
                "warning_radius": "200",
                "danger_radius": "600",
            },
            follow_redirects=True,
        )
        self.assertEqual(edit_resp.status_code, 200)
        self.assertIn("High School", edit_resp.get_data(as_text=True))

        # Delete base
        del_resp = self.client.post(
            f"/bases/{base.base_id}/delete",
            data={"csrf_token": csrf},
            follow_redirects=True,
        )
        self.assertEqual(del_resp.status_code, 200)
        self.assertIsNone(Bases.query.filter_by(base_id=base.base_id).first())

    def test_location_updates_by_role_history_and_spoof_prevention(self):
        g_csrf = self._register_guardian(self.client, username="g_loc", email="gloc@example.com")
        g_user = Users.query.filter_by(username="g_loc").first()

        # Create child
        c_resp = self.client.post(
            "/api/children",
            headers={"X-CSRF-Token": g_csrf},
            json={
                "username": "c_loc",
                "email": "cloc@example.com",
                "phone_number": "5554004000",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        child_id = c_resp.get_json()["child"]["user_id"]

        # Guardian posts multiple location updates (even attempting spoofed user_id!)
        for lat, lon in [(37.3382, -121.8863), (37.3385, -121.8865)]:
            loc_resp = self.client.post(
                "/api/location",
                headers={"X-CSRF-Token": g_csrf},
                json={"user_id": child_id, "latitude": lat, "longitude": lon},
            )
            self.assertEqual(loc_resp.status_code, 200)
            self.assertEqual(loc_resp.get_json()["role"], "guardian")

        # Still only 1 guardian record, updated in place, and child was NOT modified
        self.assertEqual(Guardian.query.count(), 1)
        g_profile = Guardian.query.filter_by(user_id=g_user.user_id).first()
        self.assertAlmostEqual(g_profile.latitude, 37.3385)
        self.assertIsNotNone(g_profile.location_updated_at)

        c_profile = Child.query.filter_by(user_id=child_id).first()
        self.assertIsNone(c_profile.latitude)
        self.assertEqual(Child_Log.query.filter_by(child_id=child_id).count(), 0)

        # Invalid coordinates rejected
        bad_lat = self.client.post(
            "/api/location",
            headers={"X-CSRF-Token": g_csrf},
            json={"latitude": 95.0, "longitude": -121.0},
        )
        self.assertEqual(bad_lat.status_code, 400)

        # Child logs in and sends 3 updates -> 1 child row updated, 3 child_log rows created
        child_client = self.app.test_client()
        self._login(child_client, "c_loc", "password123")
        c_csrf = self._get_csrf(child_client, "/child")

        for lat, lon in [(37.3382, -121.8863), (37.3392, -121.8863), (37.3402, -121.8863)]:
            resp = child_client.post(
                "/api/location",
                headers={"X-CSRF-Token": c_csrf},
                json={"latitude": lat, "longitude": lon},
            )
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(resp.get_json()["role"], "child")

        self.assertEqual(Child.query.count(), 1)
        c_profile = Child.query.filter_by(user_id=child_id).first()
        self.assertAlmostEqual(c_profile.latitude, 37.3402)
        self.assertEqual(Child_Log.query.filter_by(child_id=child_id).count(), 3)

    def test_haversine_multi_base_monitoring_alert_deduplication_and_staleness(self):
        # Verify Haversine & thresholds directly
        self.assertAlmostEqual(haversine_distance_meters(37.3382, -121.8863, 37.3382, -121.8863), 0.0)
        self.assertEqual(evaluate_threshold(100, 200, 500), "normal")
        self.assertEqual(evaluate_threshold(200, 200, 500), "normal")
        self.assertEqual(evaluate_threshold(201, 200, 500), "warning")
        self.assertEqual(evaluate_threshold(500, 200, 500), "warning")
        self.assertEqual(evaluate_threshold(501, 200, 500), "danger")

        g_csrf = self._register_guardian(self.client, username="g_mon", email="gmon@example.com")

        # Guardian creates child and two bases (Home & Park ~556m apart north-south)
        c_resp = self.client.post(
            "/api/children",
            headers={"X-CSRF-Token": g_csrf},
            json={
                "username": "c_mon",
                "email": "cmon@example.com",
                "phone_number": "5555005000",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        child_id = c_resp.get_json()["child"]["user_id"]

        # Base 1: Home at (37.3382, -121.8863), warn=200m, danger=500m
        b1_resp = self.client.post(
            "/api/bases",
            headers={"X-CSRF-Token": g_csrf},
            json={
                "base_name": "Home",
                "latitude": 37.3382,
                "longitude": -121.8863,
                "warning_radius": 200,
                "danger_radius": 500,
            },
        )
        home_id = b1_resp.get_json()["base"]["base_id"]

        # Base 2: Park at (37.3432, -121.8863) (~556m north of Home), warn=200m, danger=500m
        b2_resp = self.client.post(
            "/api/bases",
            headers={"X-CSRF-Token": g_csrf},
            json={
                "base_name": "Park",
                "latitude": 37.3432,
                "longitude": -121.8863,
                "warning_radius": 200,
                "danger_radius": 500,
            },
        )
        park_id = b2_resp.get_json()["base"]["base_id"]

        child_client = self.app.test_client()
        self._login(child_client, "c_mon", "password123")
        c_csrf = self._get_csrf(child_client, "/child")

        # 1) Child at Home (0m from Home -> normal; ~556m from Park -> danger)
        # Highest severity should be 'danger', and Park generates 1 danger alert.
        r1 = child_client.post(
            "/api/location",
            headers={"X-CSRF-Token": c_csrf},
            json={"latitude": 37.3382, "longitude": -121.8863},
        )
        self.assertEqual(r1.status_code, 200)
        dash1 = self.client.get("/api/dashboard").get_json()
        self.assertEqual(dash1["children"][0]["monitoring_status"], "danger")
        self.assertEqual(Alert.query.filter_by(is_active=True).count(), 1)
        self.assertEqual(Alert.query.filter_by(base_id=park_id, is_active=True).count(), 1)

        # 2) Child moves ~300m north (37.3409, -121.8863):
        #    - ~300m from Home -> warning (Home transitions normal -> warning => NEW alert!)
        #    - ~256m from Park -> warning (Park transitions danger -> warning => NEW alert!)
        r2 = child_client.post(
            "/api/location",
            headers={"X-CSRF-Token": c_csrf},
            json={"latitude": 37.3409, "longitude": -121.8863},
        )
        self.assertEqual(r2.status_code, 200)
        dash2 = self.client.get("/api/dashboard").get_json()
        self.assertEqual(dash2["children"][0]["monitoring_status"], "warning")
        self.assertEqual(Alert.query.filter_by(is_active=True).count(), 2)

        # 3) Repeat tick in exact same state (~301m from Home, ~255m from Park) -> NO duplicate alerts!
        before_count = Alert.query.count()
        r3 = child_client.post(
            "/api/location",
            headers={"X-CSRF-Token": c_csrf},
            json={"latitude": 37.34091, "longitude": -121.8863},
        )
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(Alert.query.count(), before_count)

        # 4) Child moves far away (37.3600, -121.8863) -> both Home and Park become danger!
        r4 = child_client.post(
            "/api/location",
            headers={"X-CSRF-Token": c_csrf},
            json={"latitude": 37.3600, "longitude": -121.8863},
        )
        self.assertEqual(r4.status_code, 200)
        active_danger = Alert.query.filter_by(is_active=True, alert_type="danger").all()
        self.assertEqual(len(active_danger), 2)

        # Acknowledge 1 alert; next 10s update in same danger state must NOT re-emit it
        ack_resp = self.client.post(
            f"/api/alerts/{active_danger[0].alert_id}/acknowledge",
            headers={"X-CSRF-Token": g_csrf},
        )
        self.assertEqual(ack_resp.status_code, 200)
        self.assertEqual(Alert.query.filter_by(is_active=True).count(), 1)

        r5 = child_client.post(
            "/api/location",
            headers={"X-CSRF-Token": c_csrf},
            json={"latitude": 37.3601, "longitude": -121.8863},
        )
        self.assertEqual(r5.status_code, 200)
        self.assertEqual(Alert.query.filter_by(is_active=True).count(), 1)

        # 5) Stale timestamp rejected by /api/location
        stale_ts = (datetime.now(timezone.utc) - timedelta(minutes=20)).isoformat()
        stale_post = child_client.post(
            "/api/location",
            headers={"X-CSRF-Token": c_csrf},
            json={"latitude": 37.3382, "longitude": -121.8863, "timestamp": stale_ts},
        )
        self.assertEqual(stale_post.status_code, 400)

        # 6) If stored child timestamp becomes stale, dashboard reports 'stale' and guardian update does not fire alerts
        c_row = Child.query.filter_by(user_id=child_id).first()
        c_row.location_updated_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=15)
        db.session.commit()

        count_before_stale_eval = Alert.query.count()
        g_loc = self.client.post(
            "/api/location",
            headers={"X-CSRF-Token": g_csrf},
            json={"latitude": 37.3382, "longitude": -121.8863},
        )
        self.assertEqual(g_loc.status_code, 200)
        self.assertEqual(Alert.query.count(), count_before_stale_eval)
        dash_stale = self.client.get("/api/dashboard").get_json()
        self.assertEqual(dash_stale["children"][0]["monitoring_status"], "stale")
        self.assertFalse(dash_stale["children"][0]["location_fresh"])

    def test_pages_render_geocode_and_tracking_script_gating(self):
        # Unauthenticated login/register pages must NOT load location_tracker.js
        login_html = self.client.get("/login").get_data(as_text=True)
        self.assertNotIn("location_tracker.js", login_html)
        register_html = self.client.get("/register").get_data(as_text=True)
        self.assertNotIn("location_tracker.js", register_html)

        # Authenticated guardian dashboard loads location_tracker.js & dashboard.js
        csrf = self._register_guardian(self.client, username="g_ui", email="gui@example.com")
        dash_html = self.client.get("/dashboard").get_data(as_text=True)
        self.assertIn("location_tracker.js", dash_html)
        self.assertIn("dashboard.js", dash_html)
        self.assertIn("Add Child", dash_html)
        self.assertIn("Add Base Location", dash_html)

        # Base add page renders Leaflet & base_map.js
        base_add_html = self.client.get("/bases/add").get_data(as_text=True)
        self.assertIn("base_map.js", base_add_html)
        self.assertIn("address-search-input", base_add_html)

        # Geocode validation rejects short query
        bad_geo = self.client.get("/api/geocode?q=a")
        self.assertEqual(bad_geo.status_code, 400)

        # Geocode works with mocked Nominatim response
        from unittest.mock import MagicMock, patch

        fake_resp = MagicMock()
        fake_resp.read.return_value = b'[{"display_name": "San Jose City Hall", "lat": "37.3382", "lon": "-121.8863"}]'
        fake_ctx = MagicMock()
        fake_ctx.__enter__.return_value = fake_resp
        fake_ctx.__exit__.return_value = False

        with patch("backend.services.geocode_service.urllib.request.urlopen", return_value=fake_ctx):
            geo_ok = self.client.get("/api/geocode?q=San+Jose+City+Hall")
            self.assertEqual(geo_ok.status_code, 200)
            results = geo_ok.get_json()["results"]
            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["display_name"], "San Jose City Hall")
            self.assertAlmostEqual(results[0]["latitude"], 37.3382)

        # Create child & log location -> detail page & API logs show entry
        c_resp = self.client.post(
            "/api/children",
            headers={"X-CSRF-Token": csrf},
            json={
                "username": "c_ui",
                "email": "cui@example.com",
                "phone_number": "5556006000",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        child_id = c_resp.get_json()["child"]["user_id"]

        # Duplicate child email prevented
        dup_child = self.client.post(
            "/api/children",
            headers={"X-CSRF-Token": csrf},
            json={
                "username": "c_ui2",
                "email": "cui@example.com",
                "phone_number": "5556006001",
                "password": "password123",
                "confirm_password": "password123",
            },
        )
        self.assertEqual(dup_child.status_code, 409)

        child_client = self.app.test_client()
        self._login(child_client, "c_ui", "password123")
        child_page_html = child_client.get("/child").get_data(as_text=True)
        self.assertIn("location_tracker.js", child_page_html)
        c_csrf = self._extract_csrf_from_html(child_page_html)

        child_client.post(
            "/api/location",
            headers={"X-CSRF-Token": c_csrf},
            json={"latitude": 37.3382, "longitude": -121.8863},
        )

        detail_html = self.client.get(f"/children/{child_id}").get_data(as_text=True)
        self.assertEqual(self.client.get(f"/children/{child_id}").status_code, 200)
        self.assertIn("37.338200", detail_html)
        logs_json = self.client.get(f"/api/children/{child_id}/logs").get_json()
        self.assertEqual(len(logs_json["logs"]), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
