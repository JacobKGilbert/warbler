"""User View tests."""

# run these tests like:
#
# FLASK_ENV=production python -m unittest test_message_views.py

import os

# Set database url to the warbler-test database.
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

from app import app, CURR_USER_KEY
from unittest import TestCase
from models import db, connect_db, Message, User, Likes, Follows

# Create all tables for tests.

db.create_all()

# Prevent WTForms from using CSRF and debug from intercepting redirects.
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        db.drop_all()
        db.create_all()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser_id = 89
        self.testuser.id = self.testuser_id

        self.user1 = User.signup("abc", "test1@test.com", "password", None)
        self.user1_id = 77
        self.user1.id = self.user1_id
        self.user2 = User.signup("efg", "test2@test.com", "password", None)
        self.user2_id = 88
        self.user2.id = self.user2_id
        self.user3 = User.signup("hij", "test3@test.com", "password", None)
        self.user4 = User.signup("testing", "test4@test.com", "password", None)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_users_index(self):
        with self.client as client:
            resp = client.get("/users")

            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertIn("@hij", str(resp.data))
            self.assertIn("@testing", str(resp.data))

    def test_users_search(self):
        with self.client as client:
            resp = client.get("/users?q=test")

            self.assertIn("@testuser", str(resp.data))
            self.assertIn("@testing", str(resp.data))

            self.assertNotIn("@abc", str(resp.data))
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))

    def test_user_show(self):
        with self.client as client:
            resp = client.get(f"/users/{self.testuser_id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))

    def setup_likes(self):
        msg1 = Message(text="trending warble", user_id=self.testuser_id)
        msg2 = Message(text="Eating some lunch", user_id=self.testuser_id)
        msg3 = Message(id=9876, text="likable warble", user_id=self.user1_id)
        db.session.add_all([msg1, msg2, msg3])
        db.session.commit()

        like1 = Likes(user_id=self.testuser_id, message_id=9876)

        db.session.add(like1)
        db.session.commit()

    def test_user_show_with_likes(self):
        self.setup_likes()

        with self.client as client:
            resp = client.get(f"/users/{self.testuser_id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))

    def test_add_like(self):
        msg = Message(id=1984, text="The earth is round", user_id=self.user1_id)
        db.session.add(msg)
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = client.post("/users/add_like/1984",
                               follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id == 1984).all()
            self.assertEqual(len(likes), 1)
            self.assertEqual(likes[0].user_id, self.testuser_id)

    def test_remove_like(self):
        self.setup_likes()

        msg = Message.query.filter(Message.text == "likable warble").one()
        self.assertIsNotNone(msg)
        self.assertNotEqual(msg.user_id, self.testuser_id)

        like = Likes.query.filter(
            Likes.user_id == self.testuser_id and Likes.message_id == msg.id
        ).one()

        self.assertIsNotNone(like)

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = client.post(
                f"/users/remove_like/{msg.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            likes = Likes.query.filter(Likes.message_id == msg.id).all()
            # the like has been deleted
            self.assertEqual(len(likes), 0)

    def test_unauthenticated_like(self):
        self.setup_likes()

        msg = Message.query.filter(Message.text == "likable warble").one()
        self.assertIsNotNone(msg)

        like_count = Likes.query.count()

        with self.client as client:
            resp = client.post(
                f"/users/add_like/{msg.id}", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            self.assertIn("Access unauthorized", str(resp.data))

            # The number of likes has not changed since making the request
            self.assertEqual(like_count, Likes.query.count())

    def setup_followers(self):
        follow1 = Follows(user_being_followed_id=self.user1_id,
                     user_following_id=self.testuser_id)
        follow2 = Follows(user_being_followed_id=self.user2_id,
                     user_following_id=self.testuser_id)
        follow3 = Follows(user_being_followed_id=self.testuser_id,
                     user_following_id=self.user1_id)

        db.session.add_all([follow1, follow2, follow3])
        db.session.commit()

    def test_user_show_with_follows(self):

        self.setup_followers()

        with self.client as client:
            resp = client.get(f"/users/{self.testuser_id}")

            self.assertEqual(resp.status_code, 200)

            self.assertIn("@testuser", str(resp.data))
            
    def test_show_following(self):

        self.setup_followers()
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = client.get(f"/users/{self.testuser_id}/following")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("@abc", str(resp.data))
            self.assertIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_show_followers(self):

        self.setup_followers()
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser_id

            resp = client.get(f"/users/{self.testuser_id}/followers")

            self.assertIn("@abc", str(resp.data))
            self.assertNotIn("@efg", str(resp.data))
            self.assertNotIn("@hij", str(resp.data))
            self.assertNotIn("@testing", str(resp.data))

    def test_unauthorized_following_page_access(self):
        self.setup_followers()
        with self.client as client:

            resp = client.get(
                f"/users/{self.testuser_id}/following", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))

    def test_unauthorized_followers_page_access(self):
        self.setup_followers()
        with self.client as client:

            resp = client.get(
                f"/users/{self.testuser_id}/followers", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertNotIn("@abc", str(resp.data))
            self.assertIn("Access unauthorized", str(resp.data))
