"""User View tests."""

# run these tests like:
#
#    FLASK_DEBUG=False python -m unittest test_message_views.py


import os
from unittest import TestCase

from models import db, Message, User, DEFAULT_IMAGE_URL, DEFAULT_HEADER_IMAGE_URL

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ["DATABASE_URL"] = "postgresql:///warbler_test"

# Now we can import app

from app import app, CURR_USER_KEY

app.config["DEBUG_TB_INTERCEPT_REDIRECTS"] = False

# This is a bit of hack, but don't use Flask DebugToolbar

app.config["DEBUG_TB_HOSTS"] = ["dont-show-debug-toolbar"]

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config["WTF_CSRF_ENABLED"] = False


class UserBaseViewTestCase(TestCase):
    def setUp(self):
        User.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", None)
        u2 = User.signup("u2", "u2@email.com", "password", None)

        db.session.flush()

        m1 = Message(text="m1-text", user_id=u1.id)
        db.session.add_all([m1])
        db.session.commit()

        self.u1_id = u1.id
        self.u2_id = u2.id
        self.m1_id = m1.id

    def tearDown(self):
        db.session.rollback()


class UserShowHomeTestCase(UserBaseViewTestCase):
    """Show Homepage Test Cases"""

    def test_get_anon_homepage(self):
        """Show anon-homepage if not logged in"""

        with app.test_client() as client:
            resp = client.get("/")
            html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("This comment is for testing the home-anon.html", html)

    def test_get_logged_in_homepage(self):
        """Show homepage with warbles if logged in"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get("/")
            html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("This comment is for testing the home.html", html)


class UserShowLoginAndSignupFormsTestCase(UserBaseViewTestCase):
    """Show Signup and Login Pages Tests"""

    def test_logged_in_redirect_to_homepage(self):
        """Redirect to homepage if logged in and access /login"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get("/login", follow_redirects=True)
            html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("This comment is for testing the home.html", html)
        # TODO: add test for displaying correct information on page for user

    def test_get_login_page(self):
        """Redirect to homepage if logged in and and try to access /login"""
        with app.test_client() as c:
            resp = c.get("/login")
            html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "This comment is for testing showing /login.html page",
            html,
        )

    def test_get_signup_page(self):
        """display signup page if logged out"""
        with app.test_client() as c:
            resp = c.get("/signup")
            html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "This comment is for testing showing /signup.html page",
            html,
        )

    def test_logged_in_redirect_signup_page(self):
        """redirect from signup page if logged in"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

            resp = c.get("/signup", follow_redirects=True)
            html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "This comment is for testing the home.html",
            html,
        )

    # TODO: setup post test


class UserLogoutViewTestCase(UserBaseViewTestCase):
    """Logout View Test Cases"""

    def test_logout_route(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id
            resp = c.post("/logout", follow_redirects=True)
            html = resp.get_data(as_text=True)

            # TODO: Check status code 200
            self.assertIn("Logged out, Going so soon :(", html)


class GeneralUserViewTestCases(UserBaseViewTestCase):
    """General view Test Cases"""

    def test_list_users_all(self):
        """Get page of existing users"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = c.get("/users", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "This comment is for testing showing /index.html page",
            html,
        )
        self.assertIn("@u1", html)
        self.assertIn("@u2", html)

    def test_list_users_filter(self):
        """Get page of filtered existing users"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u1_id

        resp = c.get("/users?q=u2", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "This comment is for testing showing /index.html page",
            html,
        )
        self.assertNotIn("@u1", html)
        self.assertIn("@u2", html)

    def test_list_users_logged_out(self):
        """Can't see users list if not logged in"""
        with app.test_client() as c:
            resp = c.get("/users", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized.", html)


class UserShowLikeViewTestCase(UserBaseViewTestCase):
    """Show Likes Test Cases"""

    def test_show_likes(self):
        """Show likes of a user when logged in"""
        m2 = Message(text="m2-text", user_id=self.u1_id)
        db.session.add(m2)
        u2 = User.query.get(self.u2_id)
        u2.likes.append(m2)
        db.session.commit()

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.get(f"/users/{self.u2_id}/likes")

            self.assertEqual(resp.status_code, 200)

            html = resp.get_data(as_text=True)

            self.assertIn(m2.text, html)
            self.assertIn(
                "This comment for testing routes involving user/likes.html",
                html,
            )

    def test_show_likes_bad_not_loggedin(self):
        """Can't see a user's likes if not logged in"""

        with app.test_client() as c:
            resp = c.get(f"/users/{self.u2_id}/likes", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)

            html = resp.get_data(as_text=True)

            self.assertIn(
                "Access unauthorized.",
                html,
            )

    # TODO: test for liking own message


class UserShowUserViewTestCase(UserBaseViewTestCase):
    """Testing show_user view function"""

    def test_show_user_profile_good(self):
        """Can view other user profile"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.get(f"/users/{self.u1_id}")

            self.assertEqual(resp.status_code, 200)

            html = resp.get_data(as_text=True)

            self.assertIn(
                "<!--This comment for testing of user/show.html-->",
                html,
            )

            m1 = Message.query.get(self.m1_id)

            self.assertIn(f"{m1.text}", html)

    def test_show_user_bad_not_loggedin(self):
        """Can't see a user's profile if not logged in"""

        with app.test_client() as c:
            resp = c.get(f"/users/{self.u2_id}", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)

            html = resp.get_data(as_text=True)

            self.assertIn(
                "Access unauthorized.",
                html,
            )

    # TODO: test user that doesnt exist


class UserShowUserFollowingAndFollowersViewTestCases(UserBaseViewTestCase):
    """Testing view functions related to following and follwers
    stop_following
    start_following
    show_followers
    show_following
    """

    def test_stop_following_bad_not_loggedin(self):
        """Can't stop following someone if not logged in"""

        with app.test_client() as c:
            resp = c.post(f"/users/stop-following/{self.u2_id}", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                "Access unauthorized.",
                html,
            )

    def test_start_following_bad_not_loggedin(self):
        """Can't start following if not logged in"""

        with app.test_client() as c:
            resp = c.post(f"/users/follow/{self.u2_id}", follow_redirects=True)

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                "Access unauthorized.",
                html,
            )

    def test_all_for_404_when_user_does_not_exist(self):
        """Test 404 when user id to follow/stop following/show
        followers/show following does not exist"""
        # TODO: break up test
        # Start Follow
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.post(f"/users/follow/0")
            self.assertEqual(resp.status_code, 404)

        # Stop following
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.post(f"/users/stop-following/0")
            self.assertEqual(resp.status_code, 404)

        # Show Followers
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.get(f"/users/0/followers")
            self.assertEqual(resp.status_code, 404)

        # Show Following
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.get(f"/users/0/following")
            self.assertEqual(resp.status_code, 404)

    def test_start_following_good(self):
        """Test start_following good case"""

        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.post(f"/users/follow/{self.u1_id}")

            self.assertEqual(resp.status_code, 302)

            u2 = User.query.get(self.u2_id)
            u1 = User.query.get(self.u1_id)

            self.assertIn(u1, u2.following)

    def test_start_stop_following_good(self):
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.post(f"/users/follow/{self.u1_id}")

            self.assertEqual(resp.status_code, 302)

            u2 = User.query.get(self.u2_id)
            u1 = User.query.get(self.u1_id)

            self.assertIn(u1, u2.following)

            resp = c.post(f"/users/stop-following/{self.u1_id}")

            u2 = User.query.get(self.u2_id)
            u1 = User.query.get(self.u1_id)

            self.assertNotIn(u1, u2.following)

    # TODO: Clear up definition
    def test_stop_following_bad_user_not_following(self):
        """Test stop following bad case where they were not following the user before"""
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            with self.assertRaises(ValueError):
                c.post(f"/users/stop-following/{self.u1_id}")

    def test_show_following_good(self):
        # TODO: Docstring
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.get(f"/users/{self.u1_id}/following")

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                "This comment for testing of routes using following.html",
                html,
            )
            # TODO: check for u1 following names

    def test_show_following_bad_not_loggedin(self):
        """Can't see who a user follows if not logged in"""

        with app.test_client() as c:
            resp = c.get(f"/users/{self.u2_id}/following", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)

            html = resp.get_data(as_text=True)

            self.assertIn(
                "Access unauthorized.",
                html,
            )

    def test_show_followers_good(self):
        # TODO: docstring
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.get(f"/users/{self.u1_id}/followers")

            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(
                "This comment for testing of routes using followers.html",
                html,
            )
            # TODO: check for u1 followers names

    def test_show_followers_bad_not_loggedin(self):
        """Can't see who follows a user when not logged in"""

        with app.test_client() as c:
            resp = c.get(f"/users/{self.u2_id}/followers", follow_redirects=True)

            self.assertEqual(resp.status_code, 200)

            html = resp.get_data(as_text=True)

            self.assertIn(
                "Access unauthorized.",
                html,
            )


