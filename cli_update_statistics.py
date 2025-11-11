#!/usr/bin/env python3
"""
CLI script to update job statistics
This script can be run daily via cron to keep statistics up-to-date.

Usage:
    python cli_update_statistics.py

Cron example (runs daily at 1:00 AM):
    0 1 * * * cd /path/to/KIGate && /usr/bin/python3 cli_update_statistics.py >> /var/log/kigate_stats.log 2>&1
"""

import asyncio
import logging
import sys
from datetime import datetime
from pathlib import Path

# Add the parent directory to the path so we can import from the project
sys.path.insert(0, str(Path(__file__).parent))

from database import init_db, close_db, get_async_session
from service.job_statistics_service import JobStatisticsService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


async def update_statistics():
    """Update job statistics"""
    logger.info("Starting job statistics update")
    
    try:
        # Initialize database
        await init_db()
        logger.info("Database initialized")
        
        # Get database session
        async for db in get_async_session():
            try:
                # Calculate all statistics
                counts = await JobStatisticsService.calculate_all_statistics(db)
                
                logger.info(f"Statistics update completed successfully:")
                logger.info(f"  - Daily statistics: {counts['day']} records")
                logger.info(f"  - Weekly statistics: {counts['week']} records")
                logger.info(f"  - Monthly statistics: {counts['month']} records")
                
                return True
                
            except Exception as e:
                logger.error(f"Error updating statistics: {str(e)}", exc_info=True)
                return False
            finally:
                # Close the session
                break
        
    except Exception as e:
        logger.error(f"Fatal error: {str(e)}", exc_info=True)
        return False
    finally:
        # Close database connections
        await close_db()
        logger.info("Database connections closed")


async def main():
    """Main entry point"""
    start_time = datetime.now()
    logger.info("=" * 60)
    logger.info("KIGate Job Statistics Update Script")
    logger.info(f"Started at: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    success = await update_statistics()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    logger.info("=" * 60)
    logger.info(f"Completed at: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info(f"Duration: {duration:.2f} seconds")
    logger.info(f"Status: {'SUCCESS' if success else 'FAILED'}")
    logger.info("=" * 60)
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
