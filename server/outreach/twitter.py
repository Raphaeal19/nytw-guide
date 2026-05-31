import tweepy
from server.config import settings


def _client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=settings.twitter_api_key,
        consumer_secret=settings.twitter_api_secret,
        access_token=settings.twitter_access_token,
        access_token_secret=settings.twitter_access_token_secret,
    )


def send_twitter_dm(username: str, message: str) -> bool:
    client = _client()
    # Resolve handle to user ID
    user = client.get_user(username=username.lstrip("@"))
    if not user.data:
        raise ValueError(f"Twitter user not found: {username}")
    client.create_direct_message(participant_id=user.data.id, text=message)
    return True
