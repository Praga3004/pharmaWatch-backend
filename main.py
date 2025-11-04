from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime
from dotenv import load_dotenv
import os, uuid
from mangum import Mangum

load_dotenv()

app = FastAPI(title="ADR Event Microservice")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.get("/")
def root():
    return {"status": "ADR microservice running 🚀"}

@app.post("/submit-form")
async def submit_form(
    patient_name: str = Form(...),
    patient_age: int = Form(...),
    patient_gender: str = Form(...),
    drug_name: str = Form(...),
    dosage: str = Form(...),
    adverse_event: str = Form(...),
    severity_level: str = Form(...),
    notes: str = Form(None),
    reporter_info: str = Form("System")
):
    try:
        report_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        supabase.table("patient_data").insert({
            "created_at": created_at,
            "name": patient_name,
            "age": patient_age,
            "gender": patient_gender,
            "drug": drug_name,
            "dosage": dosage,
            "ae": adverse_event,
            "severity": severity_level,
            "notes": notes
        }).execute()

        report_entry = {
            "id": report_id,
            "created_at": created_at,
            "reporter_info": reporter_info,
            "patient_info": f"{patient_name}, {patient_age}, {patient_gender}",
            "suspected_drugs": [drug_name],
            "adverse_event": adverse_event,
            "other_drugs": [],
            "image_links": [],
            "status": "Pending",
            "processed": False,
            "notes": notes
        }
        supabase.table("reports").insert(report_entry).execute()

        return {"message": "Form data stored successfully", "report_id": report_id}
    except Exception as e:
        return {"error": str(e)}

class ConversationRequest(BaseModel):
    report_id: str
    sender: str
    message: dict
    context_data: dict | None = None

@app.post("/conversation")
async def log_conversation(data: ConversationRequest):
    try:
        supabase.table("report_conversations").insert({
            "report_id": data.report_id,
            "sender": data.sender,
            "message": data.message,
            "context_data": data.context_data,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()
        return {"message": "Conversation logged successfully"}
    except Exception as e:
        return {"error": str(e)}
handler = Mangum(app)