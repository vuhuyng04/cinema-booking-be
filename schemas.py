from typing import List, Optional
from pydantic import BaseModel


class SeatSelection(BaseModel):
    seat_id: str
    price: float


class CreateBookingRequest(BaseModel):
    showtime_id: str
    user_email: Optional[str] = None
    seats: List[SeatSelection]


class CreateBookingResponse(BaseModel):
    id: str
    total_price: float
    status: str


class CreateMovieRequest(BaseModel):
    title: str
    description: Optional[str] = None
    poster_url: Optional[str] = None
    trailer_url: Optional[str] = None
    genre: List[str] = []
    duration: int
    rating: Optional[float] = None
    release_date: Optional[str] = None
    status: str = "now_showing"


class UpdateMovieRequest(CreateMovieRequest):
    pass


class CreateShowtimeRequest(BaseModel):
    movie_id: str
    hall_id: str
    start_time: str
    end_time: str
    price_standard: float = 80000
    price_vip: float = 120000
    price_couple: float = 200000
