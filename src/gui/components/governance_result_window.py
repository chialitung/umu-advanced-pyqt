"""Independent window for displaying governance results."""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..components.empty_state import EmptyState
from ..components.stat_card import StatCard
from ..components.styled_button import StyledButton
from ..styles import (
    BRAND_500,
    DANGER_600,
    SLATE_200,
    SLATE_500,
    SLATE_800,
    SUCCESS_500,
    WARNING_600,
)


class GovernanceResultWindow(QDialog):
    """Independent window displaying governance results for a single run."""

    def __init__(self, governance_service, run_id: str, parent=None) -> None:
        super().__init__(parent)
        self._governance_service = governance_service
        self._run_id = run_id
        self._all_results: list[dict] = []
        self._setup_window()
        self._setup_ui()
        self._load_results()

    def _setup_window(self) -> None:
        self.setWindowFlags(Qt.WindowType.Dialog)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(1200, 700)
        self.resize(1300, 800)

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 24, 32, 24)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title
        self._title_label = QLabel("治理结果")
        self._title_label.setStyleSheet(f"color: {SLATE_800}; font-size: 22px; font-weight: 700;")
        layout.addWidget(self._title_label)

        # Info bar
        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)
        self._info_time = QLabel("")
        self._info_time.setStyleSheet(f"color: {SLATE_500}; font-size: 13px;")
        self._info_range = QLabel("")
        self._info_range.setStyleSheet(f"color: {SLATE_500}; font-size: 13px;")
        self._info_status = QLabel("")
        self._info_status.setStyleSheet(f"font-size: 13px; font-weight: 600;")
        info_layout.addWidget(self._info_time)
        info_layout.addWidget(self._info_range)
        info_layout.addWidget(self._info_status)
        info_layout.addStretch()
        layout.addLayout(info_layout)

        # Stats row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        self._stat_total = StatCard("课程总数", "-")
        self._stat_compliant = StatCard("合规", "-")
        self._stat_major = StatCard("需治理", "-")
        self._stat_minor = StatCard("次要问题", "-")
        stats_layout.addWidget(self._stat_total)
        stats_layout.addWidget(self._stat_compliant)
        stats_layout.addWidget(self._stat_major)
        stats_layout.addWidget(self._stat_minor)
        layout.addLayout(stats_layout)

        # Filter row
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        self._level_filter = QComboBox()
        self._level_filter.addItems(["全部等级", "合规", "需治理", "次要问题", "未知"])
        self._level_filter.currentIndexChanged.connect(self._filter_results)
        filter_layout.addWidget(QLabel("筛选:"))
        filter_layout.addWidget(self._level_filter)

        self._rule_filter = QComboBox()
        self._rule_filter.addItems(
            [
                "全部规则",
                "规则1: 课程名称",
                "规则2: 课程形式",
                "规则3: 内容分类",
                "规则4: 课程介绍",
                "规则5: 课程学时",
                "规则6: 课程评价/考试",
                "规则7: 必修小节",
                "规则8: 课程课件",
            ]
        )
        self._rule_filter.currentIndexChanged.connect(self._filter_results)
        filter_layout.addWidget(self._rule_filter)

        self._export_btn = StyledButton("导出 Excel", StyledButton.SECONDARY)
        self._export_btn.clicked.connect(self._on_export)
        filter_layout.addWidget(self._export_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Results table: course_name, creator_email, level, issues, action
        self._results_table = QTableWidget()
        self._results_table.setColumnCount(5)
        self._results_table.setHorizontalHeaderLabels(
            ["课程名称", "讲师", "合规等级", "不合规原因", "操作"]
        )
        self._results_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._results_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._results_table.horizontalHeader().setStretchLastSection(False)
        self._results_table.setMinimumHeight(300)
        self._results_table.horizontalHeader().sectionClicked.connect(self._on_sort)
        layout.addWidget(self._results_table)

        # Empty state
        self._empty_state = EmptyState(
            icon="📭",
            title="暂无治理结果",
            description="该治理运行没有产生结果数据",
        )
        self._empty_state.setVisible(False)
        layout.addWidget(self._empty_state)

    def _load_results(self) -> None:
        data = self._governance_service.get_results(self._run_id)
        run = data.get("run") or {}
        results = data.get("results", [])
        stats = data.get("stats", {})

        # Window title
        start_date = run.get("start_date", "")
        end_date = run.get("end_date", "")
        if start_date and end_date:
            self.setWindowTitle(f"治理结果 - {start_date} ~ {end_date}")
        else:
            self.setWindowTitle("治理结果")

        # Info bar
        started = run.get("started_at", "") or ""
        if started:
            self._info_time.setText(f"运行时间: {started[:19].replace('T', ' ')}")
        else:
            self._info_time.setText("运行时间: -")

        if start_date and end_date:
            self._info_range.setText(f"日期范围: {start_date} ~ {end_date}")
        else:
            self._info_range.setText("日期范围: -")

        status = run.get("status", "")
        status_map = {
            "completed": ("已完成", SUCCESS_500),
            "interrupted": ("已中断", WARNING_600),
            "failed": ("失败", DANGER_600),
            "running": ("运行中", BRAND_500),
        }
        status_text, status_color = status_map.get(status, (status, SLATE_500))
        self._info_status.setText(f"状态: {status_text}")
        self._info_status.setStyleSheet(f"color: {status_color}; font-size: 13px; font-weight: 600;")

        # Stats
        self._stat_total.set_value(str(stats.get("total", 0)))
        self._stat_compliant.set_value(str(stats.get("compliant", 0)))
        self._stat_major.set_value(str(stats.get("major", 0)))
        self._stat_minor.set_value(str(stats.get("minor", 0)))

        # Results
        self._all_results = results
        self._populate_table(self._all_results)

    def _populate_table(self, results: list[dict]) -> None:
        has_data = len(results) > 0
        self._results_table.setVisible(has_data)
        self._empty_state.setVisible(not has_data)

        self._results_table.setRowCount(len(results))
        for row, r in enumerate(results):
            self._results_table.setItem(
                row, 0, QTableWidgetItem(r.get("course_name", ""))
            )
            self._results_table.setItem(
                row, 1, QTableWidgetItem(r.get("creator_name", "") or r.get("creator_email", ""))
            )

            level = r.get("overall_level", "unknown")
            level_item = QTableWidgetItem(
                {
                    "ok": "合规",
                    "major": "需治理",
                    "minor": "次要问题",
                    "unknown": "未知",
                }.get(level, "需治理")
            )
            level_item.setData(Qt.ItemDataRole.UserRole, level)
            self._results_table.setItem(row, 2, level_item)

            issues = r.get("issues", [])
            issue_text = "; ".join(issues) if issues else "-"
            issue_item = QTableWidgetItem(issue_text)
            issue_item.setToolTip(issue_text)
            self._results_table.setItem(row, 3, issue_item)

            action_widget = QWidget()
            action_widget.setStyleSheet("background-color: transparent;")
            action_layout = QHBoxLayout(action_widget)
            action_layout.setContentsMargins(0, 0, 0, 0)
            action_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            action_btn = StyledButton("查看", StyledButton.GHOST)
            action_btn.setFixedSize(56, 28)
            action_btn.clicked.connect(
                lambda checked, result=r: self._on_view_detail(result)
            )
            action_layout.addWidget(action_btn)
            self._results_table.setCellWidget(row, 4, action_widget)

            self._results_table.setRowHeight(row, 48)

        # Set fixed column widths
        self._results_table.setColumnWidth(0, 280)   # 课程名称 ~20 Chinese chars
        self._results_table.setColumnWidth(1, 150)   # 讲师名字
        self._results_table.setColumnWidth(2, 80)    # 合规等级
        self._results_table.setColumnWidth(3, 400)   # 不合规原因
        self._results_table.setColumnWidth(4, 80)    # 操作

    def _on_view_detail(self, result: dict) -> None:
        """Show course governance detail dialog with aligned layout and clickable links."""
        dialog = QDialog(self)
        dialog.setWindowTitle(result.get("course_name", "课程详情"))
        dialog.setMinimumSize(640, 780)
        dialog.resize(720, 820)

        # Center on screen
        from PyQt6.QtWidgets import QApplication
        screen = QApplication.primaryScreen().availableGeometry()
        dialog_geo = dialog.frameGeometry()
        dialog_geo.moveCenter(screen.center())
        dialog.move(dialog_geo.topLeft())

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # Info section with aligned labels
        info_label = QLabel("课程信息")
        info_label.setStyleSheet(f"color: {SLATE_800}; font-size: 16px; font-weight: 700;")
        layout.addWidget(info_label)

        info_grid = QGridLayout()
        info_grid.setSpacing(10)
        info_grid.setColumnMinimumWidth(0, 80)
        info_grid.setColumnStretch(1, 1)

        fields = [
            ("课程ID", result.get("course_id", "-")),
            ("课程名称", result.get("course_name", "-")),
            ("讲师", result.get("creator_name", "") or result.get("creator_email", "-")),
            ("讲师邮箱", result.get("creator_email", "-")),
        ]
        for i, (label, value) in enumerate(fields):
            lbl = QLabel(f"{label}:")
            lbl.setStyleSheet(f"color: {SLATE_500}; font-size: 13px;")
            val = QLabel(str(value))
            val.setStyleSheet(f"color: {SLATE_800}; font-size: 13px;")
            val.setWordWrap(True)
            info_grid.addWidget(lbl, i, 0, alignment=Qt.AlignmentFlag.AlignTop)
            info_grid.addWidget(val, i, 1, alignment=Qt.AlignmentFlag.AlignTop)

        # UMU link - clickable hyperlink
        umu_lbl = QLabel("UMU链接:")
        umu_lbl.setStyleSheet(f"color: {SLATE_500}; font-size: 13px;")
        umu_link = result.get("umu_link", "")
        umu_val = QLabel()
        if umu_link and umu_link != "-":
            umu_val.setText(f'<a href="{umu_link}" style="color: {BRAND_500};">{umu_link}</a>')
            umu_val.setOpenExternalLinks(True)
            umu_val.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        else:
            umu_val.setText("-")
            umu_val.setStyleSheet(f"color: {SLATE_800}; font-size: 13px;")
        umu_val.setWordWrap(True)
        info_grid.addWidget(umu_lbl, len(fields), 0, alignment=Qt.AlignmentFlag.AlignTop)
        info_grid.addWidget(umu_val, len(fields), 1, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addLayout(info_grid)

        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {SLATE_200};")
        layout.addWidget(line)

        # Rule results section
        rule_label = QLabel("规则检查结果")
        rule_label.setStyleSheet(f"color: {SLATE_800}; font-size: 16px; font-weight: 700;")
        layout.addWidget(rule_label)

        rule_results = result.get("rule_results", [])
        if rule_results:
            rule_table = QTableWidget()
            rule_table.setColumnCount(4)
            rule_table.setHorizontalHeaderLabels(["规则", "名称", "状态", "详情"])
            rule_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
            rule_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
            rule_table.horizontalHeader().setStretchLastSection(True)
            rule_table.verticalHeader().setVisible(False)
            rule_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

            rule_table.setRowCount(len(rule_results))
            for row, rr in enumerate(rule_results):
                rule_table.setItem(row, 0, QTableWidgetItem(str(rr.get("rule_id", ""))))
                rule_table.setItem(row, 1, QTableWidgetItem(rr.get("rule_name", "")))
                if rr.get("compliant"):
                    status_item = QTableWidgetItem("✅ 合规")
                    status_item.setForeground(Qt.GlobalColor.darkGreen)
                else:
                    status_item = QTableWidgetItem("❌ 不合规")
                    status_item.setForeground(Qt.GlobalColor.red)
                rule_table.setItem(row, 2, status_item)
                detail_text = rr.get("issue", "-")
                detail_item = QTableWidgetItem(detail_text)
                detail_item.setToolTip(detail_text)
                rule_table.setItem(row, 3, detail_item)
                rule_table.setRowHeight(row, 32)

            rule_table.setColumnWidth(0, 50)
            rule_table.setColumnWidth(1, 130)
            rule_table.setColumnWidth(2, 100)

            # Force full height: header + all rows, no scrollbar
            header_height = rule_table.horizontalHeader().height()
            table_height = header_height + len(rule_results) * 32
            rule_table.setFixedHeight(table_height)

            layout.addWidget(rule_table)
        else:
            no_rule = QLabel("暂无规则检查结果")
            no_rule.setStyleSheet(f"color: {SLATE_500}; font-size: 13px;")
            layout.addWidget(no_rule)

        layout.addStretch()

        # OK button
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        ok_btn = StyledButton("确定", StyledButton.PRIMARY)
        ok_btn.setFixedWidth(80)
        ok_btn.clicked.connect(dialog.accept)
        btn_layout.addWidget(ok_btn)
        layout.addLayout(btn_layout)

        dialog.exec()

    def _filter_results(self) -> None:
        level_filter = self._level_filter.currentText()
        rule_filter = self._rule_filter.currentIndex()

        filtered = []
        for r in self._all_results:
            level = r.get("overall_level", "")
            if level_filter == "合规" and level != "ok":
                continue
            if level_filter == "需治理" and level not in ("major", "minor", "unknown"):
                continue
            if level_filter == "次要问题" and level != "minor":
                continue
            if level_filter == "未知" and level != "unknown":
                continue

            if rule_filter > 0:
                rule_results = r.get("rule_results", [])
                if rule_filter - 1 < len(rule_results):
                    if rule_results[rule_filter - 1].get("compliant"):
                        continue

            filtered.append(r)

        self._populate_table(filtered)

    def _on_export(self) -> None:
        import pandas as pd
        from lms_client.timeutil import now_beijing

        data = self._governance_service.get_results(self._run_id)
        results = data.get("results", [])
        if not results:
            QMessageBox.information(self, "导出", "没有可导出的结果")
            return

        rows = []
        for r in results:
            rows.append({
                "课程ID": r.get("course_id", ""),
                "课程名称": r.get("course_name", ""),
                "创建者": r.get("creator_name", ""),
                "创建者邮箱": r.get("creator_email", ""),
                "UMU链接": r.get("umu_link", ""),
                "合规状态": "合规" if r.get("overall_compliant") else "不合规",
                "不合规原因": "; ".join(r.get("issues", [])),
            })

        path, _ = QFileDialog.getSaveFileName(
            self,
            "导出治理结果",
            f"governance_{self._run_id[:8]}_{now_beijing().strftime('%Y%m%d_%H%M%S')}.xlsx",
            "Excel (*.xlsx)",
        )
        if path:
            df = pd.DataFrame(rows)
            df.to_excel(path, sheet_name="治理结果", index=False)
            QMessageBox.information(self, "导出成功", f"结果已保存到:\n{path}")

    def _on_sort(self, section: int) -> None:
        if not hasattr(self, "_sort_column"):
            self._sort_column = -1
            self._sort_order = Qt.SortOrder.AscendingOrder

        if self._sort_column == section:
            self._sort_order = (
                Qt.SortOrder.DescendingOrder
                if self._sort_order == Qt.SortOrder.AscendingOrder
                else Qt.SortOrder.AscendingOrder
            )
        else:
            self._sort_column = section
            self._sort_order = Qt.SortOrder.AscendingOrder

        self._results_table.sortItems(section, self._sort_order)
