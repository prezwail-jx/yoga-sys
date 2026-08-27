from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.schemas.card_product import CreateCardProductRequest, UpdateCardProductRequest
from app.services.card_product import CardProductService


def _create_request(**changes):
    values = {
        "name": "指定课程卡",
        "cardType": "times",
        "price": "300.00",
        "totalTimes": 10,
        "validDays": 30,
        "activationMode": "immediate",
        "applicableCourseScope": "specific",
        "specificCourseIds": [],
    }
    values.update(changes)
    return CreateCardProductRequest.model_validate(values)


def _product(**changes):
    values = {
        "id": uuid4(),
        "name": "团课卡",
        "card_type": "times",
        "price": "300.00",
        "cost_price": None,
        "total_times": 10,
        "valid_days": 30,
        "activation_mode": "immediate",
        "applicable_course_scope": "group",
        "specific_course_ids": None,
        "absence_deduct_enabled": False,
        "cancel_refund_enabled": False,
        "enabled": True,
    }
    values.update(changes)
    return SimpleNamespace(**values)


def test_create_specific_card_validates_and_deduplicates_course_ids():
    card_repo = MagicMock()
    course_repo = MagicMock()
    first, second = uuid4(), uuid4()
    course_repo.existing_ids.return_value = {first, second}
    card_repo.create.side_effect = lambda product: product
    service = CardProductService(card_repo, course_repo)

    product = service.create_card_product(_create_request(specificCourseIds=[first, second, first]))

    assert product.specific_course_ids == [str(first), str(second)]
    course_repo.existing_ids.assert_called_once_with({first, second})


def test_create_specific_card_rejects_missing_course_before_write():
    card_repo = MagicMock()
    course_repo = MagicMock()
    missing = uuid4()
    course_repo.existing_ids.return_value = set()
    service = CardProductService(card_repo, course_repo)

    with pytest.raises(HTTPException) as error:
        service.create_card_product(_create_request(specificCourseIds=[missing]))

    assert error.value.status_code == 422
    assert str(missing) in error.value.detail
    card_repo.create.assert_not_called()


def test_update_rejects_missing_course_without_mutating_product():
    card_repo = MagicMock()
    course_repo = MagicMock()
    product = _product()
    missing = uuid4()
    card_repo.get_by_id.return_value = product
    course_repo.existing_ids.return_value = set()
    service = CardProductService(card_repo, course_repo)

    with pytest.raises(HTTPException) as error:
        service.update_card_product(
            product.id,
            UpdateCardProductRequest.model_validate({
                "applicableCourseScope": "specific",
                "specificCourseIds": [missing],
            }),
        )

    assert error.value.status_code == 422
    assert product.applicable_course_scope == "group"
    assert product.specific_course_ids is None
    card_repo.update.assert_not_called()


def test_update_non_specific_scope_clears_stale_course_ids():
    card_repo = MagicMock()
    course_repo = MagicMock()
    course_id = uuid4()
    product = _product(
        applicable_course_scope="specific",
        specific_course_ids=[str(course_id)],
    )
    card_repo.get_by_id.return_value = product
    card_repo.update.side_effect = lambda value: value
    service = CardProductService(card_repo, course_repo)

    updated = service.update_card_product(
        product.id,
        UpdateCardProductRequest.model_validate({"applicableCourseScope": "group"}),
    )

    assert updated.applicable_course_scope == "group"
    assert updated.specific_course_ids is None
    course_repo.existing_ids.assert_not_called()


def test_times_card_requires_total_times_and_valid_days_with_chinese_errors():
    with pytest.raises(ValueError, match="次数卡必须填写 totalTimes"):
        _create_request(totalTimes=None)

    with pytest.raises(ValueError, match="次数卡必须填写 validDays"):
        _create_request(validDays=None)


def test_update_historical_times_product_requires_missing_valid_days():
    card_repo = MagicMock()
    product = _product(valid_days=None)
    card_repo.get_by_id.return_value = product
    service = CardProductService(card_repo, MagicMock())

    with pytest.raises(ValueError, match="次数卡必须填写 validDays"):
        service.update_card_product(
            product.id,
            UpdateCardProductRequest.model_validate({"name": "历史次数卡"}),
        )

    card_repo.update.assert_not_called()
