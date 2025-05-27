from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
from pydantic import BaseModel
from typing import List, Optional
from bson import ObjectId
import uvicorn
from app.controlador.PatientCrud import GetPatientById, GetPatientByIdentifier, CheckDuplicatePatient, WritePatient
from app.controlador.ServiceRequestCrud import GetServiceRequestByIdentifier, GetServiceRequestById, GetServiceRequestsByPatient, WriteServiceRequest
from app.controlador.AppointmentCrud import GetAppointmentsByServiceRequest, WriteAppointment

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://patient-santiago.onrender.com","https://servicerequest.onrender.com","https://appointment-em7f.onrender.com","https://diagnosticreport.onrender.com","https://imagingstudy.onrender.com"],
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)

@app.get("/")
async def root():
    return {"message": "RIS API - Use /docs for documentation"}

# PATIENT ROUTES

@app.get("/patient/{patient_id}")
async def get_patient_by_id(patient_id: str):
    status, patient = GetPatientById(patient_id)
    if status == 'success':
        return patient
    elif status == 'notFound':
        raise HTTPException(status_code=404, detail="Patient not found")
    else:
        raise HTTPException(status_code=500, detail=status)

@app.post("/patient")
async def add_patient(request: Request):
    try:
        new_patient_dict = await request.json()
        status, patient_id = WritePatient(new_patient_dict)
        
        if status == 'success':
            return {"status": "success", "patient_id": patient_id}
        elif status == 'patientExists':
            return {"status": "exists", "existing_id": patient_id}
        else:
            raise HTTPException(status_code=400, detail=status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/patient")
async def get_patient_by_identifier(system: str, value: str):
    status, patient = GetPatientByIdentifier(system, value)
    if status == 'success':
        return patient
    elif status == 'notFound':
        raise HTTPException(status_code=404, detail="Patient not found")
    else:
        raise HTTPException(status_code=500, detail=status)

@app.post("/patient/check-duplicate")
async def check_duplicate_patient(request: Request):
    try:
        patient_data = await request.json()
        result = CheckDuplicatePatient(patient_data)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# SERVICE REQUEST ROUTES

@app.post("/servicerequest")
async def create_service_request(request: Request):
    data = await request.json()
    
    # Validate required identifier
    if not data.get('subject', {}).get('identifier'):
        raise HTTPException(
            status_code=400,
            detail="Se requiere identificador del paciente (sistema + valor)"
        )
    
    status, request_id = WriteServiceRequest(data)
    
    if status == 'success':
        return {"id": request_id}
    elif status == 'patientNotFound':
        raise HTTPException(404, "Paciente no encontrado con ese identificador")
    else:
        raise HTTPException(400, detail=status)

@app.get("/servicerequest/patient/{system}/{value}")
async def get_requests_by_patient(system: str, value: str):
    status, requests = GetServiceRequestsByPatient(system, value)
    
    if status == 'success':
        return requests
    else:
        raise HTTPException(400, detail=status)

@app.get("/servicerequest/{request_id}")
async def get_service_request(request_id: str):
    status, request = GetServiceRequestById(request_id)
    if status == 'success':
        return request
    raise HTTPException(status_code=404, detail="Solicitud no encontrada")

@app.get("/servicerequest")
async def get_service_request_by_identifier(system: str, value: str):
    status, request = GetServiceRequestByIdentifier(system, value)
    if status == 'success':
        return request
    raise HTTPException(status_code=404, detail="Solicitud no encontrada")

# APPOINTMENT ROUTES

@app.get("/appointment/service-request/{service_request_id}")
async def get_appointments_by_service_request(service_request_id: str):
    if not service_request_id or service_request_id == "undefined":
        raise HTTPException(
            status_code=400,
            detail="Invalid service request ID"
        )
    
    status, appointments = GetAppointmentsByServiceRequest(service_request_id)
    
    if status == 'success':
        return JSONResponse(
            status_code=200,
            content=appointments or []
        )
    elif status == 'invalidIdFormat':
        raise HTTPException(
            status_code=400,
            detail="Invalid service request ID format"
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Error fetching appointments"
        )

class AppointmentParticipant(BaseModel):
    actor: dict
    status: str

class AppointmentCreate(BaseModel):
    resourceType: str = "Appointment"
    status: str = "booked"
    basedOn: List[dict]
    start: str
    end: str
    appointmentType: dict
    description: Optional[str] = None
    participant: List[AppointmentParticipant]

@app.post("/appointment")
async def create_appointment(appointment: AppointmentCreate):
    try:
        # Validate service request reference
        if not appointment.basedOn or not isinstance(appointment.basedOn, list):
            raise HTTPException(
                status_code=422,
                detail="Appointment must reference a ServiceRequest"
            )

        sr_reference = appointment.basedOn[0].get('reference', '')
        if not sr_reference.startswith('ServiceRequest/'):
            raise HTTPException(
                status_code=422,
                detail="Invalid ServiceRequest reference format"
            )

        sr_id = sr_reference.split('/')[1]
        if not ObjectId.is_valid(sr_id):
            raise HTTPException(
                status_code=422,
                detail="Invalid ServiceRequest ID format"
            )

        # Verify service request exists
        from app.controlador.ServiceRequestCrud import GetServiceRequestById
        sr_status, sr_data = GetServiceRequestById(sr_id)
        if sr_status != 'success':
            raise HTTPException(
                status_code=404,
                detail="Referenced ServiceRequest not found"
            )

        # Check for existing appointment
        existing_appt = collection.find_one({
            "basedOn.reference": f"ServiceRequest/{sr_id}"
        })
        if existing_appt:
            raise HTTPException(
                status_code=409,
                detail=f"Appointment already exists: {str(existing_appt['_id'])}"
            )

        # Validate dates (updated for date-only format)
        try:
            # Handle both date-only (YYYY-MM-DD) and datetime strings
            if isinstance(appointment.start, str):
                if len(appointment.start) == 10:  # Date-only format
                    start_date = date.fromisoformat(appointment.start)
                    appointment.start = start_date.isoformat()
                else:  # Datetime format
                    start_dt = datetime.fromisoformat(appointment.start)
                    appointment.start = start_dt.date().isoformat()  # Convert to date-only
            
            if isinstance(appointment.end, str):
                if len(appointment.end) == 10:  # Date-only format
                    end_date = date.fromisoformat(appointment.end)
                    appointment.end = end_date.isoformat()
                else:  # Datetime format
                    end_dt = datetime.fromisoformat(appointment.end)
                    appointment.end = end_dt.date().isoformat()  # Convert to date-only

            # Ensure start and end are the same for date-only appointments
            if appointment.start != appointment.end:
                raise HTTPException(
                    status_code=422,
                    detail="For date-only appointments, start and end dates must be the same"
                )

        except ValueError:
            raise HTTPException(
                status_code=422,
                detail="Invalid date format (expected YYYY-MM-DD)"
            )

        # Create the appointment
        appointment_dict = appointment.dict()
        result = collection.insert_one(appointment_dict)
        
        return {"id": str(result.inserted_id)}

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error creating appointment: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error"
        )

# DIAGNOSTIC REPORT ROUTES 

##IMAGING STUDY


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
