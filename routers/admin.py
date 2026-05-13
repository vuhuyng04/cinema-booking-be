from fastapi import APIRouter, Depends, HTTPException
from db import get_supabase
from deps import get_admin_user
from schemas import CreateMovieRequest, UpdateMovieRequest, CreateShowtimeRequest

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(get_admin_user)])


@router.post("/movies")
async def create_movie(payload: CreateMovieRequest):
    sb = get_supabase()
    body = payload.model_dump(exclude_none=True)
    res = sb.table("movies").insert(body).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Insert failed")
    return res.data[0]


@router.put("/movies/{movie_id}")
async def update_movie(movie_id: str, payload: UpdateMovieRequest):
    sb = get_supabase()
    res = sb.table("movies").update(payload.model_dump(exclude_none=True)).eq("id", movie_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="Movie not found")
    return res.data[0]


@router.delete("/movies/{movie_id}", status_code=204)
async def delete_movie(movie_id: str):
    sb = get_supabase()
    sb.table("movies").delete().eq("id", movie_id).execute()
    return None


@router.post("/showtimes")
async def create_showtime(payload: CreateShowtimeRequest):
    sb = get_supabase()
    res = sb.table("showtimes").insert(payload.model_dump()).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Insert failed")
    return res.data[0]


@router.delete("/showtimes/{showtime_id}", status_code=204)
async def delete_showtime(showtime_id: str):
    sb = get_supabase()
    sb.table("showtimes").delete().eq("id", showtime_id).execute()
    return None
