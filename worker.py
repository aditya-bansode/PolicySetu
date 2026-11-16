"""
PolicySetu — Background Policy Monitoring Worker
================================================
Independent worker process executing automated government policy scans
on a strict 15-minute interval via APScheduler.

Usage:
  python worker.py              # Starts the 15-minute automated scheduler
  python worker.py --scan       # Executes an immediate single monitoring cycle and exits
  python worker.py --source pib # Runs scan for a specific source and exits
"""

import os
import sys
import time
import signal
import logging
import argparse
from typing import Optional

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Setup logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join("data", "worker.log"), encoding="utf-8")
    ]
)
logger = logging.getLogger("policysetu.worker")

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app import create_app
from app.services.monitoring_engine import PolicyMonitoringEngine
from app.models.source import GovernmentSource

LOCK_FILE = os.path.join("data", "worker.lock")


def acquire_process_lock() -> bool:
    """
    Ensure only one worker process runs at any given time.
    """
    os.makedirs("data", exist_ok=True)
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    old_pid = int(content)
                    # Check if process is genuinely alive
                    import psutil
                    if psutil.pid_exists(old_pid):
                        logger.error(f"Worker process already active with PID {old_pid}. Aborting duplicate startup.")
                        return False
        except Exception:
            pass  # Stale lock file, safe to overwrite

    with open(LOCK_FILE, "w") as f:
        f.write(str(os.getpid()))
    return True


def release_process_lock():
    """Remove lock file on clean shutdown."""
    if os.path.exists(LOCK_FILE):
        try:
            os.remove(LOCK_FILE)
            logger.info("Worker process lock released.")
        except Exception as e:
            logger.warning(f"Failed to remove lock file: {e}")


def execute_monitoring_job(app, source_name: Optional[str] = None):
    """
    Job target invoked every 15 minutes by APScheduler or triggered manually.
    """
    logger.info(">>> Initiating scheduled government policy monitoring cycle...")
    with app.app_context():
        engine = PolicyMonitoringEngine()
        if source_name:
            source = GovernmentSource.query.filter(
                (GovernmentSource.name.ilike(f"%{source_name}%")) |
                (GovernmentSource.source_type == source_name)
            ).first()
            if not source:
                logger.error(f"Source matching '{source_name}' not found.")
                return
            res = engine.scan_source(source.id)
            logger.info(f"Source scan completed: {res}")
        else:
            summary = engine.scan_all_sources()
            logger.info(
                f">>> Monitoring cycle finished: Scanned {summary['sources_scanned']} sources | "
                f"Found {summary['total_documents_found']} docs | "
                f"New: {summary['new_documents_detected']} | "
                f"Modified: {summary['modified_documents_detected']}"
            )


def main():
    parser = argparse.ArgumentParser(description="PolicySetu Background Monitoring Worker")
    parser.add_argument("--scan", "--run-once", action="store_true", help="Execute a single scan cycle immediately and exit")
    parser.add_argument("--source", type=str, help="Specific source name or code to scan")
    parser.add_argument("--interval", type=int, default=15, help="Monitoring interval in minutes (default: 15)")
    args = parser.parse_args()

    app = create_app("development")

    # Handle manual one-shot scan
    if args.scan or args.source:
        logger.info("Executing on-demand manual monitoring scan...")
        execute_monitoring_job(app, source_name=args.source)
        logger.info("Manual scan execution complete. Exiting.")
        sys.exit(0)

    # Acquire process lock for continuous scheduled worker
    if not acquire_process_lock():
        sys.exit(1)

    scheduler = BlockingScheduler()

    def handle_exit(sig, frame):
        logger.info("Graceful shutdown signal received. Stopping worker scheduler...")
        scheduler.shutdown(wait=False)
        release_process_lock()
        sys.exit(0)

    signal.signal(signal.SIGINT, handle_exit)
    signal.signal(signal.SIGTERM, handle_exit)

    # Schedule recurring job every 15 minutes
    interval_mins = args.interval
    scheduler.add_job(
        execute_monitoring_job,
        trigger=IntervalTrigger(minutes=interval_mins),
        args=[app, None],
        id="policy_monitoring_job",
        name="15-minute Official Policy Monitor",
        replace_existing=True
    )

    logger.info(f"PolicySetu Worker started successfully (PID: {os.getpid()}).")
    logger.info(f"Scheduled monitoring frequency: Every {interval_mins} minutes.")
    logger.info("Running initial startup scan cycle...")

    try:
        # Run first cycle immediately upon startup
        execute_monitoring_job(app, None)
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
    finally:
        release_process_lock()


if __name__ == "__main__":
    main()
