from unittest.mock import MagicMock

import pytest
from app.core.timezone import utc_now


def test_utc_now():
    now = utc_now()
    assert now.tzinfo is not None
    utc_offset = now.utcoffset()
    assert utc_offset is not None
    assert utc_offset.total_seconds() == 0


def test_datetime_utc_type_decorator():
    from app.core.timezone import DateTimeUTC

    dt_utc = DateTimeUTC()

    # Test process_bind_param
    import datetime

    aware_dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=5)))
    bound_dt = dt_utc.process_bind_param(aware_dt, MagicMock())
    assert bound_dt is not None
    assert bound_dt.tzinfo is not None
    bound_dt_offset = bound_dt.utcoffset()
    assert bound_dt_offset is not None
    assert bound_dt_offset.total_seconds() == 0

    # Test process_result_value
    naive_dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
    result_dt = dt_utc.process_result_value(naive_dt, MagicMock())
    assert result_dt is not None
    assert result_dt.tzinfo is not None
    result_dt_offset = result_dt.utcoffset()
    assert result_dt_offset is not None
    assert result_dt_offset.total_seconds() == 0

    aware_dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))
    result_dt = dt_utc.process_result_value(aware_dt, MagicMock())
    assert result_dt is not None
    assert result_dt.tzinfo is not None
    result_dt_offset = result_dt.utcoffset()
    assert result_dt_offset is not None
    assert result_dt_offset.total_seconds() == -3 * 3600


def test_datetime_utc_type_decorator_none():
    from app.core.timezone import DateTimeUTC

    dt_utc = DateTimeUTC()

    # Test process_bind_param with None
    bound_dt = dt_utc.process_bind_param(None, MagicMock())
    assert bound_dt is None

    # Test process_result_value with None
    result_dt = dt_utc.process_result_value(None, MagicMock())
    assert result_dt is None


def test_datetime_utc_type_decorator_no_tzinfo():
    from app.core.timezone import DateTimeUTC
    import datetime

    dt_utc = DateTimeUTC()

    # Test process_bind_param with naive datetime
    naive_dt = datetime.datetime(2024, 1, 1, 12, 0, 0)
    with pytest.raises(TypeError) as context:
        _ = dt_utc.process_bind_param(naive_dt, MagicMock())
    assert str(context.value) == "tzinfo is required"


def test_datetime_utc_type_decorator_python_type():
    from app.core.timezone import DateTimeUTC
    import datetime

    dt_utc = DateTimeUTC()
    assert dt_utc.python_type is datetime.datetime
