from datetime import date
from zipfile import ZipFile

import pytest
from fastapi import HTTPException

from app.services.reporting import ReportingService


class ExportOnlyReportingService(ReportingService):
    def __init__(self):
        super().__init__(session=None)

    def details(self, **kwargs):
        return [
            {
                "transactionId": "txn-1",
                "memberName": "张三",
                "amount": "100.00",
            }
        ], 1


def test_export_rejects_ranges_over_180_days():
    service = ExportOnlyReportingService()

    with pytest.raises(HTTPException) as error:
        service.export_xlsx(category="transactions", date_from=date(2030, 1, 1), date_to=date(2030, 7, 1))

    assert error.value.status_code == 422


def test_export_xlsx_contains_filter_metadata_and_detail_rows():
    service = ExportOnlyReportingService()

    content = service.export_xlsx(category="transactions", date_from=date(2030, 1, 1), date_to=date(2030, 1, 31))

    with ZipFile(__import__("io").BytesIO(content)) as workbook:
        sheet = workbook.read("xl/worksheets/sheet1.xml").decode()

    assert "Report" in sheet
    assert "transactions" in sheet
    assert "2030-01-01" in sheet
    assert "transactionId" in sheet
    assert "txn-1" in sheet
    assert "张三" in sheet
