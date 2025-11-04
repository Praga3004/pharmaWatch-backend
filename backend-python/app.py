from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime
import os
from dotenv import load_dotenv
import uuid

# Load environment
load_dotenv()

app = FastAPI(title="ADR Event Microservice")

# Allow frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------
# 🩺 FORM SUBMISSION ENDPOINT
# ---------------------------
@app.post("/submit-form")
async def submit_form(
    patient_name: str = Form(...),
    patient_age: int = Form(...),
    patient_gender: str = Form(...),
    drug_name: str = Form(...),
    dosage: str = Form(...),
    adverse_event: str = Form(...),
    severity_level: str = Form(...),
    notes: str = Form(None)
):
    report_id = str(uuid.uuid4())
    created_at = datetime.utcnow().isoformat()

    # Insert into patient_data
    supabase.table("pateint_data").insert({
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

    # Create report entry
    report_entry = {
        "id": report_id,
        "created_at": created_at,
        "patient_info": f"{patient_name}, {patient_age}, {patient_gender}",
        "suspected_drugs": drug_name,
        "adverse_event": adverse_event,
        "status": "Pending",
        "processed": False,
        "notes": notes
    }
    supabase.table("reports").insert(report_entry).execute()

    return {"message": "Form data stored successfully", "report_id": report_id}


# ---------------------------
# 🖼 IMAGE UPLOAD ENDPOINT
# ---------------------------
@app.post("/upload-image")
async def upload_image(report_id: str = Form(...), file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        file_name = f"{uuid.uuid4()}_{file.filename}"

        # Upload to Supabase Storage bucket (e.g., "report-images")
        storage_path = f"report-images/{file_name}"
        supabase.storage.from_("report-images").upload(storage_path, file_bytes)

        # Get public URL
        file_url = supabase.storage.from_("report-images").get_public_url(storage_path)

        # Insert metadata
        supabase.table("report_images").insert({
            "report_id": report_id,
            "filename": file_name,
            "file_url": file_url,
            "file_type": file.content_type,
            "uploaded_at": datetime.utcnow().isoformat()
        }).execute()

        return {"message": "Image uploaded successfully", "file_url": file_url}
    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# 🗣 CONVERSATION LOG ENDPOINT
# ---------------------------
class ConversationRequest(BaseModel):
    report_id: str
    sender: str  # "agent" or "patient"
    message: dict  # full JSON message from ElevenLabs agent
    context_data: dict | None = None

@app.post("/conversation")
async def log_conversation(data: ConversationRequest):
    try:
        supabase.table("report_conversations").insert({
            "report_id": data.report_id,
            "seder": data.sender,
            "message": data.message,
            "context_data": data.context_data,
            "timestamp": datetime.utcnow().isoformat()
        }).execute()

        return {"message": "Conversation logged successfully"}
    except Exception as e:
        return {"error": str(e)}


@app.get("/")
def root():
    return {"status": "ADR microservice running 🚀"}
