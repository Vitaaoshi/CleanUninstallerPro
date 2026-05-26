from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget,
    QTableWidgetItem, QPushButton, QHeaderView, QAbstractItemView,
    QMessageBox, QCheckBox, QWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QColor

from core.residual_scanner import ResidualScanResult, ResidualScanner, ResidualItem


class CleanWorker(QThread):
    finished = pyqtSignal(int, int)

    def __init__(self, items: list[ResidualItem], scanner: ResidualScanner):
        super().__init__()
        self._items = items
        self._scanner = scanner

    def run(self):
        cleaned = self._scanner.clean_selected(self._items)
        self.finished.emit(cleaned, len(self._items))


class ResidualDialog(QDialog):
    def __init__(self, result: ResidualScanResult, parent=None):
        super().__init__(parent)
        self._result = result
        self._scanner = ResidualScanner()
        self.setWindowTitle(f"残留扫描结果 - {result.program_name}")
        self.resize(900, 600)
        self.setMinimumSize(700, 400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        summary = QLabel(
            f"<b>{self._result.program_name}</b> 的残留扫描结果："
            f"共发现 <span style='color:#e74c3c'>{self._result.total_items}</span> 项残留，"
            f"占用空间 <span style='color:#e74c3c'>{self._result.total_size_display}</span>"
        )
        summary.setWordWrap(True)
        summary.setStyleSheet("padding: 8px; font-size: 14px;")
        layout.addWidget(summary)

        select_layout = QHBoxLayout()
        self._select_all_btn = QPushButton("全选")
        self._select_all_btn.clicked.connect(self._select_all)
        select_layout.addWidget(self._select_all_btn)

        self._deselect_all_btn = QPushButton("取消全选")
        self._deselect_all_btn.clicked.connect(self._deselect_all)
        select_layout.addWidget(self._deselect_all_btn)

        select_layout.addStretch()

        info = QLabel("可勾选不需要清理的项目后，点击「清理选中项」")
        info.setStyleSheet("color: #7f8c8d;")
        select_layout.addWidget(info)
        layout.addLayout(select_layout)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["选择", "路径", "类型", "说明", "大小"]
        )
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        header = self._table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        all_items = self._result.registry_items + self._result.file_items
        self._table.setRowCount(len(all_items))

        type_colors = {
            "registry_key": "#8e44ad",
            "registry_value": "#9b59b6",
            "directory": "#2980b9",
            "file": "#27ae60",
        }

        for row, item in enumerate(all_items):
            cb_widget = QWidget()
            cb_layout = QHBoxLayout(cb_widget)
            cb_layout.setContentsMargins(0, 0, 0, 0)
            cb_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            checkbox = QCheckBox()
            checkbox.setChecked(item.selected)
            checkbox.stateChanged.connect(
                lambda state, i=item: setattr(i, "selected", state == Qt.CheckState.Checked.value)
            )
            cb_layout.addWidget(checkbox)
            self._table.setCellWidget(row, 0, cb_widget)

            path_item = QTableWidgetItem(item.path)
            color = QColor(type_colors.get(item.item_type, "#95a5a6"))
            path_item.setForeground(color)
            self._table.setItem(row, 1, path_item)

            type_item = QTableWidgetItem(item.item_type)
            type_item.setForeground(color)
            self._table.setItem(row, 2, type_item)

            self._table.setItem(row, 3, QTableWidgetItem(item.description))
            self._table.setItem(row, 4, QTableWidgetItem(item.size_display))
            self._table.setRowHeight(row, 28)

        layout.addWidget(self._table)

        bottom = QHBoxLayout()
        self._count_label = QLabel("")
        self._update_count()
        bottom.addWidget(self._count_label)
        bottom.addStretch()

        cancel_btn = QPushButton("关闭")
        cancel_btn.clicked.connect(self.reject)
        bottom.addWidget(cancel_btn)

        self._clean_btn = QPushButton("清理选中项")
        self._clean_btn.setStyleSheet(
            "QPushButton { background-color: #e74c3c; color: white; "
            "padding: 8px 24px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #c0392b; }"
        )
        self._clean_btn.clicked.connect(self._clean_selected)
        bottom.addWidget(self._clean_btn)

        layout.addLayout(bottom)

    def _select_all(self):
        for row in range(self._table.rowCount()):
            widget = self._table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(True)

        all_items = self._result.registry_items + self._result.file_items
        for item in all_items:
            item.selected = True
        self._update_count()

    def _deselect_all(self):
        for row in range(self._table.rowCount()):
            widget = self._table.cellWidget(row, 0)
            if widget:
                checkbox = widget.findChild(QCheckBox)
                if checkbox:
                    checkbox.setChecked(False)

        all_items = self._result.registry_items + self._result.file_items
        for item in all_items:
            item.selected = False
        self._update_count()

    def _update_count(self):
        all_items = self._result.registry_items + self._result.file_items
        selected = sum(1 for i in all_items if i.selected)
        self._count_label.setText(f"已选择 {selected} / {len(all_items)} 项")

    def _clean_selected(self):
        all_items = self._result.registry_items + self._result.file_items
        selected = [i for i in all_items if i.selected]
        if not selected:
            QMessageBox.information(self, "提示", "未选择任何需要清理的项目")
            return

        reply = QMessageBox.warning(
            self, "确认清理",
            f"将清理 {len(selected)} 项残留数据，此操作不可逆。\n\n确定继续吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self._clean_btn.setEnabled(False)
        self._clean_btn.setText("清理中...")

        self._clean_worker = CleanWorker(selected, self._scanner)
        self._clean_worker.finished.connect(self._on_clean_finished)
        self._clean_worker.start()

    def _on_clean_finished(self, cleaned: int, total: int):
        QMessageBox.information(
            self, "清理完成",
            f"成功清理 {cleaned} / {total} 项残留数据"
        )

        all_items = self._result.registry_items + self._result.file_items
        for i, item in enumerate(all_items):
            if item.selected:
                self._table.setRowHidden(i, True)

        self.accept()