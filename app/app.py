from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime
import uvicorn
from app.controlador.PatientCrud import GetPatientById, GetPatientByIdentifier, CheckDuplicatePatient, WritePatient
from app.controlador.ServiceRequestCrud import GetServiceRequestByIdentifier, GetServiceRequestById, GetServiceRequestsByPatient, WriteServiceRequest
from app.controlador.AppointmentCrud import GetAppointmentById, WriteAppointment, GetAppointmentsByServiceRequest

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://patient-santiago.onrender.com","https://servicerequest.onrender.com","https://appointment-em7f.onrender.com","https://diagnosticreport.onrender.com","https://imagingstudy.onrender.com"],  # Permitir solo este dominio
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
async def create_appointment(request: Request):
    try:
        appointment_data = await request.json()
        
        # Validate required fields
        if not appointment_data.get('basedOn'):
            raise HTTPException(
                status_code=422,
                detail="Appointment must reference a ServiceRequest"
            )
            
        # Auto-fill missing required FHIR fields
        appointment_data.setdefault('status', 'booked')
        appointment_data.setdefault('participant', [{
            'actor': {'reference': 'Practitioner/unknown'},
            'status': 'accepted'
        }])
        
        # Save to database
        status, result = WriteAppointment(appointment_data)
        
        if status == 'success':
            return JSONResponse(
                status_code=201,
                content={"id": result}
            )
        elif status == 'appointmentAlreadyExists':
            raise HTTPException(
                status_code=409,
                detail={
                    "message": "Appointment already exists for this ServiceRequest",
                    "existing_appointment_id": result
                }
            )
        elif status == 'serviceRequestNotFound':
            raise HTTPException(status_code=404, detail="Referenced ServiceRequest not found")
        elif status == 'serviceRequestNotActive':
            raise HTTPException(status_code=400, detail="Referenced ServiceRequest is not active")
        elif status == 'invalidAppointmentDuration':
            raise HTTPException(status_code=400, detail="End time must be after start time")
        else:
            raise HTTPException(status_code=400, detail=status)
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )

@app.get("/appointment/service-request/{service_request_id}")
async def get_appointment_for_service_request(service_request_id: str):
    if service_request_id == "undefined":
        raise HTTPException(
            status_code=400,
            detail="Invalid service request ID"
        )
    
    status, appointments = GetAppointmentsByServiceRequest(service_request_id)
    
    if status == 'success':
        if not appointments:
            raise HTTPException(status_code=404, detail="No appointments found")
        return appointments
    elif status == 'invalidIdFormat':
        raise HTTPException(status_code=400, detail="Invalid ID format")
    else:
        raise HTTPException(status_code=500, detail=status)


# DIAGNOSTIC REPORT ROUTES 

##IMAGING STUDY


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
