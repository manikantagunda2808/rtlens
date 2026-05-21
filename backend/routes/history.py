from fastapi import APIRouter, HTTPException, Header
from backend.services.supabase_service import get_client

router = APIRouter()

@router.get("/my")
def my_history(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        supabase = get_client()

        user = supabase.auth.get_user(token)
        user_id = user.user.id

        result = supabase.table("reviews")\
            .select("*")\
            .eq("user_id", user_id)\
            .order("created_at", desc=True)\
            .execute()

        return result.data

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/all")
def all_history(authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        supabase = get_client()

        # verify senior role
        user = supabase.auth.get_user(token)
        user_id = user.user.id

        profile = supabase.table("profiles")\
            .select("*")\
            .eq("id", user_id)\
            .single()\
            .execute()

        if profile.data["role"] != "senior":
            raise HTTPException(status_code=403, detail="Only seniors can view all reviews")

        result = supabase.table("reviews")\
            .select("*")\
            .order("created_at", desc=True)\
            .execute()

        return result.data

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
