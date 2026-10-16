"""Qt interface for the Google Scholar / ResearchGate publication counter."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (
    QCheckBox, QFileDialog, QFormLayout, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QMessageBox, QProgressBar, QPushButton, QSpinBox,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from tools.publication_counter import SourceResult, classify_url, run, write_csv


class PublicationWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, args: argparse.Namespace, parent: QWidget) -> None:
        super().__init__(parent)
        self.args = args

    def run(self) -> None:
        try:
            self.succeeded.emit(asyncio.run(run(self.args)))
        except Exception as exc:
            self.failed.emit(str(exc))


class PublicationCounterPanel(QWidget):
    def __init__(self, window: QWidget) -> None:
        super().__init__(window)
        self.window = window
        self.results: list[SourceResult] = []
        self.result_range: tuple[int, int] | None = None
        self.pending_range: tuple[int, int] | None = None
        self.worker: PublicationWorker | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 20)
        layout.setSpacing(10)

        self.title = QLabel(); self.title.setObjectName("pageTitle"); layout.addWidget(self.title)
        self.subtitle = QLabel(); self.subtitle.setObjectName("muted"); self.subtitle.setWordWrap(True)
        layout.addWidget(self.subtitle)

        form_card = QFrame(); form_card.setObjectName("toolbar")
        form = QFormLayout(form_card)
        form.setContentsMargins(16, 14, 16, 14)
        self.scholar_label = QLabel(); self.scholar_input = QLineEdit()
        self.scholar_input.setPlaceholderText("https://scholar.google.com/citations?user=...")
        form.addRow(self.scholar_label, self.scholar_input)
        self.researchgate_label = QLabel(); self.researchgate_input = QLineEdit()
        self.researchgate_input.setPlaceholderText("https://www.researchgate.net/profile/...")
        form.addRow(self.researchgate_label, self.researchgate_input)

        self.years_label = QLabel()
        years = QWidget(); years_row = QHBoxLayout(years); years_row.setContentsMargins(0, 0, 0, 0)
        self.start_year = QSpinBox(); self.end_year = QSpinBox()
        for field in (self.start_year, self.end_year):
            field.setRange(1900, 2100); field.setMinimumWidth(90)
        self.start_year.setValue(datetime.now().year - 5)
        self.end_year.setValue(datetime.now().year)
        years_row.addWidget(self.start_year); self.to_label = QLabel(); years_row.addWidget(self.to_label)
        years_row.addWidget(self.end_year); years_row.addStretch()
        form.addRow(self.years_label, years)

        self.cookies_label = QLabel()
        cookies = QWidget(); cookie_row = QHBoxLayout(cookies); cookie_row.setContentsMargins(0, 0, 0, 0)
        self.cookies_input = QLineEdit(); cookie_row.addWidget(self.cookies_input, 1)
        self.cookies_button = QPushButton(); self.cookies_button.clicked.connect(self.choose_cookies)
        cookie_row.addWidget(self.cookies_button)
        form.addRow(self.cookies_label, cookies)

        options = QWidget(); option_row = QHBoxLayout(options); option_row.setContentsMargins(0, 0, 0, 0)
        self.chrome_checkbox = QCheckBox(); self.chrome_checkbox.setChecked(True)
        self.headed_checkbox = QCheckBox()
        option_row.addWidget(self.chrome_checkbox); option_row.addWidget(self.headed_checkbox)
        option_row.addStretch(); form.addRow(options)
        layout.addWidget(form_card)

        actions = QHBoxLayout()
        self.start_button = QPushButton(); self.start_button.setObjectName("primary")
        self.start_button.clicked.connect(self.start_count); actions.addWidget(self.start_button)
        self.csv_button = QPushButton(); self.csv_button.clicked.connect(self.export_csv)
        self.csv_button.setEnabled(False); actions.addWidget(self.csv_button)
        self.json_button = QPushButton(); self.json_button.clicked.connect(self.export_json)
        self.json_button.setEnabled(False); actions.addWidget(self.json_button)
        actions.addStretch()
        self.progress = QProgressBar(); self.progress.setRange(0, 0); self.progress.setMaximumWidth(130)
        self.progress.hide(); actions.addWidget(self.progress)
        layout.addLayout(actions)

        self.table = QTableWidget(0, 4)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().hide()
        layout.addWidget(self.table, 1)
        self.summary = QLabel(); self.summary.setObjectName("muted")
        self.summary.setWordWrap(True); layout.addWidget(self.summary)
        self.retranslate()

    def tr(self, key: str) -> str:
        return self.window.tr(key)

    def retranslate(self) -> None:
        t = self.tr
        self.title.setText(t("publication_title"))
        self.subtitle.setText(t("publication_subtitle"))
        self.scholar_label.setText(t("publication_scholar"))
        self.researchgate_label.setText(t("publication_rg"))
        self.years_label.setText(t("publication_years"))
        self.to_label.setText(t("publication_to"))
        self.cookies_label.setText(t("publication_cookies"))
        self.cookies_button.setText(t("publication_choose"))
        self.chrome_checkbox.setText(t("publication_chrome"))
        self.chrome_checkbox.setToolTip(t("publication_chrome_tip"))
        self.headed_checkbox.setText(t("publication_headed"))
        self.start_button.setText(t("publication_start"))
        self.csv_button.setText(t("publication_csv"))
        self.json_button.setText(t("publication_json"))
        self.table.setHorizontalHeaderLabels([t("publication_source"), t("publication_name"), t("publication_year"), t("publication_count")])
        if not self.results and not (self.worker and self.worker.isRunning()):
            self.summary.setText(t("publication_idle"))
        elif self.results:
            self.show_results(self.results)

    def choose_cookies(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, self.tr("publication_choose"), "", "JSON (*.json)")
        if path:
            self.cookies_input.setText(path)

    def start_count(self) -> None:
        urls = [field.text().strip() for field in (self.scholar_input, self.researchgate_input) if field.text().strip()]
        if not urls:
            QMessageBox.warning(self, self.tr("publication_error"), self.tr("publication_need_url"))
            return
        try:
            for url in urls:
                classify_url(url)
        except ValueError as exc:
            QMessageBox.warning(self, self.tr("publication_error"), str(exc))
            return
        start, end = self.start_year.value(), self.end_year.value()
        if start > end:
            QMessageBox.warning(self, self.tr("publication_error"), self.tr("publication_bad_years"))
            return
        cookie = self.cookies_input.text().strip()
        if cookie and not Path(cookie).is_file():
            QMessageBox.warning(self, self.tr("publication_error"), self.tr("publication_bad_cookies"))
            return
        self.results = []
        self.result_range = None
        self.pending_range = (start, end)
        self.table.setRowCount(0)
        self.csv_button.setEnabled(False); self.json_button.setEnabled(False)
        self.start_button.setEnabled(False); self.progress.show()
        self.summary.setText(self.tr("publication_running"))
        profile = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "NiuBToolbox" / "scholar_browser_profile"
        args = argparse.Namespace(
            urls=urls, start_year=start, end_year=end, csv=None, json=None,
            cookies=Path(cookie) if cookie else None, profile_dir=profile,
            cdp_url="http://127.0.0.1:9222" if self.chrome_checkbox.isChecked() else None,
            headed=self.headed_checkbox.isChecked(), delay=0.45, max_scrolls=300,
        )
        self.worker = PublicationWorker(args, self)
        self.worker.succeeded.connect(self.finish_success)
        self.worker.failed.connect(self.finish_error)
        self.worker.finished.connect(self.finish_worker)
        self.worker.start()

    def finish_worker(self) -> None:
        worker = self.worker
        self.worker = None
        if worker is not None:
            worker.deleteLater()

    def finish_success(self, results: list[SourceResult]) -> None:
        self.progress.hide(); self.start_button.setEnabled(True)
        self.results = results
        self.result_range = self.pending_range
        self.pending_range = None
        self.show_results(results)
        self.csv_button.setEnabled(bool(results)); self.json_button.setEnabled(bool(results))

    def finish_error(self, message: str) -> None:
        self.progress.hide(); self.start_button.setEnabled(True)
        self.pending_range = None
        self.summary.setText(self.tr("publication_failed"))
        QMessageBox.critical(self, self.tr("publication_error"), message)

    def show_results(self, results: list[SourceResult]) -> None:
        start, end = self.result_range or (self.start_year.value(), self.end_year.value())
        self.table.setRowCount(0)
        summaries = []
        for result in results:
            source = "Google Scholar" if result.source == "google_scholar" else "ResearchGate"
            name = result.profile_name or self.tr("publication_unknown")
            for year in range(start, end + 1):
                self.add_row(source, name, str(year), str(result.counts.get(year, 0)))
            total = result.interval_total(start, end)
            self.add_row(source, name, self.tr("publication_total").format(start=start, end=end), str(total))
            summary = f"{source}: {total}"
            if result.items_without_year:
                summary += f" ({result.items_without_year} {self.tr('publication_undated')})"
            if result.warning:
                summary += f" · {result.warning}"
            summaries.append(summary)
        self.summary.setText(" | ".join(summaries) if summaries else self.tr("publication_empty"))

    def add_row(self, source: str, name: str, year: str, count: str) -> None:
        row = self.table.rowCount(); self.table.insertRow(row)
        for column, value in enumerate((source, name, year, count)):
            self.table.setItem(row, column, QTableWidgetItem(value))

    def export_csv(self) -> None:
        if not self.result_range or not self.results:
            return
        path, _ = QFileDialog.getSaveFileName(self, self.tr("publication_csv"), "publications.csv", "CSV (*.csv)")
        if path:
            write_csv(Path(path), self.results, *self.result_range)
            self.summary.setText(self.tr("publication_saved").format(path=path))

    def export_json(self) -> None:
        if not self.result_range or not self.results:
            return
        path, _ = QFileDialog.getSaveFileName(self, self.tr("publication_json"), "publications.json", "JSON (*.json)")
        if path:
            start, end = self.result_range
            payload = {"start_year": start, "end_year": end, "results": [
                dict(asdict(item), interval_total=item.interval_total(start, end)) for item in self.results
            ]}
            Path(path).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            self.summary.setText(self.tr("publication_saved").format(path=path))
