from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from backend.services.supabase_service import get_client

router = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str  # junior or senior

@router.post("/login")
def login(req: LoginRequest):
    try:
        supabase = get_client()
        response = supabase.auth.sign_in_with_password({
            "email": req.email,
            "password": req.password
        })
        user = response.user
        session = response.session

        profile = supabase.table("profiles").select("*").eq("id", user.id).single().execute()

        return {
            "access_token": session.access_token,
            "user_id": user.id,
            "name": profile.data["name"],
            "role": profile.data["role"]
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid credentials")

@router.post("/signup")
def signup(req: SignupRequest):
    try:
        supabase = get_client()
        response = supabase.auth.sign_up({
            "email": req.email,
            "password": req.password
        })
        user = response.user

        supabase.table("profiles").insert({
            "id": user.id,
            "name": req.name,
            "role": req.role
        }).execute()

        return {"message": "Account created successfully"}
    except Exception as e:
        print(f"SIGNUP ERROR: {e}")  # add this line
        raise HTTPException(status_code=400, detail=str(e))
