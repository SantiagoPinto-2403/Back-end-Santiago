from fastapi import FastAPI, HTTPException, Request
import uvicorn
from app.controlador.PatientCrud import GetPatientById, WritePatient, GetPatientByIdentifier, CheckDuplicatePatient
from app.controlador.ServiceRequestCrud import WriteServiceRequest, GetServiceRequestsByPatient
from app.controlador.AppointmentCrud import GetAppointmentById, WriteAppointment, GetAppointmentByIdentifier
from app.controlador.DiagnosticReportCrud import GetDiagnosticReportById, WriteDiagnosticReport, GetDiagnosticReportByIdentifier
from app.controlador.ImagingStudyCrud import GetImagingStudyById, WriteImagingStudy, GetImagingStudyByIdentifier
from fastapi.middleware.cors import CORSMiddleware

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

##SERVICE REQUEST

@app.get("/servicerequest/{request_id}", response_model=dict)
async def get_service_request_by_id(request_id: str):
    status, service_request = GetServiceRequestById(request_id)  
    if status == 'success':
        return service_request 
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="La solicitud de servicio no existe") 
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")

@app.post("/servicerequest", response_model=dict)
async def add_service_request(request: Request):
    new_service_request_dict = dict(await request.json()) 
    status, request_id = WriteServiceRequest(new_service_request_dict)  
    if status == 'success':
        return {"_id": request_id}  
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {status}") 

@app.get("/servicerequest", response_model=dict)
async def get_service_request_by_identifier(system: str, value: str):
    status, service_request = GetServiceRequestByIdentifier(system, value) 
    if status == 'success':
        return service_request  
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="La solicitud de servicio no existe")
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")  

##APPOINTMENT

@app.get("/servicerequest/{request_id}")
async def get_service_request_by_id(request_id: str):
    status, service_request = GetServiceRequestById(request_id)
    if status == 'success':
        return service_request
    elif status == 'notFound':
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    raise HTTPException(status_code=400, detail=status)

@app.post("/servicerequest")
async def create_service_request(request: Request):
    data = await request.json()
    
    # Simple validation
    if 'subject' not in data or 'reference' not in data['subject']:
        raise HTTPException(status_code=400, detail="Se requiere referencia al paciente")
    
    status, request_id = WriteServiceRequest(data)
    if status == 'success':
        return {"id": request_id}
    elif status == 'invalidPatient':
        raise HTTPException(status_code=400, detail="Paciente no existe")
    raise HTTPException(status_code=400, detail=status)

@app.get("/servicerequest/patient/{patient_id}")
async def get_requests_by_patient(patient_id: str):
    status, requests = GetServiceRequestsByPatient(patient_id)
    if status == 'success':
        return requests
    raise HTTPException(status_code=400, detail=status)

##DIAGNOSTIC REPORT 

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


# Get requests by patient identifier
@app.get("/servicerequest/patient/{system}/{value}")
async def get_requests_by_patient(system: str, value: str):
    status, requests = GetServiceRequestsByPatient(system, value)
    
    if status == 'success':
        return requests
    else:
        raise HTTPException(400, detail=status)

##IMAGING STUDY

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
