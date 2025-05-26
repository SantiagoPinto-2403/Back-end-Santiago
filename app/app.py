from fastapi import FastAPI, HTTPException, Request
import uvicorn
from app.controlador.PatientCrud import GetPatientById, WritePatient, GetPatientByIdentifier, CheckDuplicatePatient
from app.controlador.ServiceRequestCrud import GetServiceRequestById, WriteServiceRequest, GetServiceRequestByIdentifier
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

app.get("/patient/{patient_id}")
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

@app.get("/appointment/{appointment_id}", response_model=dict)
async def get_appointment_by_id(appointment_id: str):
    status, appointment = GetAppointmentById(appointment_id) 
    if status == 'success':
        return appointment  
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="Appointment not found")
    else:
        raise HTTPException(status_code=500, detail=f"Internal server error. {status}")

@app.post("/appointment", response_model=dict)
async def add_appointment(request: Request):
    new_appointment_dict = dict(await request.json())  
    status, appointment_id = WriteAppointment(new_appointment_dict) 
    if status == 'success':
        return {"_id": appointment_id}
    else:
        raise HTTPException(status_code=500, detail=f"Internal server error: {status}")

@app.get("/appointment", response_model=dict)
async def get_appointment_by_identifier(system: str, value: str):
    status, appointment = GetAppointmentByIdentifier(system, value) 
    if status == 'success':
        return appointment  
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="Appointment not found")
    else:
        raise HTTPException(status_code=500, detail=f"Internal server error. {status}")

##DIAGNOSTIC REPORT 

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
