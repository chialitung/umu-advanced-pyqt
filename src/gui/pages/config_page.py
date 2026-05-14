"""Governance config page."""

from __future__ import annotations

import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..components.styled_button import StyledButton
from ..styles import SLATE_400, SLATE_500, SLATE_800


class ConfigPage(QWidget):
    """Page for configuring governance rules."""

    def __init__(self, auth_service, config_service, show_toast=None, parent=None) -> None:
        super().__init__(parent)
        self._auth_service = auth_service
        self._config_service = config_service
        self._show_toast = show_toast
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        # Main layout with scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(40, 32, 40, 32)
        main_layout.setSpacing(20)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title
        title = QLabel("治理规则配置")
        title.setStyleSheet(f"color: {SLATE_800}; font-size: 22px; font-weight: 700;")
        main_layout.addWidget(title)

        # Description
        desc = QLabel("配置培训数据治理的各项规则参数。修改后请点击保存。")
        desc.setStyleSheet(f"color: {SLATE_500}; font-size: 14px;")
        desc.setWordWrap(True)
        main_layout.addWidget(desc)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self._save_btn = StyledButton("保存配置", StyledButton.PRIMARY)
        self._backup_btn = StyledButton("备份配置", StyledButton.SECONDARY)
        self._restore_btn = StyledButton("从文件恢复", StyledButton.SECONDARY)
        self._reset_btn = StyledButton("恢复默认", StyledButton.GHOST)

        btn_layout.addWidget(self._save_btn)
        btn_layout.addWidget(self._backup_btn)
        btn_layout.addWidget(self._restore_btn)
        btn_layout.addWidget(self._reset_btn)
        btn_layout.addStretch()
        main_layout.addLayout(btn_layout)

        # Scroll area for config groups
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(0, 0, 0, 0)
        scroll_layout.setSpacing(20)
        scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Rule 1 & 2: Course title
        group1 = QGroupBox("规则 1 & 2: 课程标题")
        g1_layout = QVBoxLayout(group1)
        g1_layout.setSpacing(12)

        g1_layout.addWidget(QLabel("禁用词（每行一个）:"))
        self._forbidden_words = QTextEdit()
        g1_layout.addWidget(self._forbidden_words)

        g1_layout.addWidget(QLabel("例外词（每行一个）:"))
        self._exception_words = QTextEdit()
        g1_layout.addWidget(self._exception_words)

        g1_layout.addWidget(QLabel("后备禁用词（每行一个）:"))
        self._fallback_words = QTextEdit()
        g1_layout.addWidget(self._fallback_words)

        scroll_layout.addWidget(group1)

        # Rule 3: Category
        group3 = QGroupBox("规则 3: 内容分类")
        g3_layout = QVBoxLayout(group3)
        g3_layout.addWidget(QLabel("有效分类（每行一个）:"))
        self._valid_categories = QTextEdit()
        g3_layout.addWidget(self._valid_categories)
        scroll_layout.addWidget(group3)

        # Rule 4: Description
        group4 = QGroupBox("规则 4: 课程介绍")
        g4_layout = QVBoxLayout(group4)
        g4_layout.addWidget(QLabel("无意义占位符（每行一个）:"))
        self._meaningless_placeholders = QTextEdit()
        g4_layout.addWidget(self._meaningless_placeholders)
        scroll_layout.addWidget(group4)

        # Rule 6: Evaluation
        group6 = QGroupBox("规则 6: 课程评价/考试")
        g6_layout = QVBoxLayout(group6)
        g6_layout.addWidget(QLabel("评价关键词（每行一个）:"))
        self._evaluation_keywords = QTextEdit()
        g6_layout.addWidget(self._evaluation_keywords)
        scroll_layout.addWidget(group6)

        # Rule 8: Materials
        group8 = QGroupBox("规则 8: 课程课件")
        g8_layout = QVBoxLayout(group8)
        g8_layout.addWidget(QLabel("空内容标记:"))
        self._empty_marker = QLineEdit()
        g8_layout.addWidget(self._empty_marker)
        g8_layout.addWidget(self._helper_label("检测到该标记时视为课件内容为空"))
        scroll_layout.addWidget(group8)

        # Global exclusions
        group_global = QGroupBox("全局排除参数")
        gg_layout = QVBoxLayout(group_global)
        gg_layout.setSpacing(12)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("排除 umu_id:"))
        self._excluded_umu_id = QLineEdit()
        row1.addWidget(self._excluded_umu_id)
        gg_layout.addLayout(row1)
        gg_layout.addWidget(self._helper_label("该用户的课程将被排除在治理范围外"))

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("排除 lesson_type:"))
        self._excluded_lesson_type = QLineEdit()
        row2.addWidget(self._excluded_lesson_type)
        gg_layout.addLayout(row2)
        gg_layout.addWidget(self._helper_label("该类型的课程将被排除（默认 999）"))

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("最大时长（小时）:"))
        self._max_duration = QSpinBox()
        self._max_duration.setMinimum(1)
        self._max_duration.setMaximum(999)
        row3.addWidget(self._max_duration)
        row3.addStretch()
        gg_layout.addLayout(row3)
        gg_layout.addWidget(self._helper_label("超过此时长的课程将被标记为异常"))

        gg_layout.addWidget(QLabel("例外课程 ID（每行一个）:"))
        self._excluded_course_ids = QTextEdit()
        gg_layout.addWidget(self._excluded_course_ids)
        gg_layout.addWidget(self._helper_label("这些课程 ID 将被跳过治理审核"))

        scroll_layout.addWidget(group_global)
        # Ensure every QTextEdit can display 10 lines without scrolling
        for text_edit in scroll_widget.findChildren(QTextEdit):
            fm = text_edit.fontMetrics()
            # lineSpacing * 10 lines + padding(20) + border(3) + document margin(8)
            text_edit.setMinimumHeight(fm.lineSpacing() * 10 + 31)

        scroll_layout.addStretch()

        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)

    def _connect_signals(self) -> None:
        self._save_btn.clicked.connect(self._on_save)
        self._backup_btn.clicked.connect(self._on_backup)
        self._restore_btn.clicked.connect(self._on_restore)
        self._reset_btn.clicked.connect(self._on_reset)
        self._config_service.config_changed.connect(self.load_config)

    def refresh(self) -> None:
        self.load_config()

    def load_config(self) -> None:
        configs = self._config_service.load_config()
        self._forbidden_words.setPlainText("\n".join(configs.get("forbidden_words", [])))
        self._exception_words.setPlainText("\n".join(configs.get("exception_words", [])))
        self._fallback_words.setPlainText("\n".join(configs.get("fallback_forbidden_words", [])))
        self._valid_categories.setPlainText("\n".join(configs.get("valid_categories", [])))
        self._meaningless_placeholders.setPlainText("\n".join(configs.get("meaningless_placeholders", [])))
        self._evaluation_keywords.setPlainText("\n".join(configs.get("evaluation_keywords", [])))
        self._empty_marker.setText(configs.get("empty_content_marker", ""))
        self._excluded_umu_id.setText(configs.get("excluded_umu_id", ""))
        self._excluded_lesson_type.setText(configs.get("excluded_lesson_type", ""))
        self._max_duration.setValue(configs.get("max_duration_hours", 30))
        self._excluded_course_ids.setPlainText("\n".join(str(c) for c in configs.get("excluded_course_ids", [])))

    @staticmethod
    def _helper_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setStyleSheet(f"color: {SLATE_400}; font-size: 12px;")
        return label

    def _get_configs(self) -> dict:
        return {
            "forbidden_words": [w.strip() for w in self._forbidden_words.toPlainText().split("\n") if w.strip()],
            "exception_words": [w.strip() for w in self._exception_words.toPlainText().split("\n") if w.strip()],
            "fallback_forbidden_words": [w.strip() for w in self._fallback_words.toPlainText().split("\n") if w.strip()],
            "valid_categories": [w.strip() for w in self._valid_categories.toPlainText().split("\n") if w.strip()],
            "meaningless_placeholders": [w.strip() for w in self._meaningless_placeholders.toPlainText().split("\n") if w.strip()],
            "evaluation_keywords": [w.strip() for w in self._evaluation_keywords.toPlainText().split("\n") if w.strip()],
            "empty_content_marker": self._empty_marker.text().strip(),
            "excluded_umu_id": self._excluded_umu_id.text().strip(),
            "excluded_lesson_type": self._excluded_lesson_type.text().strip(),
            "max_duration_hours": self._max_duration.value(),
            "excluded_course_ids": [w.strip() for w in self._excluded_course_ids.toPlainText().split("\n") if w.strip()],
        }

    def _validate(self) -> tuple[bool, str]:
        """Validate config fields. Returns (is_valid, error_message)."""
        # Validate excluded_course_ids are numeric
        course_ids_text = self._excluded_course_ids.toPlainText().strip()
        if course_ids_text:
            for line in course_ids_text.split("\n"):
                line = line.strip()
                if line and not line.isdigit():
                    return False, f"例外课程 ID 必须全部为数字，发现非法值: {line}"

        # Validate empty_content_marker is not empty
        if not self._empty_marker.text().strip():
            return False, "空内容标记不能为空"

        return True, ""

    def _highlight_invalid(self, widget, invalid: bool) -> None:
        """Highlight or clear invalid field styling."""
        from ..styles import DANGER_500, SLATE_200
        border_color = DANGER_500 if invalid else SLATE_200
        if isinstance(widget, (QLineEdit, QTextEdit)):
            widget.setStyleSheet(f"""
                QLineEdit, QTextEdit {{
                    border: 1.5px solid {border_color};
                    border-radius: 8px;
                    padding: 8px 14px;
                }}
            """)

    def _on_save(self) -> None:
        is_valid, error = self._validate()
        if not is_valid:
            if self._show_toast:
                self._show_toast(error, "error")
            else:
                QMessageBox.warning(self, "验证失败", error)
            return

        self._config_service.save_config(self._get_configs())
        if self._show_toast:
            self._show_toast("配置已保存", "success")
        else:
            QMessageBox.information(self, "保存成功", "配置已保存。")

    def _on_backup(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "备份配置", "governance_config.json", "JSON (*.json)")
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write(self._config_service.backup_config())
            QMessageBox.information(self, "备份成功", f"配置已保存到:\n{path}")

    def _on_restore(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "恢复配置", "", "JSON (*.json)")
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    self._config_service.restore_config(f.read())
                QMessageBox.information(self, "恢复成功", "配置已从文件恢复。请检查无误后保存。")
            except Exception as exc:
                QMessageBox.critical(self, "恢复失败", str(exc))

    def _on_reset(self) -> None:
        reply = QMessageBox.question(
            self, "确认恢复默认",
            "确定要恢复所有配置为默认值吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            reply2 = QMessageBox.question(
                self, "二次确认",
                "再次确认：将所有配置恢复为默认值？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply2 == QMessageBox.StandardButton.Yes:
                self._config_service.reset_config()
                QMessageBox.information(self, "已恢复", "配置已恢复为默认值。")
