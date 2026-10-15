"""实时统计与周期快照的回归测试。"""

from __future__ import annotations

import unittest
from datetime import datetime
from unittest.mock import patch

from sqlalchemy import create_engine, event, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.database import Base
from backend.app.models import (
    Course,
    CourseSession,
    FeedbackRecord,
    StatisticsSetting,
    StatisticsSnapshot,
    User,
)
from backend.app.services import snapshot_service
from backend.app.services.statistics_service import calculate_current_statistics


class StatisticsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        @event.listens_for(self.engine, "connect")
        def enable_foreign_keys(dbapi_connection, _connection_record) -> None:
            dbapi_connection.execute("PRAGMA foreign_keys = ON")

        Base.metadata.create_all(self.engine)
        self.session_factory = sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
        )

    def tearDown(self) -> None:
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    @staticmethod
    def add_user(
        database_session: Session,
        *,
        username: str,
        role: str,
        phone: str,
        class_name: str | None = None,
    ) -> User:
        user = User(
            username=username,
            role=role,
            password_hash="test-only",
            name=username,
            phone=phone,
            status="active",
            student_no=f"NO-{username}" if role == "student" else None,
            grade="2026级" if role == "student" else None,
            class_name=class_name,
            major="软件工程" if role == "student" else None,
        )
        database_session.add(user)
        database_session.flush()
        return user

    def add_course_and_classroom(
        self,
        database_session: Session,
        *,
        teacher: User,
        start_time: datetime,
        class_name: str = "测试班",
    ) -> CourseSession:
        course = Course(name="测试课程", teacher_id=teacher.id, status="active")
        database_session.add(course)
        database_session.flush()
        classroom = CourseSession(
            course_id=course.id,
            class_name=class_name,
            topic="统计测试",
            start_time=start_time,
            status="active",
        )
        database_session.add(classroom)
        database_session.flush()
        return classroom

    def test_latest_feedback_uses_submission_time_and_cutoff(self) -> None:
        with self.session_factory() as database_session:
            teacher = self.add_user(
                database_session,
                username="teacher",
                role="teacher",
                phone="10001",
            )
            student = self.add_user(
                database_session,
                username="student",
                role="student",
                phone="10002",
                class_name="测试班",
            )
            classroom = self.add_course_and_classroom(
                database_session,
                teacher=teacher,
                start_time=datetime(2026, 9, 23, 9, 0),
            )
            database_session.add_all(
                [
                    FeedbackRecord(
                        session_id=classroom.id,
                        student_id=student.id,
                        score=6,
                        submitted_at=datetime(2026, 9, 23, 9, 10),
                    ),
                    FeedbackRecord(
                        session_id=classroom.id,
                        student_id=student.id,
                        score=1,
                        submitted_at=datetime(2026, 9, 23, 9, 5),
                    ),
                ]
            )
            database_session.commit()

            current = calculate_current_statistics(classroom.id, database_session)
            self.assertEqual(current.total_students, 1)
            self.assertEqual(current.average_score, 6.0)

            historical = calculate_current_statistics(
                classroom.id,
                database_session,
                submitted_before=datetime(2026, 9, 23, 9, 7),
            )
            self.assertEqual(historical.total_students, 1)
            self.assertEqual(historical.average_score, 1.0)

    def test_scheduler_snapshots_only_the_last_completed_period(self) -> None:
        fixed_now = datetime(2026, 9, 23, 10, 12)
        with self.session_factory() as database_session:
            administrator = self.add_user(
                database_session,
                username="admin",
                role="admin",
                phone="20001",
            )
            teacher = self.add_user(
                database_session,
                username="teacher",
                role="teacher",
                phone="20002",
            )
            student = self.add_user(
                database_session,
                username="student",
                role="student",
                phone="20003",
                class_name="测试班",
            )
            classroom = self.add_course_and_classroom(
                database_session,
                teacher=teacher,
                start_time=datetime(2026, 9, 23, 10, 1),
            )
            future_classroom = self.add_course_and_classroom(
                database_session,
                teacher=teacher,
                start_time=datetime(2026, 9, 23, 10, 11),
                class_name="未来班",
            )
            database_session.add(
                StatisticsSetting(
                    id=1,
                    interval_minutes=5,
                    updated_by=administrator.id,
                )
            )
            database_session.add_all(
                [
                    FeedbackRecord(
                        session_id=classroom.id,
                        student_id=student.id,
                        score=2,
                        submitted_at=datetime(2026, 9, 23, 10, 4),
                    ),
                    FeedbackRecord(
                        session_id=classroom.id,
                        student_id=student.id,
                        score=4,
                        submitted_at=datetime(2026, 9, 23, 10, 9),
                    ),
                    FeedbackRecord(
                        session_id=classroom.id,
                        student_id=student.id,
                        score=6,
                        submitted_at=datetime(2026, 9, 23, 10, 11),
                    ),
                ]
            )
            database_session.commit()
            classroom_id = classroom.id
            future_classroom_id = future_classroom.id

        with (
            patch.object(snapshot_service, "SessionLocal", self.session_factory),
            patch.object(
                snapshot_service,
                "utc_now_without_timezone",
                return_value=fixed_now,
            ),
        ):
            self.assertEqual(snapshot_service.generate_active_classroom_snapshots(), 1)
            self.assertEqual(snapshot_service.generate_active_classroom_snapshots(), 0)

        with self.session_factory() as database_session:
            snapshots = list(
                database_session.scalars(select(StatisticsSnapshot))
            )
            self.assertEqual(len(snapshots), 1)
            snapshot = snapshots[0]
            self.assertEqual(snapshot.session_id, classroom_id)
            self.assertNotEqual(snapshot.session_id, future_classroom_id)
            self.assertEqual(snapshot.period_start, datetime(2026, 9, 23, 10, 5))
            self.assertEqual(snapshot.period_end, datetime(2026, 9, 23, 10, 10))
            self.assertEqual(snapshot.total_students, 1)
            self.assertEqual(snapshot.score_4_count, 1)
            self.assertEqual(snapshot.score_6_count, 0)


if __name__ == "__main__":
    unittest.main()
