"""Message model tests."""

# run these tests with:
#
# python -m unittest test_message_model.py

import os

# Set database url to the warbler-test database.
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

from app import app
from unittest import TestCase
from sqlalchemy import exc
from models import db, User, Message, Follows, Likes

# Create all tables for tests.

db.create_all()


class UserModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""
        db.drop_all()
        db.create_all()

        
        user = User.signup("Test User", "test@test.com", "password", None)
        db.session.commit()

        self.user_id = user.id
        self.user = User.query.get(self.user_id)

        self.client = app.test_client()

    def tearDown(self):
        res = super().tearDown()
        db.session.rollback()
        return res

    def test_message_model(self):
        """Does basic model work?"""

        msg = Message(
            text="test message",
            user_id=self.user_id
        )

        db.session.add(msg)
        db.session.commit()

        # User should have 1 message
        self.assertEqual(len(self.user.messages), 1)
        self.assertEqual(self.user.messages[0].text, "test message")

    def test_message_likes(self):
        msg1 = Message(
            text="another test message",
            user_id=self.user_id
        )

        msg2 = Message(
            text="wait... another...?",
            user_id=self.user_id
        )

        second_user = User.signup("Test User2", "test@email.com", "passw0rd", None)
        user_id = 5
        second_user.id = user_id
        db.session.add_all([msg1, msg2, second_user])
        db.session.commit()

        second_user.likes.append(msg1)

        db.session.commit()

        likes = Likes.query.filter(Likes.user_id == user_id).all()
        self.assertEqual(len(likes), 1)
        self.assertEqual(likes[0].message_id, msg1.id)
