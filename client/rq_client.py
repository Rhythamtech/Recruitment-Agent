from redis import Redis
from dotenv import load_dotenv
from rq import Queue
import os

load_dotenv()

redis_url = os.getenv("REDIS_URL")
queue = Queue(connection=Redis.from_url(redis_url))