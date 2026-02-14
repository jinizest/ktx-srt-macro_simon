"""Integration tests for KTXService"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
from src.infrastructure.adapters.ktx_service import KTXService
from src.domain.models.entities import ReservationRequest, Passenger, CreditCard, ReservationResult
from src.domain.models.enums import PassengerType, TrainType, SeatPreference


@pytest.fixture
def ktx_service():
    """Create KTXService instance for testing"""
    return KTXService()


@pytest.fixture
def sample_reservation_request():
    """Create a sample reservation request"""
    return ReservationRequest(
        departure_station="서울",
        arrival_station="부산",
        departure_date=date(2025, 1, 15),
        departure_time="100000",
        passengers=[
            Passenger(passenger_type=PassengerType.ADULT, count=2),
            Passenger(passenger_type=PassengerType.CHILD, count=1)
        ],
        train_type=TrainType.KTX
    )


class TestKTXServiceLogin:
    """Tests for KTXService login/logout"""

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_successful_login(self, mock_korail_class, ktx_service):
        """Test successful login"""
        # Arrange
        mock_korail = Mock()
        mock_korail.login.return_value = True
        ktx_service._korail = mock_korail

        # Act
        result = ktx_service.login("test_user", "test_password")

        # Assert
        assert result is True
        assert ktx_service.is_logged_in() is True
        mock_korail.login.assert_called_once_with("test_user", "test_password")

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_failed_login(self, mock_korail_class, ktx_service):
        """Test failed login"""
        # Arrange
        mock_korail = Mock()
        mock_korail.login.return_value = False
        ktx_service._korail = mock_korail

        # Act
        result = ktx_service.login("test_user", "wrong_password")

        # Assert
        assert result is False
        assert ktx_service.is_logged_in() is False

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_login_exception(self, mock_korail_class, ktx_service):
        """Test login with exception"""
        # Arrange
        mock_korail = Mock()
        mock_korail.login.side_effect = Exception("Network error")
        ktx_service._korail = mock_korail

        # Act
        result = ktx_service.login("test_user", "test_password")

        # Assert
        assert result is False
        assert ktx_service.is_logged_in() is False

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_logout(self, mock_korail_class, ktx_service):
        """Test logout"""
        # Arrange
        mock_korail = Mock()
        ktx_service._korail = mock_korail
        ktx_service._logged_in = True

        # Act
        result = ktx_service.logout()

        # Assert
        assert result is True
        assert ktx_service.is_logged_in() is False
        mock_korail.logout.assert_called_once()


class TestKTXServiceSearchTrains:
    """Tests for KTXService search_trains"""

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_search_trains_not_logged_in(self, mock_korail_class, ktx_service, sample_reservation_request):
        """Test searching trains when not logged in"""
        # Arrange
        ktx_service._logged_in = False

        # Act
        result = ktx_service.search_trains(sample_reservation_request)

        # Assert
        assert result == []

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_search_trains_success(self, mock_korail_class, ktx_service, sample_reservation_request):
        """Test successful train search"""
        # Arrange
        ktx_service._logged_in = True
        mock_korail = Mock()

        mock_train = Mock()
        mock_train.train_no = "001"
        mock_train.dep_date = "20250115"
        mock_train.dep_time = "100000"
        mock_train.arr_date = "20250115"
        mock_train.arr_time = "123000"
        mock_train.train_type = "KTX"
        mock_train.adultcharge = "59800"
        mock_train.seat_count = 10

        mock_korail.search_train.return_value = [mock_train]
        ktx_service._korail = mock_korail

        # Act
        result = ktx_service.search_trains(sample_reservation_request)

        # Assert
        assert len(result) == 1
        assert result[0].train_number == "001"
        assert result[0].train_type == TrainType.KTX

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_search_trains_exception(self, mock_korail_class, ktx_service, sample_reservation_request):
        """Test train search with exception"""
        # Arrange
        ktx_service._logged_in = True
        mock_korail = Mock()
        mock_korail.search_train.side_effect = Exception("Search error")
        ktx_service._korail = mock_korail

        # Act
        result = ktx_service.search_trains(sample_reservation_request)

        # Assert
        assert result == []


    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_search_trains_uses_requested_date_and_time(self, mock_korail_class, ktx_service, sample_reservation_request):
        """요청한 날짜/시간으로 검색 API를 호출해야 한다"""
        ktx_service._logged_in = True
        mock_korail = Mock()
        mock_korail.search_train.return_value = []
        ktx_service._korail = mock_korail

        ktx_service.search_trains(sample_reservation_request)

        _, kwargs = mock_korail.search_train.call_args
        assert kwargs["date"] == "20250115"
        assert kwargs["time"] == "100000"


class TestKTXSeatPreferenceMapping:
    """KTX 좌석 옵션 매핑 테스트"""

    def test_to_korail_reserve_option_special_first(self):
        option = KTXService._to_korail_reserve_option(SeatPreference.SPECIAL_FIRST)
        assert option == "SPECIAL_FIRST"

    def test_to_korail_reserve_option_default_when_invalid(self):
        option = KTXService._to_korail_reserve_option(None)
        assert option == "GENERAL_FIRST"


class TestKTXServiceReserveTrainOption:
    """reserve 시 좌석 옵션 전달 테스트"""

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_reserve_train_passes_selected_seat_preference(self, mock_korail_class, ktx_service, sample_reservation_request):
        ktx_service._logged_in = True
        sample_reservation_request.seat_preference = SeatPreference.SPECIAL_FIRST

        mock_korail = Mock()

        mock_train = Mock()
        mock_train.train_no = "001"
        mock_train.has_seat.return_value = True

        mock_schedule = Mock()
        mock_schedule.train_number = "001"

        mock_reservation = Mock()
        mock_reservation.rsv_id = "R123456"

        mock_korail.search_train.return_value = [mock_train]
        mock_korail.reserve.return_value = mock_reservation
        ktx_service._korail = mock_korail

        result = ktx_service.reserve_train(mock_schedule, sample_reservation_request)

        assert result.success is True
        _, kwargs = mock_korail.reserve.call_args
        assert kwargs["option"] == "SPECIAL_FIRST"


class TestKTXServiceReserveTrain:
    """Tests for KTXService reserve_train"""

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_reserve_train_not_logged_in(self, mock_korail_class, ktx_service, sample_reservation_request):
        """Test reserving train when not logged in"""
        # Arrange
        ktx_service._logged_in = False
        mock_schedule = Mock()

        # Act
        result = ktx_service.reserve_train(mock_schedule, sample_reservation_request)

        # Assert
        assert result.success is False
        assert result.message == "Not logged in"

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_reserve_train_not_found(self, mock_korail_class, ktx_service, sample_reservation_request):
        """Test reserving train when train not found"""
        # Arrange
        ktx_service._logged_in = True
        mock_korail = Mock()
        mock_korail.search_train.return_value = []
        ktx_service._korail = mock_korail

        mock_schedule = Mock()
        mock_schedule.train_number = "999"

        # Act
        result = ktx_service.reserve_train(mock_schedule, sample_reservation_request)

        # Assert
        assert result.success is False
        assert result.message == "Train not found"


class TestKTXServicePayment:
    """Tests for KTXService payment_reservation"""

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_payment_not_logged_in(self, mock_korail_class, ktx_service):
        """Test payment when not logged in"""
        # Arrange
        ktx_service._logged_in = False
        mock_reservation = ReservationResult(
            success=True,
            reservation_number="R123456",
            message="Success"
        )
        mock_card = CreditCard(
            number="1234567812345678",
            password="12",
            validation_number="990101",
            expire="2512",
            is_corporate=False
        )

        # Act
        result = ktx_service.payment_reservation(mock_reservation, mock_card)

        # Assert
        assert result.success is False
        assert result.message == "Not logged in"

    @patch('src.infrastructure.adapters.ktx_service.Korail')
    def test_payment_reservation_not_found(self, mock_korail_class, ktx_service):
        """Test payment when reservation not found"""
        # Arrange
        ktx_service._logged_in = True
        mock_korail = Mock()
        mock_korail.reservations.return_value = None
        ktx_service._korail = mock_korail

        mock_reservation = ReservationResult(
            success=True,
            reservation_number="R123456",
            message="Success"
        )
        mock_card = CreditCard(
            number="1234567812345678",
            password="12",
            validation_number="990101",
            expire="2512",
            is_corporate=False
        )

        # Act
        result = ktx_service.payment_reservation(mock_reservation, mock_card)

        # Assert
        assert result.success is False
        assert result.message == "Reservation not found"
