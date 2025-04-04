from fastapi import FastAPI, HTTPException, Request
import uvicorn
from app.controlador.PatientCrud import GetServiceRequestById,WriteServiceRequest
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://servicerequest.onrender.com"],  # Permitir solo este dominio
    allow_credentials=True,
    allow_methods=["*"],  # Permitir todos los métodos (GET, POST, etc.)
    allow_headers=["*"],  # Permitir todos los encabezados
)

@app.get("/")
async def root():
    return{"message":"API funcionando"}

@app.get("/service/{service_request_id}", response_model=dict)
async def get_service_request_by_id(service_request_id: str):
    status,service_request = GetServiceRequestById(service_request_id)
    if status=='success':
        return service_request  # Return service request
    elif status=='notFound':
        raise HTTPException(status_code=204, detail="La solicitud no existe")
    else:
        raise HTTPException(status_code=500, detail=f"Error interno del servidor. {status}")

@app.post("/service", response_model=dict)
async def add_service_request(request: Request):
    new_service_dict = await request.json()
    status,service_request_id = WriteServiceRequest(new_service_dict)
    if status=='success':
        return {"_id":service_request_id}  # Return patient id
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

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