class UserDeleteAndEditRouteViewTestCases(UserBaseViewTestCase):
    """Delete and Edit Route Tests"""

    #############################################################
    # Delete tests
    def test_user_delete_logged_in(self):
        # TODO: docstrings
        with app.test_client() as c:
            u2 = User.query.get(self.u2_id)
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.u2_id

            resp = c.post("/users/delete", follow_redirects=True)

            html = resp.get_data(as_text=True)

        users = User.query.all()

        self.assertEqual(resp.status_code, 200)
        self.assertIn("User successfully deleted", html)
        self.assertNotIn(u2, users)

    def test_user_delete_not_logged_in(self):
        # TODO: docstrings
        with app.test_client() as c:
            resp = c.post("/users/delete", follow_redirects=True)

            html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("Access unauthorized.", html)

    # TODO: cant delete someone else

    # #############################################################
    # # Edit tests

    # def test_user_edit_profile(self):
    #     with app.test_client() as c:
    #         with c.session_transaction() as sess:
    #             sess[CURR_USER_KEY] = self.u2_id

    #             u2 = User.query.get(self.u2_id)
    #             resp = c.post(
    #                 "/users/profile",
    #                 data={
    #                     "username": "testusername",
    #                     "email": "newemail@test.com",
    #                     "location": "test location",
    #                     "password": u2.password,
    #                 },
    #                 follow_redirects=True,
    #             )

    #         testuser = User.query.get(self.u2_id)
    #         users = User.query.all()

    #     self.assertEqual(resp.status_code, 200)
    #     self.assertIn(testuser, users)
    #     self.assertNotEqual(u2, testuser)

    # def test_user_edit_profile_bad(self):
    #     with app.test_client() as c:
    #         with c.session_transaction() as sess:
    #             sess[CURR_USER_KEY] = self.u2_id

    #             resp = c.post(
    #                 "/users/profile",
    #                 data={
    #                     "username": "testusername",
    #                     "email": "newemail@test.com",
    #                     "location": "test location",
    #                     "password": "wrongpassword",
    #                 },
    #                 follow_redirects=True,
    #             )
    #             db.session.commit()

    #         html = resp.get_data(as_text=True)
    #         testuser = User.query.get(self.u2_id)
    #         users = User.query.all()

    #     self.assertEqual(resp.status_code, 200)
    #     self.assertIn(testuser, users)
    #     self.assertIn("Invalid password", html)
