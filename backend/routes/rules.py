from fastapi import APIRouter, HTTPException, Header
from backend.services.rules_service import load_raw_rules, save_rules
from backend.services.supabase_service import get_client

router = APIRouter()

@router.get("/{review_type}")
def get_rules(review_type: str):
    try:
        rules = load_raw_rules(review_type)
        return rules
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/{review_type}")
def update_rules(review_type: str, data: dict, authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        supabase = get_client()

        # verify senior role
        user = supabase.auth.get_user(token)
        user_id = user.user.id

        profile = supabase.table("profiles").select("*").eq("id", user_id).single().execute()

        if profile.data["role"] != "senior":
            raise HTTPException(status_code=403, detail="Only seniors can update rules")

        save_rules(review_type, data)
        return {"message": f"{review_type} rules updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
