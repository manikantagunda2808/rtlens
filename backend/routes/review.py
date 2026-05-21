from fastapi import APIRouter, HTTPException, Header, UploadFile, File, Form
from pydantic import BaseModel
from backend.services.groq_service import review_code
from backend.services.rules_service import load_rules
from backend.services.supabase_service import get_client
import zipfile
import io
import os

router = APIRouter()

def detect_file_type(filename: str) -> str:
    name = filename.lower()
    uvm_keywords = ["_seq", "_driver", "_agent", "_env", "_monitor", "_scoreboard", "uvm_"]
    tb_keywords = ["_tb", "_testbench", "_test"]
    if any(k in name for k in uvm_keywords):
        return "uvm"
    if any(k in name for k in tb_keywords):
        return "tb"
    return "rtl"

def load_assignment_rules(assignment: dict, rule_type: str) -> str:
    # always load global rules first
    global_rules = load_rules(rule_type)
    
    # check if assignment has specific rules
    rules_data = assignment.get(f"{rule_type}_rules", [])
    if not rules_data:
        # no assignment rules — global only
        return global_rules
    
    # combine global + assignment rules
    assignment_rules = ""
    for r in rules_data:
        assignment_rules += f"- [{r['id']}] ({r['severity'].upper()}) {r['rule']}\n"
    
    return global_rules + "\n# Assignment Specific Rules\n" + assignment_rules

@router.post("/run")
async def run_review(
    assignment_id: str = Form(...),
    user_name: str = Form(...),
    file: UploadFile = File(...),
    authorization: str = Header(...)
):
    try:
        token = authorization.replace("Bearer ", "")
        supabase = get_client()

        # verify user
        user = supabase.auth.get_user(token)
        user_id = user.user.id

        # get assignment
        assignment = supabase.table("assignments").select("*").eq("id", assignment_id).single().execute()
        assignment_data = assignment.data

        # extract zip
        content = await file.read()
        zip_file = zipfile.ZipFile(io.BytesIO(content))

        # group files by type
        files_by_type = {"rtl": [], "tb": [], "uvm": []}
        for name in zip_file.namelist():
            if name.endswith((".v", ".sv", ".uvm")) and not name.startswith("__"):
                file_type = detect_file_type(os.path.basename(name))
                code = zip_file.read(name).decode("utf-8", errors="ignore")
                files_by_type[file_type].append({"name": name, "code": code})

        # review each group
        all_violations = []
        all_warnings = []
        all_passed = []
        total_score = 0
        reviewed_count = 0
        combined_summary = []

        for ftype, files in files_by_type.items():
            if not files:
                continue
            combined_code = "\n\n".join([f"### {f['name']}\n{f['code']}" for f in files])
            rules = load_assignment_rules(assignment_data, ftype)
            result = review_code(combined_code, rules, ftype)

            all_violations.extend(result.get("violations", []))
            all_warnings.extend(result.get("warnings", []))
            all_passed.extend(result.get("passed", []))
            total_score += result.get("score", 0)
            reviewed_count += 1
            combined_summary.append(f"[{ftype.upper()}] {result.get('summary', '')}")

        final_score = round(total_score / reviewed_count, 1) if reviewed_count else 0
        final_summary = " | ".join(combined_summary)

        # save to supabase
        supabase.table("reviews").insert({
            "user_id": user_id,
            "user_name": user_name,
            "review_type": "mixed",
            "code": f"ZIP upload — {assignment_data['name']}",
            "score": final_score,
            "violations": all_violations,
            "warnings": all_warnings,
            "passed": all_passed,
            "summary": final_summary
        }).execute()

        return {
            "score": final_score,
            "violations": all_violations,
            "warnings": all_warnings,
            "passed": all_passed,
            "summary": final_summary
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
class PasteReviewRequest(BaseModel):
    review_type: str
    code: str
    user_name: str

@router.post("/paste")
async def paste_review(req: PasteReviewRequest, authorization: str = Header(...)):
    try:
        token = authorization.replace("Bearer ", "")
        supabase = get_client()
        user = supabase.auth.get_user(token)
        user_id = user.user.id

        rules = load_rules(req.review_type)
        result = review_code(req.code, rules, req.review_type)

        supabase.table("reviews").insert({
            "user_id": user_id,
            "user_name": req.user_name,
            "review_type": req.review_type,
            "code": req.code,
            "score": result["score"],
            "violations": result["violations"],
            "warnings": result["warnings"],
            "passed": result["passed"],
            "summary": result["summary"]
        }).execute()

        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
