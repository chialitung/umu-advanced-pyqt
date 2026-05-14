"""Sync service for PyQt6 GUI."""

from __future__ import annotations

import logging
import os
from datetime import datetime

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lms_client.auth import SessionAuth
from lms_client.client import LMSClient
from lms_client.storage.models import Base, Course, CourseGroupTime, Session as SessionModel, User
from lms_client.timeutil import now_beijing, timestamp_to_beijing

from .auth_service import deserialize_session

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_DATABASE_URL = f"sqlite:///{os.path.join(_PROJECT_ROOT, 'lms.db')}"


class SyncWorker(QThread):
    """Background worker for sync operations."""

    progress_updated = pyqtSignal(int, str)  # percent, message
    sync_finished = pyqtSignal(bool, str)  # success, details

    def __init__(self, database_url: str, serialized_session: str, sync_type: str,
                 start_date: str | None = None, end_date: str | None = None) -> None:
        super().__init__()
        self.database_url = database_url
        self.serialized_session = serialized_session
        self.sync_type = sync_type
        self.start_date = start_date
        self.end_date = end_date
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)

        # Ensure columns
        from sqlalchemy import inspect
        inspector = inspect(engine)
        if "chapter_id" not in {c["name"] for c in inspector.get_columns("sessions")}:
            with engine.connect() as conn:
                conn.execute("ALTER TABLE sessions ADD COLUMN chapter_id VARCHAR(64)")
                conn.commit()

        session = deserialize_session(self.serialized_session)
        auth = SessionAuth(session=session)
        client = LMSClient(auth=auth)

        try:
            if self.sync_type == "users":
                self._sync_users(client, SessionLocal)
            else:
                self._sync_courses(client, SessionLocal)
        except Exception as exc:
            logger.exception("Sync failed")
            self.sync_finished.emit(False, str(exc))
        finally:
            client.close()

    def _sync_users(self, client: LMSClient, SessionLocal: sessionmaker) -> None:
        import time

        batch_size = 1000
        processed = 0
        total = 0

        for is_mgr in (0, 1):
            mgr_label = "管理员" if is_mgr else "普通用户"
            if is_mgr > 0:
                time.sleep(1.0)

            first_resp = client.get(
                "/ajax/enterprise/getUserList",
                params={"page": 1, "size": batch_size, "is_manager": is_mgr},
            )
            first_data = first_resp.get("data", {}) if isinstance(first_resp, dict) else {}
            first_items = first_data.get("list", []) if isinstance(first_data, dict) else []
            page_info = first_data.get("page_info", {}) if isinstance(first_data, dict) else {}
            total_page_num = int(page_info.get("total_page_num", 0))
            list_total_num = int(page_info.get("list_total_num", 0))
            total += list_total_num

            self.progress_updated.emit(0, f"已更新 {processed} / {total} 用户")

            if first_items:
                records = [self._transform_user(item) for item in first_items]
                self._upsert_users(records, SessionLocal)
                processed += len(first_items)
                self.progress_updated.emit(
                    int(processed / max(total, 1) * 100),
                    f"已更新 {processed} / {total} 用户"
                )

            for page in range(2, total_page_num + 1):
                if self._cancelled:
                    self.sync_finished.emit(False, "同步已取消")
                    return
                time.sleep(1.0)
                result = client.get(
                    "/ajax/enterprise/getUserList",
                    params={"page": page, "size": batch_size, "is_manager": is_mgr},
                )
                data = result.get("data", {}) if isinstance(result, dict) else {}
                items = data.get("list", []) if isinstance(data, dict) else []
                if items:
                    records = [self._transform_user(item) for item in items]
                    self._upsert_users(records, SessionLocal)
                    processed += len(items)
                    self.progress_updated.emit(
                        int(processed / max(total, 1) * 100),
                        f"已更新 {processed} / {total} 用户"
                    )

        self.progress_updated.emit(100, f"用户同步完成，共 {processed} 条")
        self.sync_finished.emit(True, f"用户同步完成，共 {processed} 条")

    def _sync_courses(self, client: LMSClient, SessionLocal: sessionmaker) -> None:
        import time

        date_params = {}
        if self.start_date:
            try:
                begin_dt = datetime.strptime(self.start_date, "%Y-%m-%d")
                date_params["start_day"] = self.start_date
                date_params["startDay"] = int(begin_dt.timestamp() * 1000)
            except (ValueError, TypeError):
                logger.warning("Invalid start_date: %s", self.start_date)
        if self.end_date:
            try:
                end_dt = datetime.strptime(self.end_date, "%Y-%m-%d")
                date_params["end_day"] = self.end_date
                date_params["endDay"] = int(end_dt.timestamp() * 1000)
            except (ValueError, TypeError):
                logger.warning("Invalid end_date: %s", self.end_date)

        batch_size = 500
        first_page_params = {"page": 1, "size": batch_size, **date_params}
        first_page = client.get("/ajax/enterprise/getReportGroupList", params=first_page_params)
        data = first_page.get("data", {})
        page_info = data.get("page_info", {}) if isinstance(data, dict) else {}
        total = int(page_info.get("list_total_num", 0))
        total_page_num = int(page_info.get("total_page_num", 0))

        processed = 0
        saved = 0

        def _process_page(page_data: dict, page_num: int) -> None:
            nonlocal processed, saved
            items = page_data.get("list", []) if isinstance(page_data, dict) else []
            if not items:
                return
            records = [self._transform_course(item) for item in items]
            session_sync_ids, page_saved = self._upsert_courses(records, SessionLocal)

            for idx, group_id in enumerate(session_sync_ids, 1):
                self.progress_updated.emit(
                    int(processed / max(total, 1) * 100),
                    f"接口返回 {processed + len(items)} / {total} 课程，入库 {saved + page_saved} 条，正在同步小节 {idx}/{len(session_sync_ids)}"
                )
                self._fetch_and_save_sessions(client, group_id, SessionLocal)
                if idx < len(session_sync_ids):
                    time.sleep(0.5)

            processed += len(items)
            saved += page_saved
            self.progress_updated.emit(
                int(processed / max(total, 1) * 100),
                f"接口返回 {processed} / {total} 课程，入库 {saved} 条"
            )

        _process_page(data, 1)

        for page in range(2, total_page_num + 1):
            if self._cancelled:
                self.sync_finished.emit(False, "同步已取消")
                return
            time.sleep(1.0)
            result = client.get(
                "/ajax/enterprise/getReportGroupList",
                params={"page": page, "size": batch_size, **date_params},
            )
            page_data = result.get("data", {}) if isinstance(result, dict) else {}
            _process_page(page_data, page)

        self.progress_updated.emit(100, f"课程同步完成，接口返回 {processed} 条，入库 {saved} 条")
        self.sync_finished.emit(True, f"课程同步完成，接口返回 {processed} 条，入库 {saved} 条")

    @staticmethod
    def _transform_user(raw: dict) -> dict:
        umu_id = raw.get("id") or raw.get("user_id") or raw.get("umu_id")
        departments = raw.get("departments")
        return {
            "raw_data": raw,
            "umu_id": str(umu_id) if umu_id else "",
            "number": raw.get("number"),
            "user_name": raw.get("user_name"),
            "name": raw.get("user_name") or raw.get("name"),
            "email": raw.get("email"),
            "mobile": raw.get("mobile"),
            "account_joining_time": timestamp_to_beijing(raw.get("account_joining_time")),
            "departments": departments if isinstance(departments, str) else None,
            "role_type": str(raw.get("role_type", "")),
        }

    @staticmethod
    def _transform_course(raw: dict) -> dict:
        group_times = raw.get("group_times") or raw.get("groupTimes") or raw.get("scheduleList") or raw.get("group_time")
        if isinstance(group_times, dict):
            group_times = [group_times]
        course_id_value = raw.get("id") or raw.get("group_id")
        course_id_str = str(course_id_value) if course_id_value else ""
        return {
            "raw_data": raw,
            "course_id": course_id_str,
            "group_id": course_id_str,
            "title": raw.get("title"),
            "name": raw.get("title") or raw.get("name"),
            "creat_time": timestamp_to_beijing(raw.get("creat_time")),
            "source": raw.get("source"),
            "desc": raw.get("desc"),
            "update_time": timestamp_to_beijing(raw.get("update_time")),
            "head_img_old": raw.get("head_img"),
            "head_img_new": raw.get("head_img"),
            "lesson_type": raw.get("lesson_type"),
            "group_time": timestamp_to_beijing(raw.get("group_time")),
            "umu_id": raw.get("umu_id"),
            "share_url": raw.get("share_url"),
            "access_code": raw.get("access_code"),
            "categoryArr": raw.get("categoryArr"),
            "multimedia_id": raw.get("multimedia_id"),
            "group_times": group_times if isinstance(group_times, list) else None,
        }

    @staticmethod
    def _upsert_users(records: list[dict], SessionLocal: sessionmaker) -> None:
        session = SessionLocal()
        try:
            for record in records:
                umu_id = record.get("umu_id")
                if not umu_id:
                    continue
                existing = session.query(User).filter_by(umu_id=umu_id).first()
                if existing:
                    for key, value in record.items():
                        if key != "raw_data":
                            setattr(existing, key, value)
                    existing.raw_data = record["raw_data"]
                else:
                    session.add(User(**record))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @staticmethod
    def _upsert_courses(records: list[dict], SessionLocal: sessionmaker) -> tuple[list[str], int]:
        session = SessionLocal()
        session_sync_ids = []
        try:
            course_ids = [r.get("course_id") for r in records if r.get("course_id")]
            existing_courses = {
                c.course_id: c
                for c in session.query(Course).filter(Course.course_id.in_(course_ids)).all()
            }
            inserted = 0
            updated = 0
            skipped = 0

            for record in records:
                course_id = record.get("course_id")
                if not course_id:
                    skipped += 1
                    continue

                group_times = record.pop("group_times", None)
                if group_times:
                    SyncWorker._save_group_times(session, course_id, group_times)

                existing = existing_courses.get(course_id)
                head_img_new = record.get("head_img_new")
                lesson_type = record.get("lesson_type")
                group_id = record.get("group_id")
                update_time = record.get("update_time")

                if existing:
                    for key, value in record.items():
                        if key != "raw_data" or value is not None:
                            setattr(existing, key, value)
                    if group_id:
                        last_fetch = existing.last_fetch_time
                        if not last_fetch or not update_time or update_time > last_fetch:
                            session_sync_ids.append(group_id)
                    existing.last_fetch_time = now_beijing()
                    updated += 1
                else:
                    if group_id:
                        session_sync_ids.append(group_id)
                    record["last_fetch_time"] = now_beijing()
                    session.add(Course(**record))
                    inserted += 1
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

        return session_sync_ids, inserted + updated

    @staticmethod
    def _save_group_times(session, group_id: str, group_times: list[dict]) -> None:
        session.query(CourseGroupTime).filter_by(group_id=group_id).delete()
        for gt in group_times:
            start_str = gt.get("startTime", "")
            end_str = gt.get("endTime", "")
            group_day = gt.get("groupDay", "")
            start_dt = SyncWorker._parse_group_time(group_day, start_str)
            end_dt = SyncWorker._parse_group_time(group_day, end_str)
            if start_dt and end_dt:
                session.add(CourseGroupTime(
                    group_id=group_id,
                    start_time=start_dt,
                    end_time=end_dt,
                ))

    @staticmethod
    def _parse_group_time(group_day: str, time_str: str):
        if not group_day or not time_str:
            return None
        try:
            from datetime import time as dt_time
            date_part = datetime.strptime(group_day, "%Y-%m-%d").date()
            hour, minute = map(int, time_str.split(":"))
            t = dt_time(hour, minute)
            return datetime.combine(date_part, t)
        except (ValueError, TypeError):
            return None

    def _fetch_and_save_sessions(self, client: LMSClient, group_id: str, SessionLocal: sessionmaker) -> None:
        import time

        try:
            result = client.get(
                "/ajax/session/getsessionlistbygroup",
                params={
                    "group_id": group_id,
                    "isFirstLoad": "true",
                    "is_contain_chapter": 1,
                    "page": 1,
                    "size": 500,
                    "status_str": "0,1",
                },
            )
            data = result.get("data", {}) if isinstance(result, dict) else {}
            items = data.get("list", []) if isinstance(data, dict) else []
        except Exception:
            return

        records = []
        chapter_ids = []
        for item in items:
            item_type = item.get("item_type")
            if item_type == 2 or str(item_type) == "2":
                cid = str(item.get("id", ""))
                if cid:
                    chapter_ids.append(cid)
                continue
            record = self._build_session_record(item, group_id)
            if record:
                records.append(record)

        for chapter_id in chapter_ids:
            try:
                chapter_result = client.get(
                    "/ajax/session/getsessionlistbygroup",
                    params={
                        "group_id": group_id,
                        "chapter_id": chapter_id,
                        "page": 1,
                        "size": 500,
                        "status_str": "0,1",
                    },
                )
                chapter_data = chapter_result.get("data", {}) if isinstance(chapter_result, dict) else {}
                chapter_items = chapter_data.get("list", []) if isinstance(chapter_data, dict) else []
            except Exception:
                continue
            for item in chapter_items:
                record = self._build_session_record(item, group_id, chapter_id=chapter_id)
                if record:
                    records.append(record)

        if records:
            self._upsert_sessions(records, SessionLocal)

    @staticmethod
    def _build_session_record(item: dict, course_id: str, chapter_id: str = "") -> dict | None:
        info = item.get("sessionInfo", {})
        if not info:
            return None
        setup = info.get("setup", {})
        return {
            "session_id": str(info.get("sessionId", "")),
            "course_id": course_id,
            "chapter_id": chapter_id if chapter_id else str(info.get("chapter_id", "")),
            "name": info.get("sessionTitle", ""),
            "status": int(info.get("status", 0)) if info.get("status") is not None else 1,
            "session_type": str(info.get("sessionType", "")),
            "is_require": 1 if info.get("is_require") else 0,
            "type_name": setup.get("type_name") or setup.get("typeName") or "",
            "questions": item.get("questionArr"),
            "raw_data": item,
        }

    @staticmethod
    def _upsert_sessions(records: list[dict], SessionLocal: sessionmaker) -> None:
        session = SessionLocal()
        try:
            for record in records:
                session_id = record.get("session_id")
                if not session_id:
                    continue
                existing = session.query(SessionModel).filter_by(session_id=session_id).first()
                if existing:
                    for key, value in record.items():
                        if key != "raw_data":
                            setattr(existing, key, value)
                    existing.raw_data = record["raw_data"]
                else:
                    session.add(SessionModel(**record))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class SyncService(QObject):
    """Manages sync operations for the GUI."""

    progress_updated = pyqtSignal(str, int, str)  # sync_type, percent, message
    sync_finished = pyqtSignal(str, bool, str)  # sync_type, success, details

    def __init__(self, database_url: str = DEFAULT_DATABASE_URL) -> None:
        super().__init__()
        self.database_url = database_url
        self._user_worker: SyncWorker | None = None
        self._course_worker: SyncWorker | None = None

    def start_sync_users(self, serialized_session: str) -> None:
        if self._user_worker and self._user_worker.isRunning():
            return
        self._user_worker = SyncWorker(self.database_url, serialized_session, "users")
        self._user_worker.progress_updated.connect(
            lambda p, m: self.progress_updated.emit("users", p, m)
        )
        self._user_worker.sync_finished.connect(
            lambda s, d: self.sync_finished.emit("users", s, d)
        )
        self._user_worker.start()

    def start_sync_courses(self, serialized_session: str, start_date: str | None = None,
                           end_date: str | None = None) -> None:
        if self._course_worker and self._course_worker.isRunning():
            return
        self._course_worker = SyncWorker(
            self.database_url, serialized_session, "courses", start_date, end_date
        )
        self._course_worker.progress_updated.connect(
            lambda p, m: self.progress_updated.emit("courses", p, m)
        )
        self._course_worker.sync_finished.connect(
            lambda s, d: self.sync_finished.emit("courses", s, d)
        )
        self._course_worker.start()

    def is_running(self, sync_type: str) -> bool:
        worker = self._user_worker if sync_type == "users" else self._course_worker
        return worker is not None and worker.isRunning()

    def cancel(self, sync_type: str) -> None:
        worker = self._user_worker if sync_type == "users" else self._course_worker
        if worker is not None and worker.isRunning():
            worker.cancel()
