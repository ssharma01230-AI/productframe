import argparse
import logging
import multiprocessing
import os
import time

from dotenv import load_dotenv

from .worker import QUEUE, process_job, run_once
from productframe_api.config import get_settings
from redis import Redis

logger = logging.getLogger(__name__)


def _worker_loop() -> None:
    """Run one isolated Redis consumer in its own process."""
    while True:
        try:
            run_once()
        except Exception as exc:
            # run_once records and acknowledges individual job failures.
            # This catch is for infrastructure failures such as Redis or
            # database outages; avoid logging raw provider responses.
            logger.error("Worker loop failed (%s); continuing to listen for jobs.", type(exc).__name__)
        time.sleep(1)


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
    run = subparsers.add_parser("run")
    run.add_argument("--workers", type=int, default=max(1, int(os.environ.get("GENERATION_WORKERS", "1"))))
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
        if args.workers < 1:
            parser.error("--workers must be at least 1")
        print(f"Worker listening for analysis and generation jobs ({args.workers} consumer{'s' if args.workers != 1 else ''})...")
        if args.workers == 1:
            _worker_loop()
        context = multiprocessing.get_context("spawn")
        workers = [context.Process(target=_worker_loop, name=f"productframe-worker-{index + 1}") for index in range(args.workers)]
        for worker in workers:
            worker.start()
        try:
            for worker in workers:
                worker.join()
        except BaseException:
            for worker in workers:
                if worker.is_alive():
                    worker.terminate()
            for worker in workers:
                worker.join()
            raise
