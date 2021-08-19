"""Message View tests."""

# run these tests like:
#
# FLASK_ENV=production python -m unittest test_message_views.py

import os

# Set database url to the warbler-test database.
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

from app import app, CURR_USER_KEY
from unittest import TestCase
from models import db, connect_db, Message, User

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
        self.testuser_id = 4
        self.testuser.id = self.testuser_id

        db.session.commit()

    def test_add_message(self):
        """Can use add a message?"""

        with self.client as client:
            # Allow for changes to session for logging in.
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = client.post("/messages/new", data={"text": "Hello"})

            # Ensure redirects.
            self.assertEqual(resp.status_code, 302)
            
            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_add_no_session(self):
        with self.client as client:
            resp = client.post("/messages/new",
                          data={"text": "Hello"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_add_invalid_user(self):
        with self.client as client:
            with client.session_transaction() as sess:
                # Set current user to a non-existent user.
                sess[CURR_USER_KEY] = 100

            resp = client.post("/messages/new",
                          data={"text": "Hello"}, follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

    def test_message_show(self):

        msg = Message(
            id=100,
            text="test message",
            user_id=self.testuser_id
        )

        db.session.add(msg)
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            q_msg = Message.query.get(100)

            resp = client.get(f'/messages/{q_msg.id}')

            self.assertEqual(resp.status_code, 200)
            self.assertIn(q_msg.text, str(resp.data))

    def test_invalid_message_show(self):
        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = client.get('/messages/99999999')

            self.assertEqual(resp.status_code, 404)

    def test_message_delete(self):

        msg = Message(
            id=100,
            text="test message",
            user_id=self.testuser_id
        )
        db.session.add(msg)
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = client.post("/messages/100/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)

            q_msg = Message.query.get(100)
            self.assertIsNone(q_msg)

    def test_unauthorized_message_delete(self):

        # A second user that will try to delete the message
        user = User.signup(username="unauth-user",
                        email="testtest@test.com",
                        password="password",
                        image_url=None)
        user.id = 5000

        #Message is owned by testuser
        msg = Message(
            id=111,
            text="test message",
            user_id=self.testuser_id
        )
        db.session.add_all([user, msg])
        db.session.commit()

        with self.client as client:
            with client.session_transaction() as sess:
                sess[CURR_USER_KEY] = 5000

            resp = client.post("/messages/111/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

            q_msg = Message.query.get(111)
            self.assertIsNotNone(q_msg)

    def test_message_delete_no_authentication(self):

        msg = Message(
            id=999,
            text="test message",
            user_id=self.testuser_id
        )
        db.session.add(msg)
        db.session.commit()

        with self.client as client:
            resp = client.post("/messages/999/delete", follow_redirects=True)
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Access unauthorized", str(resp.data))

            q_msg = Message.query.get(999)
            self.assertIsNotNone(q_msg)
