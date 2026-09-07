import argparse
import logging
import time

from dotenv import load_dotenv

from .worker import QUEUE, process_job, run_once
from productframe_api.config import get_settings
from redis import Redis

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for name in ("httpx", "httpcore", "urllib3", "openai", "botocore"):
        logging.getLogger(name).setLevel(logging.WARNING)
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
        redis = Redis.from_url(settings.redis_url, decode_responses=True)
        redis.xadd(QUEUE, {"type": "analyse", "job_id": args.job_id}, maxlen=10000, approximate=True)
        redis.close()
        print(f"Queued analysis job {args.job_id}")
    elif args.command == "run-once":
        print("Processed a job." if run_once() else "No queued jobs.")
    else:
        print("Worker listening for analysis jobs...")
        while True:
            try:
                run_once()
            except Exception as exc:
                # process_job records the failure. Avoid logging raw provider
                # exceptions, which may contain request data or credentials.
                logger.error("Analysis job processing failed (%s); continuing to listen for jobs.", type(exc).__name__)
            time.sleep(1)
