from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from supabase import create_client, Client
from datetime import datetime
import os
from dotenv import load_dotenv
import uuid

# Load environment variables
load_dotenv()

app = FastAPI(title="ADR Event Microservice")

# Enable CORS (you can restrict this later for security)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Supabase client setup
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
    notes: str = Form(None),
    reporter_info: str = Form("System")  # Default value if not passed
):
    try:
        report_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat()

        # Insert into patient_data
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

        # Create report entry
        report_entry = {
            "id": report_id,
            "created_at": created_at,
            "reporter_info": reporter_info,  # ✅ Fix for missing NOT NULL column
            "patient_info": f"{patient_name}, {patient_age}, {patient_gender}",
            "suspected_drugs": [drug_name],  # PostgreSQL expects array format
            "adverse_event": adverse_event,
            "other_drugs": [],
            "image_links": [],
            "status": "Pending",
            "processed": False,
            "notes": notes
        }

        supabase.table("reports").insert(report_entry).execute()

        return {
            "message": "Form data stored successfully",
            "report_id": report_id
        }

    except Exception as e:
        return {"error": str(e)}


# ---------------------------
# 🖼 IMAGE UPLOAD ENDPOINT
# ---------------------------
@app.post("/upload-image")
async def upload_image(report_id: str = Form(...), file: UploadFile = File(...)):
    try:
        file_bytes = await file.read()
        file_name = f"{uuid.uuid4()}_{file.filename}"

        # Upload to Supabase storage (make sure you have a "report-images" bucket)
        storage_path = f"report-images/{file_name}"
        supabase.storage.from_("report-images").upload(storage_path, file_bytes)

        # Get public URL for the uploaded file
        file_url = supabase.storage.from_("report-images").get_public_url(storage_path)

        # Insert file metadata
        supabase.table("report_images").insert({
            "report_id": report_id,
            "file_name": file_name,
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
    message: dict  # JSON message from ElevenLabs agent
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


# ---------------------------
# 🏠 ROOT ENDPOINT
# ---------------------------
@app.get("/")
def root():
    return {"status": "ADR microservice running 🚀"}
