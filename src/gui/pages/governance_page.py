"""Governance page — the most complex page with tabs, step indicator, results, and history."""

from __future__ import annotations

from datetime import datetime, timedelta

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..components.empty_state import EmptyState
from ..components.governance_result_window import GovernanceResultWindow
from ..components.progress_bar import ProgressBar
from ..components.stat_card import StatCard
from ..components.step_indicator import StepIndicator
from ..components.styled_button import StyledButton
from ..styles import (
    BRAND_500,
    DANGER_50,
    DANGER_600,
    SLATE_200,
    SLATE_500,
    SLATE_800,
    SUCCESS_500,
    WARNING_50,
    WARNING_500,
    WARNING_600,
)


class PreviewWorker(QThread):
    """Background worker for loading governance preview stats."""

    preview_finished = pyqtSignal(dict)
    preview_error = pyqtSignal(str)

    def __init__(self, governance_service, start_date: str, end_date: str) -> None:
        super().__init__()
        self._governance_service = governance_service
        self._start_date = start_date
        self._end_date = end_date

    def run(self) -> None:
        try:
            data = self._governance_service.preview_governance(self._start_date, self._end_date)
            self.preview_finished.emit(data)
        except Exception as exc:
            self.preview_error.emit(str(exc))


class GovernancePage(QWidget):
    """Governance page with new governance and history tabs."""

    def __init__(
        self,
        auth_service,
        sync_service,
        governance_service,
        show_toast=None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._auth_service = auth_service
        self._sync_service = sync_service
        self._governance_service = governance_service
        self._show_toast = show_toast
        self._current_run_id: str = ""
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 32, 40, 32)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Title
        title = QLabel("培训数据治理")
        title.setStyleSheet(f"color: {SLATE_800}; font-size: 22px; font-weight: 700;")
        layout.addWidget(title)

        # Non-admin warning
        self._warning_label = QLabel("⚠️ 您不是管理员，无法执行治理操作。")
        self._warning_label.setObjectName("non-admin-warning")
        self._warning_label.setVisible(False)
        layout.addWidget(self._warning_label)

        # Tabs
        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        # New Governance Tab
        self._new_tab = self._create_new_tab()
        self._tabs.addTab(self._new_tab, "新治理")

        # History Tab
        self._history_tab = self._create_history_tab()
        self._tabs.addTab(self._history_tab, "历史记录")

        layout.addWidget(self._tabs)

    def _create_new_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(20)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Description
        desc = QLabel("对培训课程数据进行自动化合规审核，覆盖课程名称、分类、介绍、学时、评价、必修小节、课件等8项规则。")
        desc.setStyleSheet(f"color: {SLATE_500}; font-size: 14px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # Quick date chips
        chip_layout = QHBoxLayout()
        chip_layout.setSpacing(8)
        chip_names = [("last_month", "上个月"), ("month", "本月"), ("quarter", "本季度"), ("year", "本年"), ("all", "全部")]
        for key, label in chip_names:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName("chip")
            btn.clicked.connect(lambda checked, k=key: self._on_chip_clicked(k))
            chip_layout.addWidget(btn)
        chip_layout.addStretch()
        layout.addLayout(chip_layout)

        # Date range + refresh
        date_layout = QHBoxLayout()
        date_layout.setSpacing(12)

        from PyQt6.QtWidgets import QDateEdit
        self._start_date = QDateEdit()
        self._start_date.setCalendarPopup(True)
        self._start_date.setFixedWidth(140)
        self._start_date.setDate(datetime(datetime.now().year, 1, 1))
        self._start_date.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(QLabel("从:"))
        date_layout.addWidget(self._start_date)

        self._end_date = QDateEdit()
        self._end_date.setCalendarPopup(True)
        self._end_date.setFixedWidth(140)
        self._end_date.setDate(datetime.now())
        self._end_date.setDisplayFormat("yyyy-MM-dd")
        date_layout.addWidget(QLabel("至:"))
        date_layout.addWidget(self._end_date)

        self._refresh_btn = StyledButton("刷新预览", StyledButton.GHOST)
        self._refresh_btn.clicked.connect(self._load_preview)
        date_layout.addWidget(self._refresh_btn)

        date_layout.addStretch()
        layout.addLayout(date_layout)

        # Preview stats
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        self._preview_course_count = StatCard("待审核课程", "-")
        self._preview_user_count = StatCard("已同步用户", "-")
        self._preview_last_sync = StatCard("数据更新时间", "-")
        stats_layout.addWidget(self._preview_course_count)
        stats_layout.addWidget(self._preview_user_count)
        stats_layout.addWidget(self._preview_last_sync)
        layout.addLayout(stats_layout)

        # Step indicator
        self._step_indicator = StepIndicator(["配置范围", "数据同步", "执行审核", "查看结果"])
        layout.addWidget(self._step_indicator)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)
        self._full_governance_btn = StyledButton("开始完整治理", StyledButton.PRIMARY)
        self._full_governance_btn.setMinimumHeight(44)
        self._quick_governance_btn = StyledButton("快速治理（不重新同步）", StyledButton.SECONDARY)
        self._quick_governance_btn.setMinimumHeight(44)
        self._cancel_governance_btn = StyledButton("取消治理", StyledButton.GHOST)
        self._cancel_governance_btn.setMinimumHeight(44)
        self._cancel_governance_btn.setVisible(False)
        btn_layout.addWidget(self._full_governance_btn)
        btn_layout.addWidget(self._quick_governance_btn)
        btn_layout.addWidget(self._cancel_governance_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Progress area
        self._progress = ProgressBar()
        layout.addWidget(self._progress)

        # Live stats
        live_layout = QHBoxLayout()
        live_layout.setSpacing(20)
        self._live_total = QLabel("课程总量: -")
        self._live_progress = QLabel("已审核: -")
        self._live_compliant = QLabel("合规: -")
        self._live_major = QLabel("需治理: -")
        for lbl in (self._live_total, self._live_progress, self._live_compliant, self._live_major):
            lbl.setStyleSheet(f"color: {SLATE_500}; font-size: 13px;")
            live_layout.addWidget(lbl)
        live_layout.addStretch()
        layout.addLayout(live_layout)

        layout.addStretch()
        return tab

    def _create_history_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 16, 0, 0)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Filter row
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(12)

        self._history_search = QLineEdit()
        self._history_search.setPlaceholderText("搜索...")
        self._history_search.setMinimumWidth(200)
        filter_layout.addWidget(self._history_search)

        self._history_status = QComboBox()
        self._history_status.addItems(["全部状态", "已完成", "已中断", "失败"])
        filter_layout.addWidget(self._history_status)

        self._history_sort = QComboBox()
        self._history_sort.addItems(["最新优先", "最早优先"])
        filter_layout.addWidget(self._history_sort)

        self._history_clear_btn = StyledButton("清空历史", StyledButton.GHOST)
        self._history_clear_btn.clicked.connect(self._on_clear_history)
        filter_layout.addWidget(self._history_clear_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # History table
        self._history_table = QTableWidget()
        self._history_table.setColumnCount(7)
        self._history_table.setHorizontalHeaderLabels(["时间", "状态", "日期范围", "课程数", "合规率", "操作", ""])
        self._history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._history_table.horizontalHeader().setStretchLastSection(True)
        self._history_table.setMinimumHeight(400)
        # Set minimum width for action column (index 5) to fit buttons
        self._history_table.horizontalHeader().setMinimumSectionSize(60)
        layout.addWidget(self._history_table)

        # Empty state for history
        self._history_empty = EmptyState(
            icon="📭",
            title="暂无治理历史",
            description="完成一次治理后，记录将显示在这里",
        )
        self._history_empty.setVisible(False)
        layout.addWidget(self._history_empty)

        # Pagination
        page_layout = QHBoxLayout()
        self._prev_btn = StyledButton("上一页", StyledButton.GHOST)
        self._prev_btn.clicked.connect(self._on_prev_page)
        self._page_label = QLabel("第 1 页")
        self._page_label.setStyleSheet(f"color: {SLATE_500}; font-size: 13px;")
        self._next_btn = StyledButton("下一页", StyledButton.GHOST)
        self._next_btn.clicked.connect(self._on_next_page)
        page_layout.addStretch()
        page_layout.addWidget(self._prev_btn)
        page_layout.addWidget(self._page_label)
        page_layout.addWidget(self._next_btn)
        page_layout.addStretch()
        layout.addLayout(page_layout)

        return tab

    def _connect_signals(self) -> None:
        self._full_governance_btn.clicked.connect(self._on_full_governance)
        self._quick_governance_btn.clicked.connect(self._on_quick_governance)
        self._cancel_governance_btn.clicked.connect(self._on_cancel_governance)
        self._governance_service.progress_updated.connect(self._on_governance_progress)
        self._governance_service.governance_finished.connect(self._on_governance_finished)
        self._sync_service.sync_finished.connect(self._on_sync_finished)
        self._history_search.textChanged.connect(self._filter_history)
        self._history_status.currentIndexChanged.connect(self._filter_history)
        self._history_sort.currentIndexChanged.connect(self._filter_history)
        self._history_table.horizontalHeader().sectionClicked.connect(self._on_history_sort)

    def refresh(self) -> None:
        is_admin = self._auth_service.is_admin()
        self._full_governance_btn.setEnabled(is_admin)
        self._quick_governance_btn.setEnabled(is_admin)
        self._warning_label.setVisible(not is_admin)
        self._load_preview()
        self._load_history()
        self._check_active_governance()

    def _check_active_governance(self) -> None:
        """Check if there's an active governance run on page load."""
        if self._governance_service.is_running():
            self._step_indicator.set_current(2)
            self._progress.setVisible(True)

    def _on_chip_clicked(self, key: str) -> None:
        today = datetime.now()
        if key == "last_month":
            first = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
            last = today.replace(day=1) - timedelta(days=1)
            self._start_date.setDate(first)
            self._end_date.setDate(last)
        elif key == "month":
            self._start_date.setDate(today.replace(day=1))
            self._end_date.setDate(today)
        elif key == "quarter":
            quarter = (today.month - 1) // 3
            first_month = quarter * 3 + 1
            self._start_date.setDate(today.replace(month=first_month, day=1))
            self._end_date.setDate(today)
        elif key == "year":
            self._start_date.setDate(today.replace(month=1, day=1))
            self._end_date.setDate(today)
        elif key == "all":
            self._start_date.setDate(datetime(2020, 1, 1))
            self._end_date.setDate(today)
        self._load_preview()

    def _load_preview(self) -> None:
        start = self._start_date.date().toString("yyyy-MM-dd")
        end = self._end_date.date().toString("yyyy-MM-dd")
        self._refresh_btn.setEnabled(False)
        self._preview_course_count.set_value("-")
        self._preview_user_count.set_value("-")
        self._preview_last_sync.set_value("加载中...")

        self._preview_worker = PreviewWorker(self._governance_service, start, end)
        self._preview_worker.preview_finished.connect(self._on_preview_finished)
        self._preview_worker.preview_error.connect(self._on_preview_error)
        self._preview_worker.finished.connect(lambda: setattr(self, '_preview_worker', None))
        self._preview_worker.start()

    def _on_preview_finished(self, data: dict) -> None:
        self._refresh_btn.setEnabled(True)
        self._preview_course_count.set_value(str(data.get("course_count", 0)))
        self._preview_user_count.set_value(str(data.get("user_count", 0)))
        last_sync = data.get("last_sync")
        if last_sync:
            self._preview_last_sync.set_value(last_sync[:10])
        else:
            self._preview_last_sync.set_value("未同步")

    def _on_preview_error(self, error: str) -> None:
        self._refresh_btn.setEnabled(True)
        self._preview_last_sync.set_value("加载失败")

    def _set_governance_running(self, running: bool) -> None:
        self._full_governance_btn.setVisible(not running)
        self._quick_governance_btn.setVisible(not running)
        self._cancel_governance_btn.setVisible(running)

    def _on_full_governance(self) -> None:
        serialized = self._auth_service.get_serialized_session()
        if not serialized:
            return
        self._step_indicator.set_current(0)
        self._start_full_governance(serialized)

    def _start_full_governance(self, serialized: str) -> None:
        start = self._start_date.date().toString("yyyy-MM-dd")
        end = self._end_date.date().toString("yyyy-MM-dd")
        self._step_indicator.set_current(1)
        self._progress.reset()
        self._progress.set_value(0, "正在同步用户数据...")
        self._sync_service.start_sync_users(serialized)
        self._pending_full_governance = True
        self._pending_dates = (start, end)
        self._set_governance_running(True)

    def _on_sync_finished(self, sync_type: str, success: bool, details: str) -> None:
        if not getattr(self, '_pending_full_governance', False):
            return
        if not success and "取消" in details:
            self._pending_full_governance = False
            self._set_governance_running(False)
            return
        serialized = self._auth_service.get_serialized_session()
        if not serialized:
            return
        start, end = self._pending_dates
        if sync_type == "users":
            self._progress.set_value(0, "正在同步课程数据...")
            self._sync_service.start_sync_courses(serialized, start, end)
        elif sync_type == "courses":
            self._step_indicator.set_current(2)
            self._progress.set_value(0, "准备开始审核...")
            self._current_run_id = self._governance_service.start_governance(serialized, start, end)
            self._pending_full_governance = False

    def _on_quick_governance(self) -> None:
        serialized = self._auth_service.get_serialized_session()
        if not serialized:
            return
        start = self._start_date.date().toString("yyyy-MM-dd")
        end = self._end_date.date().toString("yyyy-MM-dd")
        self._step_indicator.set_current(2)
        self._progress.reset()
        self._current_run_id = self._governance_service.start_governance(serialized, start, end)
        self._set_governance_running(True)

    def _on_cancel_governance(self) -> None:
        self._governance_service.cancel()
        self._sync_service.cancel("users")
        self._sync_service.cancel("courses")
        self._set_governance_running(False)
        self._pending_full_governance = False
        self._progress.set_value(0, "已取消")
        self._step_indicator.set_current(0)

    def _on_governance_progress(self, progress: int, total: int, compliant: int,
                                 non_compliant: int, major: int, current_course: str,
                                 message: str) -> None:
        percent = int(progress / max(total, 1) * 100)
        self._progress.set_value(percent, message)
        self._live_total.setText(f"课程总量: {total}")
        self._live_progress.setText(f"已审核: {progress}")
        self._live_compliant.setText(f"合规: {compliant}")
        self._live_major.setText(f"需治理: {major}")

    def _on_governance_finished(self, success: bool, run_id: str, message: str) -> None:
        self._set_governance_running(False)
        self._progress.set_value(100 if success else 0, message)
        self._step_indicator.set_current(3 if success else 2)
        if success:
            self._current_run_id = run_id
            window = GovernanceResultWindow(self._governance_service, run_id, self)
            window.exec()
        self._load_history()

    def _load_history(self) -> None:
        self._history_data = self._governance_service.get_runs()
        self._history_page = 0
        self._history_page_size = 10
        self._filter_history()

    def _filter_history(self) -> None:
        if not hasattr(self, '_history_data'):
            return

        data = self._history_data[:]
        search = self._history_search.text().strip().lower()
        status_filter = self._history_status.currentText()
        sort = self._history_sort.currentText()

        if search:
            data = [r for r in data if search in (r.get("run_id", "") + str(r.get("start_date", ""))).lower()]

        if status_filter != "全部状态":
            status_map = {"已完成": "completed", "已中断": "interrupted", "失败": "failed"}
            target = status_map.get(status_filter)
            if target:
                data = [r for r in data if r.get("status") == target]

        if sort == "最早优先":
            data = list(reversed(data))

        self._filtered_history = data
        self._history_page = 0
        self._render_history_page()

    def _on_history_sort(self, section: int) -> None:
        if not hasattr(self, '_history_data'):
            return

        if not hasattr(self, '_history_sort_column'):
            self._history_sort_column = -1
            self._history_sort_order = Qt.SortOrder.AscendingOrder

        if self._history_sort_column == section:
            self._history_sort_order = Qt.SortOrder.DescendingOrder if self._history_sort_order == Qt.SortOrder.AscendingOrder else Qt.SortOrder.AscendingOrder
        else:
            self._history_sort_column = section
            self._history_sort_order = Qt.SortOrder.AscendingOrder

        # Sort the underlying data
        key_funcs = {
            0: lambda r: r.get("started_at", ""),
            1: lambda r: r.get("status", ""),
            2: lambda r: r.get("start_date", ""),
            3: lambda r: r.get("total_courses", 0),
            4: lambda r: r.get("compliant_rate") or -1,
        }

        if section in key_funcs:
            self._history_data.sort(
                key=key_funcs[section],
                reverse=(self._history_sort_order == Qt.SortOrder.DescendingOrder)
            )
            self._filter_history()

    def _render_history_page(self) -> None:
        data = getattr(self, '_filtered_history', [])
        start = self._history_page * self._history_page_size
        end = start + self._history_page_size
        page_data = data[start:end]

        self._history_empty.setVisible(len(data) == 0)
        self._history_table.setVisible(len(data) > 0)
        self._prev_btn.setVisible(len(data) > 0)
        self._next_btn.setVisible(len(data) > 0)
        self._page_label.setVisible(len(data) > 0)

        self._history_table.setRowCount(len(page_data))
        max_action_width = 80  # at least one button
        for row, r in enumerate(page_data):
            started = r.get("started_at", "") or ""
            self._history_table.setItem(row, 0, QTableWidgetItem(started[:19].replace("T", " ")))

            status = r.get("status", "")
            status_map = {"completed": "已完成", "interrupted": "已中断", "failed": "失败", "running": "运行中"}
            status_item = QTableWidgetItem(status_map.get(status, status))
            self._history_table.setItem(row, 1, status_item)

            date_range = f"{r.get('start_date', '')} ~ {r.get('end_date', '')}"
            self._history_table.setItem(row, 2, QTableWidgetItem(date_range))
            self._history_table.setItem(row, 3, QTableWidgetItem(str(r.get("total_courses", 0))))
            rate = r.get("compliant_rate")
            self._history_table.setItem(row, 4, QTableWidgetItem(f"{rate}%" if rate is not None else "-"))

            actions = QWidget()
            actions.setStyleSheet("background-color: transparent;")
            act_layout = QHBoxLayout(actions)
            act_layout.setContentsMargins(2, 2, 2, 2)
            act_layout.setSpacing(6)
            act_layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)

            view_btn = StyledButton("查看", StyledButton.GHOST)
            view_btn.setFixedSize(56, 28)
            view_btn.clicked.connect(lambda checked, rid=r.get("run_id"): self._view_run(rid))
            act_layout.addWidget(view_btn)

            action_width = 56 + 6 + 56  # view + spacing + delete

            if status in ("interrupted", "failed"):
                resume_btn = StyledButton("继续", StyledButton.GHOST)
                resume_btn.setFixedSize(56, 28)
                resume_btn.clicked.connect(lambda checked, rid=r.get("run_id"): self._resume_run(rid))
                act_layout.addWidget(resume_btn)
                action_width += 6 + 56  # + spacing + resume

            del_btn = StyledButton("删除", StyledButton.GHOST)
            del_btn.setFixedSize(56, 28)
            del_btn.clicked.connect(lambda checked, rid=r.get("run_id"): self._delete_run(rid))
            act_layout.addWidget(del_btn)
            act_layout.addStretch()

            max_action_width = max(max_action_width, action_width + 8)  # + margin padding

            self._history_table.setCellWidget(row, 5, actions)
            self._history_table.setRowHeight(row, 48)

        # Set fixed column widths so action column fits all buttons
        self._history_table.setColumnWidth(0, 170)   # 时间
        self._history_table.setColumnWidth(1, 80)    # 状态
        self._history_table.setColumnWidth(2, 220)   # 日期范围
        self._history_table.setColumnWidth(3, 70)    # 课程数
        self._history_table.setColumnWidth(4, 70)    # 合规率
        self._history_table.setColumnWidth(5, max_action_width)  # 操作

        total_pages = max((len(data) + self._history_page_size - 1) // self._history_page_size, 1)
        current_page = self._history_page + 1
        self._page_label.setText(f"第 {current_page} / {total_pages} 页")
        self._prev_btn.setEnabled(self._history_page > 0)
        self._next_btn.setEnabled(end < len(data))

    def _on_prev_page(self) -> None:
        if self._history_page > 0:
            self._history_page -= 1
            self._render_history_page()

    def _on_next_page(self) -> None:
        data = getattr(self, '_filtered_history', [])
        max_page = (len(data) + self._history_page_size - 1) // self._history_page_size - 1
        if self._history_page < max_page:
            self._history_page += 1
            self._render_history_page()

    def _view_run(self, run_id: str) -> None:
        self._current_run_id = run_id
        window = GovernanceResultWindow(self._governance_service, run_id, self)
        window.exec()

    def _resume_run(self, run_id: str) -> None:
        serialized = self._auth_service.get_serialized_session()
        if not serialized:
            return
        if self._governance_service.resume_governance(run_id, serialized):
            self._current_run_id = run_id
            self._step_indicator.set_current(2)
            self._progress.reset()
            self._tabs.setCurrentIndex(0)

    def _delete_run(self, run_id: str) -> None:
        msg = QMessageBox(self)
        msg.setWindowTitle("确认删除")
        msg.setText("确定要删除这条治理记录吗？此操作不可撤销。")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        reply = msg.exec()
        if reply == QMessageBox.StandardButton.Yes:
            self._governance_service.delete_run(run_id)
            self._load_history()

    def _on_clear_history(self) -> None:
        reply = QMessageBox.question(
            self, "确认清空",
            "确定要清空所有治理历史记录吗？此操作不可撤销。",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._governance_service.clear_all_runs()
            self._load_history()
