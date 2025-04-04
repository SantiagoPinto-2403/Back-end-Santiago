from fastapi import FastAPI, HTTPException, Request
import uvicorn
from app.controlador.PatientCrud import GetPatientById,WritePatient,GetPatientByIdentifier
from app.controlador.ServiceRequestCrud import GetServiceRequestById, WriteServiceRequest, GetServiceRequestByIdentifier
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://patient-santiago.onrender.com","https://servicerequest.onrender.com"],  # Permitir solo este dominio
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)

@app.get("/patient/{patient_id}", response_model=dict)
async def get_patient_by_id(patient_id: str):
    status,patient = GetPatientById(patient_id)
    if status=='success':
        return patient  # Return patient
    elif status=='notFound':
        raise HTTPException(status_code=204, detail="El paciente no existe")
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")

@app.post("/patient", response_model=dict)
async def add_patient(request: Request):
    new_patient_dict = dict(await request.json())
    status,patient_id = WritePatient(new_patient_dict)
    if status=='success':
        return {"_id":patient_id}  # Return patient id
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {status}")

@app.get("/patient", response_model=dict)
async def get_patient_by_identifier(system: str, value: str):
    status,patient = GetPatientByIdentifier(system,value)
    if status=='success':
        return patient  # Return patient
    elif status=='notFound':
        raise HTTPException(status_code=204, detail="El paciente no existe")
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")

@app.get("/servicerequest/{request_id}", response_model=dict)
async def get_service_request_by_id(request_id: str):
    status, service_request = GetServiceRequestById(request_id)  # Llamar a la función que obtiene la solicitud
    if status == 'success':
        return service_request  # Devolver la solicitud si se encuentra
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="La solicitud de servicio no existe")  # Código 204 si no se encuentra
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")  # Error interno

# Ruta para agregar una nueva solicitud de servicio
@app.post("/servicerequest", response_model=dict)
async def add_service_request(request: Request):
    new_service_request_dict = dict(await request.json())  # Convertir la solicitud JSON a un diccionario
    status, request_id = WriteServiceRequest(new_service_request_dict)  # Llamar a la función que escribe la solicitud
    if status == 'success':
        return {"_id": request_id}  # Devolver el ID de la solicitud si se creó correctamente
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {status}")  # Error interno

# Ruta para obtener una solicitud de servicio por su identificador
@app.get("/servicerequest", response_model=dict)
async def get_service_request_by_identifier(system: str, value: str):
    status, service_request = GetServiceRequestByIdentifier(system, value)  # Llamar a la función que busca la solicitud
    if status == 'success':
        return service_request  # Devolver la solicitud si se encuentra
    elif status == 'notFound':
        raise HTTPException(status_code=204, detail="La solicitud de servicio no existe")  # Código 204 si no se encuentra
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")  # Error interno

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
