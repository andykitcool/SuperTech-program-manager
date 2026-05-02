import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


async def sync_photos_for_activity(activity_id: int, db: Session):
    """Sync photos from Wotu for a given activity and archive them to programs."""
    from app.models import Activity, Photo, Program
    from app.config import get_settings

    settings = get_settings()
    activity = db.query(Activity).filter(Activity.id == activity_id).first()
    if not activity or not activity.wotu_album_url:
        return

    logger.info(f"Starting photo sync for activity {activity_id}")

    try:
        from app.utils.wotu_client import WotuClient
        client = WotuClient()

        photos_data = await client.fetch_photos(activity.wotu_album_url)
        if not photos_data:
            logger.info(f"No new photos found for activity {activity_id}")
            return

        tolerance = timedelta(minutes=settings.PHOTO_SYNC_TIME_TOLERANCE_MINUTES)
        new_count = 0
        matched_count = 0

        for photo_info in photos_data:
            # Check if already synced
            existing = db.query(Photo).filter(
                Photo.wotu_photo_id == photo_info.get("photo_id")
            ).first()
            if existing:
                continue

            # Try to match with a program by shoot_time
            shoot_time = photo_info.get("shoot_time")
            matched_program_id = None

            if shoot_time:
                programs = db.query(Program).filter(
                    Program.activity_id == activity_id,
                    Program.start_time.isnot(None),
                    Program.end_time.isnot(None),
                ).all()

                for program in programs:
                    if (
                        program.start_time - tolerance
                        <= shoot_time
                        <= program.end_time + tolerance
                    ):
                        matched_program_id = program.id
                        break

            # Create photo record
            sync_status = "matched" if matched_program_id else "unmatched"
            photo = Photo(
                activity_id=activity_id,
                program_id=matched_program_id,
                filename=photo_info.get("filename", "unknown.jpg"),
                wotu_url=photo_info.get("url"),
                wotu_photo_id=photo_info.get("photo_id"),
                shoot_time=shoot_time,
                width=photo_info.get("width"),
                height=photo_info.get("height"),
                file_size=photo_info.get("file_size"),
                sync_status=sync_status,
            )
            db.add(photo)
            new_count += 1
            if matched_program_id:
                matched_count += 1

        db.commit()
        logger.info(
            f"Photo sync completed for activity {activity_id}: "
            f"{new_count} new, {matched_count} matched"
        )

        # Update photo counts for matched programs
        if matched_count > 0:
            programs = db.query(Program).filter(
                Program.activity_id == activity_id
            ).all()
            for program in programs:
                count = db.query(Photo).filter(
                    Photo.program_id == program.id
                ).count()
                if count != program.photo_count:
                    old_count = program.photo_count
                    program.photo_count = count
                    # Check auto-ready
                    from app.models.activity import ReadyStatus, VideoStatus
                    if (
                        program.ready_mode.value == "auto"
                        and program.video_status == VideoStatus.READY
                        and program.photo_count >= 1
                        and program.ready_status != ReadyStatus.READY
                    ):
                        program.ready_status = ReadyStatus.READY
            db.commit()

    except Exception as e:
        logger.error(f"Photo sync error for activity {activity_id}: {e}")
        db.rollback()


def start_scheduler():
    """Start the APScheduler for photo sync tasks."""
    if not scheduler.running:
        scheduler.start()
        logger.info("Photo sync scheduler started")


def stop_scheduler():
    """Stop the APScheduler."""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Photo sync scheduler stopped")
