"""Governance service for PyQt6 GUI."""

from __future__ import annotations

import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from PyQt6.QtCore import QObject, QThread, pyqtSignal
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from lms_client.auth import SessionAuth
from lms_client.client import LMSClient
from lms_client.storage.models import (
    Base,
    Course,
    CourseGroupTime,
    GovernanceConfig,
    GovernanceResult,
    GovernanceRun,
    Session as SessionModel,
    User,
)
from lms_client.timeutil import now_beijing

from .auth_service import deserialize_session

logger = logging.getLogger(__name__)

_PROJECT_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
DEFAULT_DATABASE_URL = f"sqlite:///{os.path.join(_PROJECT_ROOT, 'lms.db')}"

DEFAULT_CONFIGS = {
    "forbidden_words": ["接待", "交流", "访谈", "座谈", "茶话会", "员工沟通", "福利宣讲", "工会活动",
                        "wellbeing", "员工大会", "志愿者活动", "团建", "报名", "问卷", "抽奖", "投票",
                        "会议", "宣讲", "早会", "面谈", "晤谈", "电话会议", "心理健康", "党建", "督导",
                        "团结", "优秀代表", "表彰", "纪念", "庆典"],
    "exception_words": ["培训", "学习", "研讨", "研究", "课程", "教育", "辅导", "指导", "论坛",
                        "工作坊", "角色扮演", "模拟演练", "案例分析", "小组讨论", "讲座", "导师",
                        "讲解", "解读", "政策解读", "政策", "小测", "测验", "考试", "考卷", "试卷"],
    "fallback_forbidden_words": [],
    "valid_categories": ["通用力", "专业力", "领导力", "新兴力"],
    "evaluation_keywords": ["满意度", "帮助", "收获", "评价", "得分", "评分", "打分", "建议",
                            "改进", "推荐", "探讨", "话题", "学习", "知识", "简要说明", "意见或建议"],
    "meaningless_placeholders": ["课程大纲：", "课程大纲:", "课程大纲", "暂无", "待定"],
    "empty_content_marker": "b96beb74eb4e5ea5419d74b956c5404c",
    "excluded_umu_id": "13264912",
    "excluded_lesson_type": "999",
    "max_duration_hours": 30,
    "excluded_course_ids": [],
}


def _title_matched_forbidden_words(title: str | None, forbidden_words: set[str] | None = None) -> list[str]:
    if not title:
        return []
    words = forbidden_words if forbidden_words is not None else set(DEFAULT_CONFIGS["forbidden_words"])
    matches = [fw for fw in words if fw in title]
    return sorted(matches, key=lambda w: (-len(w), w))


def _title_hits_exception(title: str | None, exception_words: set[str] | None = None) -> bool:
    if not title:
        return False
    words = exception_words if exception_words is not None else set(DEFAULT_CONFIGS["exception_words"])
    return any(ew in title for ew in words)


@dataclass
class RuleResult:
    rule_id: int
    rule_name: str
    compliant: bool
    level: str
    issue: str = ""


@dataclass
class CourseGovernanceResult:
    course_id: str
    group_id: str
    course_name: str
    creator_email: str
    creator_name: str
    umu_link: str
    overall_compliant: bool
    overall_level: str
    rule_results: list[dict] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


