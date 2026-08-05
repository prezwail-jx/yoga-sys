from unittest.mock import MagicMock

from app.api.deps import get_private_training_service, get_reporting_service
from app.services.private_training import PrivateTrainingService
from app.services.reporting import ReportingService


def test_private_training_dependency_returns_service_instance():
    service = get_private_training_service(MagicMock())

    assert isinstance(service, PrivateTrainingService)


def test_reporting_dependency_returns_reporting_service_instance():
    service = get_reporting_service(MagicMock())

    assert isinstance(service, ReportingService)
