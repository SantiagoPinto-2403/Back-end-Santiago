from fastapi import FastAPI, HTTPException, Request, Query
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

@app.get("/appointment/{appointment_id}")
async def get_appointment(appointment_id: str):
    status, appointment = GetAppointmentById(appointment_id)
    if status == 'success':
        return appointment
    elif status == 'notFound':
        raise HTTPException(404, detail="Appointment not found")
    else:
        raise HTTPException(400, detail=status)

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
 
@app.get("/diagnosticreport/{report_id}", response_model=dict)
async def get_diagnostic_report_by_id(report_id: str):
    status, diagnostic_report = GetDiagnosticReportById(report_id)  
    if status == 'success':
        return diagnostic_report 
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="El informe diagnóstico no existe") 
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")


@app.post("/diagnosticreport", response_model=dict)
async def add_diagnostic_report(request: Request):
    new_diagnostic_report_dict = dict(await request.json()) 
    status, report_id = WriteDiagnosticReport(new_diagnostic_report_dict)  
    if status == 'success':
        return {"_id": report_id}  
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {status}") 


@app.get("/diagnosticreport", response_model=dict)
async def get_diagnostic_report_by_identifier(system: str, value: str):
    status, diagnostic_report = GetDiagnosticReportByIdentifier(system, value) 
    if status == 'success':
        return diagnostic_report  
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="El informe diagnóstico no existe")
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")

# IMAGING STUDY ROUTES

@app.get("/imagingstudy/{study_id}", response_model=dict)
async def get_imaging_study_by_id(study_id: str):
    status, imaging_study = GetImagingStudyById(study_id)  
    if status == 'success':
        return imaging_study
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="El estudio de imagen no existe") 
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")


@app.post("/imagingstudy", response_model=dict)
async def add_imaging_study(request: Request):
    new_study_dict = dict(await request.json())
    status, study_id = WriteImagingStudy(new_study_dict)
    if status == 'success':
        return {"_id": study_id}
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {status}")


@app.get("/imagingstudy", response_model=dict)
async def get_imaging_study_by_identifier(system: str, value: str):
    status, imaging_study = GetImagingStudyByIdentifier(system, value)
    if status == 'success':
        return imaging_study
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="El estudio de imagen no existe")
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)