class GovernanceConfigService:
    """Manages governance rule configurations."""

    def __init__(self, database_url: str = DEFAULT_DATABASE_URL):
        self.engine = create_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def get_config(self, key: str, default=None):
        session = self.SessionLocal()
        try:
            record = session.query(GovernanceConfig).filter_by(config_key=key).first()
            if record and record.config_value is not None:
                return record.config_value
            return DEFAULT_CONFIGS.get(key, default) if default is not None else DEFAULT_CONFIGS.get(key)
        finally:
            session.close()

    def get_all_configs(self) -> dict:
        session = self.SessionLocal()
        try:
            records = session.query(GovernanceConfig).all()
            stored = {r.config_key: r.config_value for r in records if r.config_value is not None}
            result = dict(DEFAULT_CONFIGS)
            result.update(stored)
            return result
        finally:
            session.close()

    def set_config(self, key: str, value, description: str | None = None) -> None:
        session = self.SessionLocal()
        try:
            record = session.query(GovernanceConfig).filter_by(config_key=key).first()
            if record:
                record.config_value = value
                if description is not None:
                    record.description = description
            else:
                session.add(GovernanceConfig(
                    config_key=key,
                    config_value=value,
                    description=description or "",
                ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def reset_to_defaults(self) -> None:
        session = self.SessionLocal()
        try:
            session.query(GovernanceConfig).delete()
            for key, value in DEFAULT_CONFIGS.items():
                session.add(GovernanceConfig(
                    config_key=key,
                    config_value=value,
                    description="",
                ))
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class GovernanceWorker(QThread):
    """Background worker for governance operations."""

    progress_updated = pyqtSignal(int, int, int, int, int, str, str)
    # progress, total, compliant, non_compliant, major, current_course, message
    governance_finished = pyqtSignal(bool, str, str)  # success, run_id, message

    def __init__(self, database_url: str, serialized_session: str, run_id: str,
                 start_date: str | None = None, end_date: str | None = None,
                 resume: bool = False, owner: str = "") -> None:
        super().__init__()
        self.database_url = database_url
        self.serialized_session = serialized_session
        self.run_id = run_id
        self.start_date = start_date
        self.end_date = end_date
        self.resume = resume
        self.owner = owner
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

        config_service = GovernanceConfigService(self.database_url)
        client = None
        db_session = SessionLocal()

        try:
            session = deserialize_session(self.serialized_session)
            auth = SessionAuth(session=session)
            client = LMSClient(auth=auth)

            run_record = db_session.query(GovernanceRun).filter_by(run_id=self.run_id).first()
            if not run_record and not self.resume:
                run_record = GovernanceRun(
                    run_id=self.run_id,
                    status="running",
                    start_date=self.start_date,
                    end_date=self.end_date,
                    owner=self.owner,
                )
                db_session.add(run_record)
                db_session.commit()
            elif run_record and self.resume:
                run_record.status = "running"
                run_record.error_message = None
                db_session.commit()

            excluded_umu_id = config_service.get_config("excluded_umu_id", "13264912")
            excluded_lesson_type = config_service.get_config("excluded_lesson_type", "999")
            query = (
                db_session.query(Course)
                .filter(Course.umu_id != excluded_umu_id)
                .filter(Course.lesson_type != excluded_lesson_type)
            )

            run_start_date = self.start_date or getattr(run_record, "start_date", None)
            run_end_date = self.end_date or getattr(run_record, "end_date", None)

            if run_start_date:
                try:
                    start_dt = datetime.strptime(run_start_date, "%Y-%m-%d")
                    query = query.filter(Course.creat_time >= start_dt)
                except (ValueError, TypeError):
                    pass
            if run_end_date:
                try:
                    end_dt = datetime.strptime(run_end_date, "%Y-%m-%d")
                    query = query.filter(Course.creat_time < end_dt + timedelta(days=1))
                except (ValueError, TypeError):
                    pass

            courses = query.all()
            total = len(courses)

            if run_record:
                run_record.total_courses = total
                db_session.commit()

            existing_ids = set()
            processed = 0
            compliant_count = 0
            non_compliant_count = 0
            major_count = 0

            if self.resume:
                existing_results = db_session.query(GovernanceResult.course_id).filter_by(run_id=self.run_id).all()
                existing_ids = {r.course_id for r in existing_results}
                existing_all = db_session.query(GovernanceResult).filter_by(run_id=self.run_id).all()
                processed = len(existing_all)
                for r in existing_all:
                    if r.overall_compliant:
                        compliant_count += 1
                    else:
                        non_compliant_count += 1
                    if r.overall_level in ("major", "minor", "unknown"):
                        major_count += 1

            for course in courses:
                if self._cancelled:
                    self.governance_finished.emit(False, self.run_id, "治理已取消")
                    return

                if course.course_id in existing_ids:
                    continue

                current_course = course.title or course.course_id
                self.progress_updated.emit(
                    processed, total, compliant_count, non_compliant_count, major_count,
                    current_course, f"正在审核: {current_course}"
                )

                result = self._check_course(course, client, db_session, config_service)
                self._save_result(self.run_id, result, db_session)

                processed += 1
                if result.overall_compliant:
                    compliant_count += 1
                else:
                    non_compliant_count += 1
                if result.overall_level in ("major", "minor", "unknown"):
                    major_count += 1

                self.progress_updated.emit(
                    processed, total, compliant_count, non_compliant_count, major_count,
                    current_course, f"正在审核: {current_course}"
                )

                time.sleep(0.5)

            if run_record:
                run_record.status = "completed"
                run_record.completed_at = now_beijing()
                run_record.processed_courses = processed
                db_session.commit()

            self.governance_finished.emit(True, self.run_id, f"治理完成，共审核 {processed} 门课程")
        except Exception as exc:
            logger.exception("Governance failed")
            try:
                db_session.rollback()
                run_record = db_session.query(GovernanceRun).filter_by(run_id=self.run_id).first()
                if run_record:
                    run_record.status = "failed"
                    run_record.error_message = str(exc)
                    db_session.commit()
            except Exception:
                pass
            self.governance_finished.emit(False, self.run_id, f"治理失败: {exc}")
        finally:
            if client is not None:
                client.close()
            db_session.close()

    def _check_course(self, course: Course, client: LMSClient, db_session, config_service: GovernanceConfigService) -> CourseGovernanceResult:
        course_id = course.course_id or ""
        group_id = course.group_id or ""
        title = course.title or ""

        creator_email = ""
        creator_name = ""
        if course.umu_id:
            creator = db_session.query(User).filter_by(umu_id=course.umu_id).first()
            if creator:
                creator_email = creator.email or ""
                creator_name = creator.name or ""

        umu_link = f"https://www.umu.cn/course/index#/groups/{course_id}/groupInfo/view"

        try:
            lesson_type = int(course.lesson_type) if course.lesson_type is not None else None
        except (ValueError, TypeError):
            lesson_type = None

        excluded_course_ids = config_service.get_config("excluded_course_ids", [])
        if course_id and excluded_course_ids and str(course_id) in [str(c) for c in excluded_course_ids]:
            return CourseGovernanceResult(
                course_id=course_id, group_id=group_id, course_name=title,
                creator_email=creator_email, creator_name=creator_name, umu_link=umu_link,
                overall_compliant=True, overall_level="ok",
                rule_results=[{"rule_id": i, "rule_name": f"规则{i}", "compliant": True, "level": "ok", "issue": ""} for i in range(1, 9)],
                issues=[],
            )

        rule_results: list[RuleResult] = []
        rule_results.append(self._check_rule1_title(title, lesson_type, config_service))
        rule_results.append(self._check_rule2_type(title, lesson_type, config_service))
        rule_results.append(self._check_rule3_category(course.categoryArr, config_service))
        rule_results.append(self._check_rule4_description(course.desc, course.multimedia_id, client, config_service, lesson_type))
        rule_results.append(self._check_rule5_duration(db_session, group_id, config_service, lesson_type, course.umu_id))

        sessions = self._get_local_sessions(group_id, db_session)
        attempted_fetch = False
        if not sessions:
            fetched = self._fetch_and_save_sessions(client, group_id, db_session)
            attempted_fetch = True
            if fetched:
                sessions = self._get_local_sessions(group_id, db_session)

        if not sessions and attempted_fetch:
            no_session_issue = "没有查询到课程小节"
            if lesson_type in (1, 2):
                rule_results.append(RuleResult(rule_id=6, rule_name="课程评价/考试", compliant=False, level="major", issue=no_session_issue))
            rule_results.append(RuleResult(rule_id=7, rule_name="必修小节", compliant=False, level="major", issue=no_session_issue))
            if lesson_type in (1, 2):
                rule_results.append(RuleResult(rule_id=8, rule_name="课程课件", compliant=False, level="major", issue=no_session_issue))
        else:
            rule_results.append(self._check_rule6_evaluation(sessions, lesson_type, config_service))
            rule_results.append(self._check_rule7_required(sessions))
            rule_results.append(self._check_rule8_materials(sessions, lesson_type, client, config_service))

        levels = [r.level for r in rule_results]
        has_major = any(l == "major" for l in levels)
        has_unknown = any(l == "unknown" for l in levels)
        has_minor = any(l == "minor" for l in levels)

        if has_major:
            overall_level = "major"
            overall_compliant = False
        elif has_unknown:
            overall_level = "unknown"
            overall_compliant = False
        elif has_minor:
            overall_level = "minor"
            overall_compliant = False
        else:
            overall_level = "ok"
            overall_compliant = True

        issues = [r.issue for r in rule_results if r.issue]

        return CourseGovernanceResult(
            course_id=course_id, group_id=group_id, course_name=title,
            creator_email=creator_email, creator_name=creator_name, umu_link=umu_link,
            overall_compliant=overall_compliant, overall_level=overall_level,
            rule_results=[{"rule_id": r.rule_id, "rule_name": r.rule_name, "compliant": r.compliant, "level": r.level, "issue": r.issue} for r in rule_results],
            issues=issues,
        )

    @staticmethod
    def _check_rule1_title(title: str, lesson_type: int | None, config_service: GovernanceConfigService) -> RuleResult:
        forbidden_words = set(config_service.get_config("forbidden_words", []))
        exception_words = set(config_service.get_config("exception_words", []))
        fallback_words = set(config_service.get_config("fallback_forbidden_words", []))

        if title and len(title) < 2:
            return RuleResult(rule_id=1, rule_name="课程名称", compliant=False, level="major", issue="课程标题字符数不足 2 个")

        fallback_hits = _title_matched_forbidden_words(title, fallback_words)
        if fallback_hits:
            return RuleResult(rule_id=1, rule_name="课程名称", compliant=False, level="major", issue=f"课程标题包含兜底禁词：{'、'.join(fallback_hits)}")

        if lesson_type == 0:
            return RuleResult(rule_id=1, rule_name="课程名称", compliant=True, level="ok", issue="")

        forbidden_hits = _title_matched_forbidden_words(title, forbidden_words)
        if not forbidden_hits:
            return RuleResult(rule_id=1, rule_name="课程名称", compliant=True, level="ok", issue="")

        if _title_hits_exception(title, exception_words):
            return RuleResult(rule_id=1, rule_name="课程名称", compliant=True, level="ok", issue="")

        return RuleResult(rule_id=1, rule_name="课程名称", compliant=False, level="major", issue=f"课程名称涉及非培训内容（命中禁词：{'、'.join(forbidden_hits)}）")

    @staticmethod
    def _check_rule2_type(title: str, lesson_type: int | None, config_service: GovernanceConfigService) -> RuleResult:
        forbidden_words = set(config_service.get_config("forbidden_words", []))
        exception_words = set(config_service.get_config("exception_words", []))
        forbidden_hits = _title_matched_forbidden_words(title, forbidden_words)
        hits_exception = _title_hits_exception(title, exception_words)

        if lesson_type in (0, 1, 2):
            if forbidden_hits and not hits_exception:
                return RuleResult(rule_id=2, rule_name="课程形式", compliant=False, level="major", issue=f"培训类课程标题包含非培训关键词：{'、'.join(forbidden_hits)}")
            return RuleResult(rule_id=2, rule_name="课程形式", compliant=True, level="ok", issue="")

        if lesson_type == 999:
            if not forbidden_hits or hits_exception:
                return RuleResult(rule_id=2, rule_name="课程形式", compliant=True, level="minor", issue="非培训类课程标题疑似与形式错位")
            return RuleResult(rule_id=2, rule_name="课程形式", compliant=True, level="ok", issue="")

        return RuleResult(rule_id=2, rule_name="课程形式", compliant=True, level="unknown", issue="无法识别课程形式")

    @staticmethod
    def _check_rule3_category(category_arr, config_service: GovernanceConfigService) -> RuleResult:
        valid_categories = set(config_service.get_config("valid_categories", []))
        if not category_arr:
            return RuleResult(rule_id=3, rule_name="内容分类", compliant=False, level="major", issue="课程缺少通用力/专业力/领导力/新兴力分类")

        names = set()
        if isinstance(category_arr, list):
            for item in category_arr:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("categoryName") or ""
                    if name:
                        names.add(name)
                elif isinstance(item, str):
                    names.add(item)
        elif isinstance(category_arr, dict):
            name = category_arr.get("name") or category_arr.get("categoryName") or ""
            if name:
                names.add(name)

        for name in names:
            for valid in valid_categories:
                if valid in name:
                    return RuleResult(rule_id=3, rule_name="内容分类", compliant=True, level="ok", issue="")

        return RuleResult(rule_id=3, rule_name="内容分类", compliant=False, level="major", issue="课程缺少通用力/专业力/领导力/新兴力分类")

    @staticmethod
    def _check_rule4_description(desc: str | None, multimedia_id: str | None, client: LMSClient, config_service: GovernanceConfigService, lesson_type: int | None = None) -> RuleResult:
        if lesson_type == 0:
            return RuleResult(rule_id=4, rule_name="课程介绍", compliant=True, level="ok", issue="")

        meaningless_placeholders = set(config_service.get_config("meaningless_placeholders", []))
        desc_str = (desc or "").strip()

        if desc_str and desc_str not in meaningless_placeholders:
            if desc_str.startswith("课程大纲：") and len(desc_str) > len("课程大纲："):
                return RuleResult(rule_id=4, rule_name="课程介绍", compliant=True, level="ok", issue="")
            if len(desc_str) > 4 and desc_str != "课程大纲：":
                return RuleResult(rule_id=4, rule_name="课程介绍", compliant=True, level="ok", issue="")

        if multimedia_id:
            try:
                resp = client.get("/ajax/multimedia/fulltextinfo", params={"top_section_id": multimedia_id})
                data = resp.get("data", {}) if isinstance(resp, dict) else {}
                content = data.get("content", "") if isinstance(data, dict) else ""
                if content and "<img" in content:
                    return RuleResult(rule_id=4, rule_name="课程介绍", compliant=True, level="ok", issue="")
            except Exception:
                pass

        if not desc_str:
            return RuleResult(rule_id=4, rule_name="课程介绍", compliant=False, level="major", issue="课程介绍为空且无图片介绍" if not multimedia_id else "课程介绍为空且非图片型介绍")

        if desc_str in meaningless_placeholders:
            return RuleResult(rule_id=4, rule_name="课程介绍", compliant=False, level="major", issue="课程介绍为无意义占位符")

        return RuleResult(rule_id=4, rule_name="课程介绍", compliant=False, level="unknown", issue="课程介绍内容过短，需人工确认")

    @staticmethod
    def _check_rule5_duration(db_session, group_id: str, config_service: GovernanceConfigService, lesson_type: int | None = None, umu_id: str | None = None) -> RuleResult:
        if not group_id:
            return RuleResult(rule_id=5, rule_name="课程学时", compliant=False, level="major", issue="课程缺少分组ID，无法判断学时")

        records = db_session.query(CourseGroupTime).filter_by(group_id=group_id).all()
        if not records:
            return RuleResult(rule_id=5, rule_name="课程学时", compliant=False, level="major", issue="未设置课程学时")

        total_hours = 0.0
        for r in records:
            if r.start_time and r.end_time:
                total_hours += (r.end_time - r.start_time).total_seconds() / 3600.0

        if lesson_type == 0 and umu_id != "11875281" and total_hours > 3:
            return RuleResult(rule_id=5, rule_name="课程学时", compliant=False, level="major", issue="线上课程学时异常，建议检查学时设置")

        max_duration = config_service.get_config("max_duration_hours", 30)
        if total_hours > max_duration:
            return RuleResult(rule_id=5, rule_name="课程学时", compliant=False, level="major", issue=f"课程学时设置可能错误（{total_hours:.1f}小时）")

        return RuleResult(rule_id=5, rule_name="课程学时", compliant=True, level="ok", issue="")

    @staticmethod
    def _check_rule6_evaluation(sessions: list[SessionModel], lesson_type: int | None, config_service: GovernanceConfigService) -> RuleResult:
        if lesson_type not in (1, 2):
            return RuleResult(rule_id=6, rule_name="课程评价/考试", compliant=True, level="ok", issue="")

        if not sessions:
            return RuleResult(rule_id=6, rule_name="课程评价/考试", compliant=True, level="unknown", issue="缺少小节数据，无法判断")

        for s in sessions:
            if s.session_type == "10" and s.is_require == 1:
                return RuleResult(rule_id=6, rule_name="课程评价/考试", compliant=True, level="ok", issue="")

        for s in sessions:
            if s.session_type == "6" and s.is_require == 1:
                if s.type_name == "评价":
                    return RuleResult(rule_id=6, rule_name="课程评价/考试", compliant=True, level="ok", issue="")
                if GovernanceWorker._questions_have_evaluation(s.questions, config_service):
                    return RuleResult(rule_id=6, rule_name="课程评价/考试", compliant=True, level="ok", issue="")

        for s in sessions:
            if s.session_type == "1" and s.is_require == 1:
                if GovernanceWorker._questions_have_evaluation(s.questions, config_service):
                    return RuleResult(rule_id=6, rule_name="课程评价/考试", compliant=True, level="ok", issue="")

        return RuleResult(rule_id=6, rule_name="课程评价/考试", compliant=False, level="major", issue="课程缺少评价或考试小节")

    @staticmethod
    def _questions_have_evaluation(questions, config_service: GovernanceConfigService) -> bool:
        evaluation_keywords = set(config_service.get_config("evaluation_keywords", []))
        if not questions or not isinstance(questions, list):
            return False
        for q in questions:
            title = GovernanceWorker._extract_question_title(q)
            if not title:
                continue
            for kw in evaluation_keywords:
                if kw in title:
                    return True
        return False

    @staticmethod
    def _extract_question_title(question) -> str:
        if isinstance(question, str):
            return question
        if not isinstance(question, dict):
            return ""
        title = question.get("title") or question.get("question") or question.get("name") or ""
        if title:
            return title
        info = question.get("questionInfo", {})
        if isinstance(info, dict):
            title = info.get("questionTitle") or info.get("title") or info.get("question") or info.get("name") or ""
            if title:
                return title
        setup = question.get("setup", {})
        if isinstance(setup, dict):
            return setup.get("title") or setup.get("question") or setup.get("name") or ""
        return ""

    @staticmethod
    def _check_rule7_required(sessions: list[SessionModel]) -> RuleResult:
        if not sessions:
            return RuleResult(rule_id=7, rule_name="必修小节", compliant=True, level="unknown", issue="缺少小节数据，无法判断")
        all_optional = all(s.is_require == 0 for s in sessions)
        if all_optional:
            return RuleResult(rule_id=7, rule_name="必修小节", compliant=False, level="major", issue="所有小节均为选修")
        return RuleResult(rule_id=7, rule_name="必修小节", compliant=True, level="ok", issue="")

    @staticmethod
    def _check_rule8_materials(sessions: list[SessionModel], lesson_type: int | None, client: LMSClient, config_service: GovernanceConfigService) -> RuleResult:
        if lesson_type not in (1, 2):
            return RuleResult(rule_id=8, rule_name="课程课件", compliant=True, level="ok", issue="")

        if not sessions:
            return RuleResult(rule_id=8, rule_name="课程课件", compliant=False, level="major", issue="缺少小节数据，无法判断课件")

        if any(s.session_type in ("13", "15") for s in sessions):
            return RuleResult(rule_id=8, rule_name="课程课件", compliant=True, level="ok", issue="")

        doc_sessions = [s for s in sessions if s.session_type == "14"]
        if not doc_sessions:
            return RuleResult(rule_id=8, rule_name="课程课件", compliant=False, level="major", issue="课程未上传课件（无文档小节）")

        empty_content_marker = config_service.get_config("empty_content_marker", "b96beb74eb4e5ea5419d74b956c5404c")
        has_valid_material = False
        for s in doc_sessions:
            try:
                resp = client.get(f"/uapi/v1/element/{s.session_id}")
                raw = resp.get("data", resp) if isinstance(resp, dict) else resp
                if empty_content_marker not in str(raw):
                    has_valid_material = True
                    break
            except Exception:
                continue

        if has_valid_material:
            return RuleResult(rule_id=8, rule_name="课程课件", compliant=True, level="ok", issue="")

        return RuleResult(rule_id=8, rule_name="课程课件", compliant=False, level="major", issue="课程未上传有效课件")

    @staticmethod
    def _get_local_sessions(group_id: str, db_session) -> list[SessionModel]:
        if not group_id:
            return []
        return db_session.query(SessionModel).filter_by(course_id=group_id).all()

    def _fetch_and_save_sessions(self, client: LMSClient, group_id: str, db_session) -> int:
        if not group_id:
            return 0
        items = self._fetch_session_list(client, group_id)
        records = self._collect_session_records(items, group_id)
        for cid in self._extract_chapter_ids(items):
            chapter_items = self._fetch_chapter_items(client, group_id, cid)
            records.extend(self._collect_session_records(chapter_items, group_id, cid))
        if records:
            self._upsert_sessions(records, db_session)
        return len(records)

    @staticmethod
    def _fetch_session_list(client: LMSClient, group_id: str) -> list[dict]:
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
            return data.get("list", []) if isinstance(data, dict) else []
        except Exception:
            return []

    @staticmethod
    def _extract_chapter_ids(items: list[dict]) -> list[str]:
        ids = []
        for item in items:
            if item.get("item_type") == 2 or str(item.get("item_type")) == "2":
                cid = str(item.get("id", ""))
                if cid:
                    ids.append(cid)
        return ids

    @staticmethod
    def _fetch_chapter_items(client: LMSClient, group_id: str, chapter_id: str) -> list[dict]:
        try:
            result = client.get(
                "/ajax/session/getsessionlistbygroup",
                params={
                    "group_id": group_id,
                    "chapter_id": chapter_id,
                    "page": 1,
                    "size": 500,
                    "status_str": "0,1",
                },
            )
            data = result.get("data", {}) if isinstance(result, dict) else {}
            return data.get("list", []) if isinstance(data, dict) else []
        except Exception:
            return []

    @staticmethod
    def _collect_session_records(items: list[dict], group_id: str, chapter_id: str = "") -> list[dict]:
        records = []
        for item in items:
            record = GovernanceWorker._build_session_record(item, group_id, chapter_id)
            if record:
                records.append(record)
        return records

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
    def _upsert_sessions(records: list[dict], db_session) -> None:
        for record in records:
            sid = record.get("session_id")
            if not sid:
                continue
            existing = db_session.query(SessionModel).filter_by(session_id=sid).first()
            if existing:
                for key, value in record.items():
                    if key != "raw_data":
                        setattr(existing, key, value)
                existing.raw_data = record["raw_data"]
            else:
                db_session.add(SessionModel(**record))
        db_session.commit()

    def _save_result(self, run_id: str, result: CourseGovernanceResult, db_session) -> None:
        gr = GovernanceResult(
            run_id=run_id,
            course_id=result.course_id,
            group_id=result.group_id,
            course_name=result.course_name,
            creator_email=result.creator_email,
            creator_name=result.creator_name,
            umu_link=result.umu_link,
            overall_compliant=result.overall_compliant,
            overall_level=result.overall_level,
            rule_results=result.rule_results,
            issues=result.issues,
            owner=self.owner,
        )
        db_session.add(gr)
        db_session.commit()


class GovernanceService(QObject):
    """Manages governance operations for the GUI."""

    progress_updated = pyqtSignal(int, int, int, int, int, str, str)
    # progress, total, compliant, non_compliant, major, current_course, message
    governance_finished = pyqtSignal(bool, str, str)  # success, run_id, message

    def __init__(self, database_url: str = DEFAULT_DATABASE_URL) -> None:
        super().__init__()
        self.database_url = database_url
        self.config_service = GovernanceConfigService(database_url)
        self._worker: GovernanceWorker | None = None
        self._recover_interrupted_runs()

    def _recover_interrupted_runs(self) -> None:
        engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        db_session = SessionLocal()
        try:
            orphaned = db_session.query(GovernanceRun).filter_by(status="running").all()
            for run in orphaned:
                run.status = "interrupted"
                run.error_message = "应用重启导致任务中断"
            if orphaned:
                db_session.commit()
                logger.info("Recovered %d interrupted governance runs", len(orphaned))
        except Exception:
            db_session.rollback()
        finally:
            db_session.close()

    def start_governance(self, serialized_session: str, start_date: str | None = None,
                         end_date: str | None = None, owner: str = "") -> str:
        if self._worker and self._worker.isRunning():
            return ""
        run_id = str(uuid.uuid4())
        self._worker = GovernanceWorker(
            self.database_url, serialized_session, run_id, start_date, end_date, owner=owner
        )
        self._worker.progress_updated.connect(self.progress_updated)
        self._worker.governance_finished.connect(self.governance_finished)
        self._worker.start()
        return run_id

    def resume_governance(self, run_id: str, serialized_session: str, owner: str = "") -> bool:
        if self._worker and self._worker.isRunning():
            return False
        engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        try:
            run = db_session.query(GovernanceRun).filter_by(run_id=run_id).first()
            if not run:
                return False
            if run.status not in ("interrupted", "failed"):
                return False
        finally:
            db_session.close()

        self._worker = GovernanceWorker(
            self.database_url, serialized_session, run_id, resume=True, owner=owner
        )
        self._worker.progress_updated.connect(self.progress_updated)
        self._worker.governance_finished.connect(self.governance_finished)
        self._worker.start()
        return True

    def is_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def cancel(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()

    def preview_governance(self, start_date: str | None = None, end_date: str | None = None, owner: str = "") -> dict:
        engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        Base.metadata.create_all(engine)
        db_session = SessionLocal()
        try:
            excluded_umu_id = self.config_service.get_config("excluded_umu_id", "13264912")
            excluded_lesson_type = self.config_service.get_config("excluded_lesson_type", "999")
            query = (
                db_session.query(Course)
                .filter(Course.umu_id != excluded_umu_id)
                .filter(Course.lesson_type != excluded_lesson_type)
            )
            if owner:
                query = query.filter(
                    or_(Course.synced_by == owner, Course.synced_by.is_(None))
                )

            user_query = db_session.query(User)
            if owner:
                user_query = user_query.filter(
                    or_(User.synced_by == owner, User.synced_by.is_(None))
                )

            if start_date:
                try:
                    start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                    query = query.filter(Course.creat_time >= start_dt)
                except (ValueError, TypeError):
                    pass
            if end_date:
                try:
                    end_dt = datetime.strptime(end_date, "%Y-%m-%d")
                    query = query.filter(Course.creat_time < end_dt + timedelta(days=1))
                except (ValueError, TypeError):
                    pass

            course_count = query.count()
            user_count = user_query.count()
            last_course = query.order_by(Course.update_time.desc()).first()
            last_sync = None
            if last_course and last_course.update_time:
                last_sync = last_course.update_time.isoformat()

            return {"course_count": course_count, "user_count": user_count, "last_sync": last_sync}
        finally:
            db_session.close()

    def get_runs(self, owner: str = "") -> list[dict]:
        engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        try:
            query = db_session.query(GovernanceRun).order_by(GovernanceRun.started_at.desc())
            if owner:
                query = query.filter(
                    or_(GovernanceRun.owner == owner, GovernanceRun.owner.is_(None))
                )
            runs = query.all()
            result = []
            for r in runs:
                compliant_rate = None
                if r.status in ("completed", "interrupted") and r.total_courses:
                    compliant_count = db_session.query(GovernanceResult).filter_by(
                        run_id=r.run_id, overall_compliant=True
                    ).count()
                    compliant_rate = round((compliant_count / r.total_courses) * 100)
                result.append({
                    "run_id": r.run_id,
                    "started_at": r.started_at.isoformat() if r.started_at else None,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                    "total_courses": r.total_courses,
                    "processed_courses": r.processed_courses,
                    "status": r.status,
                    "error_message": r.error_message,
                    "start_date": r.start_date,
                    "end_date": r.end_date,
                    "compliant_rate": compliant_rate,
                })
            return result
        finally:
            db_session.close()

    def get_results(self, run_id: str, owner: str = "") -> dict:
        engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        try:
            run_query = db_session.query(GovernanceRun).filter_by(run_id=run_id)
            if owner:
                run_query = run_query.filter(
                    or_(GovernanceRun.owner == owner, GovernanceRun.owner.is_(None))
                )
            run = run_query.first()
            if not run:
                return {"run": None, "results": [], "stats": {}}

            results = db_session.query(GovernanceResult).filter_by(run_id=run_id).all()
            total = len(results)
            compliant = sum(1 for r in results if r.overall_compliant)
            major = sum(1 for r in results if r.overall_level in ("major", "minor", "unknown"))

            return {
                "run": {
                    "run_id": run.run_id,
                    "started_at": run.started_at.isoformat() if run.started_at else None,
                    "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                    "total_courses": run.total_courses,
                    "processed_courses": run.processed_courses,
                    "status": run.status,
                    "error_message": run.error_message,
                    "start_date": run.start_date,
                    "end_date": run.end_date,
                },
                "results": [
                    {
                        "course_id": r.course_id,
                        "course_name": r.course_name,
                        "creator_email": r.creator_email,
                        "creator_name": r.creator_name,
                        "umu_link": r.umu_link,
                        "overall_compliant": r.overall_compliant,
                        "overall_level": r.overall_level,
                        "rule_results": r.rule_results,
                        "issues": r.issues,
                    }
                    for r in results
                ],
                "stats": {"total": total, "compliant": compliant, "major": major},
            }
        finally:
            db_session.close()

    def delete_run(self, run_id: str, owner: str = "") -> bool:
        engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        try:
            run_query = db_session.query(GovernanceRun).filter_by(run_id=run_id)
            if owner:
                run_query = run_query.filter(
                    or_(GovernanceRun.owner == owner, GovernanceRun.owner.is_(None))
                )
            run = run_query.first()
            if not run:
                return False
            db_session.query(GovernanceResult).filter_by(run_id=run_id).delete()
            db_session.delete(run)
            db_session.commit()
            return True
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()

    def clear_all_runs(self, owner: str = "") -> int:
        engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        SessionLocal = sessionmaker(bind=engine)
        db_session = SessionLocal()
        try:
            if owner:
                # Delete results for runs owned by this user
                run_ids = [
                    r.run_id for r in
                    db_session.query(GovernanceRun).filter(
                        or_(GovernanceRun.owner == owner, GovernanceRun.owner.is_(None))
                    ).all()
                ]
                if run_ids:
                    db_session.query(GovernanceResult).filter(
                        GovernanceResult.run_id.in_(run_ids)
                    ).delete(synchronize_session=False)
                count = db_session.query(GovernanceRun).filter(
                    or_(GovernanceRun.owner == owner, GovernanceRun.owner.is_(None))
                ).delete(synchronize_session=False)
            else:
                db_session.query(GovernanceResult).delete()
                count = db_session.query(GovernanceRun).delete()
            db_session.commit()
            return count
        except Exception:
            db_session.rollback()
            raise
        finally:
            db_session.close()
