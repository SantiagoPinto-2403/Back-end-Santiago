from fastapi import FastAPI, HTTPException, Request, APIRouter, Query
import uvicorn
from app.controlador.PatientCrud import GetPatientById, WritePatient, GetPatientByIdentifier, CheckDuplicatePatient
from app.controlador.ServiceRequestCrud import WriteServiceRequest, GetServiceRequestsByPatient, GetServiceRequestByIdentifier, GetServiceRequestById
from app.controlador.AppointmentCrud import WriteAppointment, GetAppointmentById
from app.controlador.DiagnosticReportCrud import GetDiagnosticReportById, WriteDiagnosticReport, GetDiagnosticReportByIdentifier
from app.controlador.ImagingStudyCrud import GetImagingStudyById, WriteImagingStudy, GetImagingStudyByIdentifier
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
from typing import Optional

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://patient-santiago.onrender.com","https://servicerequest.onrender.com","https://appointment-em7f.onrender.com","https://diagnosticreport.onrender.com","https://imagingstudy.onrender.com"],  # Permitir solo este dominio
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)

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

# Add these endpoints if not already present
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

@app.post("/appointment")
async def create_appointment(appointment_data: dict):
    # Validate required fields
    if not appointment_data.get('basedOn'):
        raise HTTPException(400, "Se requiere referencia a ServiceRequest")
    
    # Auto-fill missing required FHIR fields
    appointment_data.setdefault('status', 'booked')
    appointment_data.setdefault('participant', [{
        'actor': {'reference': 'Practitioner/unknown'},
        'status': 'accepted'
    }])
    
    # Validate dates
    try:
        if 'start' in appointment_data:
            datetime.fromisoformat(appointment_data['start'])
        if 'end' in appointment_data:
            datetime.fromisoformat(appointment_data['end'])
    except ValueError:
        raise HTTPException(400, "Formato de fecha inválido")
    
    # Save to database
    status, appt_id = WriteAppointment(appointment_data)
    
    if status == 'success':
        return {"id": appt_id}
    elif status == 'appointmentAlreadyExists':
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una cita para esta solicitud (ID: {appt_id})"
        )
    elif status == 'serviceRequestNotFound':
        raise HTTPException(400, "Solicitud de servicio no encontrada")
    else:
        raise HTTPException(400, detail=status)

# DIAGNOSTIC REPORT ROUTES 

# IMAGING STUDY ROUTES

@router.post("/")
async def create_imaging_study(study_data: dict):
    """Create a new ImagingStudy with validation"""
    status, result = WriteImagingStudy(study_data)
    
    if status == 'success':
        return {"id": result}
    elif status.startswith('errorValidating'):
        raise HTTPException(status_code=422, detail=status)
    elif status == 'errorInserting':
        raise HTTPException(status_code=500, detail="Failed to create imaging study")
    else:
        raise HTTPException(status_code=400, detail=status)

@router.get("/{study_id}")
async def get_imaging_study_by_id(study_id: str):
    """Get an ImagingStudy by ID"""
    status, study = GetImagingStudyById(study_id)
    
    if status == 'success':
        return study
    elif status == 'notFound':
        raise HTTPException(status_code=404, detail="Imaging study not found")
    else:
        raise HTTPException(status_code=500, detail=status)

@router.get("/")
async def get_imaging_study_by_identifier(
    system: Optional[str] = Query(None),
    value: Optional[str] = Query(None)
):
    """Get ImagingStudy by identifier (requires both system and value)"""
    if not (system and value):
        raise HTTPException(
            status_code=400,
            detail="Both system and value parameters are required"
        )
    
    status, study = GetImagingStudyByIdentifier(system, value)
    
    if status == 'success':
        return study
    elif status == 'notFound':
        raise HTTPException(status_code=404, detail="Imaging study not found")
    else:
        raise HTTPException(status_code=500, detail=status)

@router.get("/by-appointment/{appointment_id}")
async def get_imaging_study_by_appointment(appointment_id: str):
    """Get ImagingStudy by appointment reference"""
    # This would require a new CRUD function - see note below
    status, study = GetImagingStudyByAppointment(appointment_id)
    
    if status == 'success':
        return study
    elif status == 'notFound':
        raise HTTPException(status_code=404, detail="No imaging study found for this appointment")
    else:
        raise HTTPException(status_code=500, detail=status)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)