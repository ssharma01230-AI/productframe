import argparse
import time

from dotenv import load_dotenv

from .worker import QUEUE, process_job, run_once
from productframe_api.config import get_settings
from redis import Redis


def main() -> None:
    load_dotenv()
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    enqueue = subparsers.add_parser("enqueue")
    enqueue.add_argument("job_id")
    subparsers.add_parser("run-once")
    subparsers.add_parser("run")
    args = parser.parse_args()
    settings = get_settings()
    if args.command == "enqueue":
        redis = Redis.from_url(settings.redis_url)
        redis.lpush(QUEUE, args.job_id)
        redis.close()
        print(f"Queued analysis job {args.job_id}")
    elif args.command == "run-once":
        print("Processed a job." if run_once() else "No queued jobs.")
    else:
        print("Worker listening for analysis jobs...")
        while True:
            run_once()
            time.sleep(1)
