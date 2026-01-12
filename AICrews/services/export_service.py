"""Usage data export service for CSV/Excel formats."""
from __future__ import annotations

import io
import csv
from typing import List, Dict, Any
from datetime import datetime


class ExportFormat:
    """Supported export formats."""
    CSV = "csv"
    EXCEL = "excel"


class ExportService:
    """Service for exporting usage data to various formats."""

    def generate_csv(
        self,
        data: List[Dict[str, Any]],
        include_header: bool = True
    ) -> str:
        """
        Generate CSV string from usage data.

        Args:
            data: List of usage activity records
            include_header: Whether to include CSV header row

        Returns:
            CSV formatted string
        """
        if not data:
            return "date,time,activity,model,reports,tokens\n"

        output = io.StringIO()

        fieldnames = [
            "date",
            "time",
            "activity",
            "model",
            "reports",
            "tokens"
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)

        if include_header:
            writer.writeheader()

        for row in data:
            writer.writerow({
                "date": row.get("date", ""),
                "time": row.get("time", ""),
                "activity": row.get("activity", ""),
                "model": row.get("model", ""),
                "reports": row.get("reports", 0),
                "tokens": row.get("tokens", 0)
            })

        return output.getvalue()

    def generate_filename(
        self,
        format: str = ExportFormat.CSV,
        start_date: datetime = None,
        end_date: datetime = None
    ) -> str:
        """
        Generate filename for export file.

        Args:
            format: Export format (csv/excel)
            start_date: Start date of data range
            end_date: End date of data range

        Returns:
            Filename string
        """
        ext = "csv" if format == ExportFormat.CSV else "xlsx"

        if start_date and end_date:
            date_range = f"{start_date.strftime('%Y%m%d')}-{end_date.strftime('%Y%m%d')}"
        else:
            date_range = datetime.now().strftime('%Y%m%d')

        return f"usage_export_{date_range}.{ext}"


__all__ = ["ExportService", "ExportFormat"]
