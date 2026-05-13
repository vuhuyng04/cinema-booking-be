from fastapi import APIRouter, Depends, HTTPException
from db import get_supabase
from deps import CurrentUser, get_current_user
from schemas import CreateBookingRequest, CreateBookingResponse

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=CreateBookingResponse)
async def create_booking(payload: CreateBookingRequest, user: CurrentUser = Depends(get_current_user)):
    if not payload.seats:
        raise HTTPException(status_code=400, detail="At least one seat required")
    sb = get_supabase()

    # Check showtime exists
    st = sb.table("showtimes").select("id").eq("id", payload.showtime_id).execute()
    if not st.data:
        raise HTTPException(status_code=404, detail="Showtime not found")

    # Check seat availability
    seat_ids = [s.seat_id for s in payload.seats]
    taken = sb.table("booking_seats").select("seat_id").eq("showtime_id", payload.showtime_id).in_("seat_id", seat_ids).execute()
    if taken.data:
        raise HTTPException(status_code=409, detail="One or more seats already booked")

    total = sum(s.price for s in payload.seats)

    booking = (
        sb.table("bookings")
        .insert({
            "user_id": user.user_id,
            "user_email": payload.user_email or user.email,
            "showtime_id": payload.showtime_id,
            "total_price": total,
            "status": "confirmed",
        })
        .execute()
    )
    if not booking.data:
        raise HTTPException(status_code=500, detail="Failed to create booking")
    booking_id = booking.data[0]["id"]

    try:
        sb.table("booking_seats").insert([
            {
                "booking_id": booking_id,
                "showtime_id": payload.showtime_id,
                "seat_id": s.seat_id,
                "price": s.price,
            }
            for s in payload.seats
        ]).execute()
    except Exception as e:
        # Rollback the booking row if seat insert fails (e.g., race condition)
        sb.table("bookings").delete().eq("id", booking_id).execute()
        raise HTTPException(status_code=409, detail=f"Seat reservation failed: {e}")

    return CreateBookingResponse(id=booking_id, total_price=total, status="confirmed")


@router.get("/me")
async def my_bookings(user: CurrentUser = Depends(get_current_user)):
    sb = get_supabase()
    res = (
        sb.table("bookings")
        .select(
            "id, total_price, status, created_at,"
            "showtime:showtimes(start_time,"
            "  hall:halls(name, cinema:cinemas(name)),"
            "  movie:movies(id, title, poster_url))"
        )
        .eq("user_id", user.user_id)
        .order("created_at", desc=True)
        .execute()
    )
    bookings = res.data or []
    # Fetch seats for each booking
    booking_ids = [b["id"] for b in bookings]
    seats_by_booking: dict[str, list] = {}
    if booking_ids:
        bs = (
            sb.table("booking_seats")
            .select("booking_id, seat:seats(row_label, col_number)")
            .in_("booking_id", booking_ids)
            .execute()
        )
        for row in bs.data or []:
            seats_by_booking.setdefault(row["booking_id"], []).append(row["seat"])
    for b in bookings:
        b["seats"] = seats_by_booking.get(b["id"], [])
    return bookings


@router.delete("/{booking_id}", status_code=204)
async def cancel_booking(booking_id: str, user: CurrentUser = Depends(get_current_user)):
    sb = get_supabase()
    existing = sb.table("bookings").select("user_id").eq("id", booking_id).execute()
    if not existing.data or existing.data[0]["user_id"] != user.user_id:
        raise HTTPException(status_code=404, detail="Booking not found")
    sb.table("bookings").update({"status": "cancelled"}).eq("id", booking_id).execute()
    sb.table("booking_seats").delete().eq("booking_id", booking_id).execute()
    return None
