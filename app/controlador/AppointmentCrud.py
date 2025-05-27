from connection import connect_to_mongodb
from bson import ObjectId
from datetime import datetime
from pymongo import ReturnDocument
from app.controlador.ServiceRequestCrud import GetServiceRequestById

collection = connect_to_mongodb("RIS_DataBase", "Appointments")

def GetAppointmentsByServiceRequest(service_request_id: str):
    try:
        if not service_request_id or not ObjectId.is_valid(service_request_id):
            return "invalidIdFormat", None
        
        # Try multiple reference formats
        query = {
            "$or": [
                {"basedOn.reference": f"ServiceRequest/{service_request_id}"},
                {"basedOn.reference": f"ServiceRequest/{ObjectId(service_request_id)}"},
                {"basedOn.reference": {"$regex": f"ServiceRequest/{service_request_id}$"}},
                {"basedOn.0.reference": f"ServiceRequest/{service_request_id}"}
            ]
        }
        
        appointments = list(collection.find(query))
        
        # Convert ObjectIds to strings
        for appt in appointments:
            appt["_id"] = str(appt["_id"])
            
        return "success", appointments
        
    except Exception as e:
        print(f"DB Error in GetAppointmentsByServiceRequest: {str(e)}")
        return f"error: {str(e)}", None

def WriteAppointment(appointment_dict: dict):
    try:
        # Validate ServiceRequest exists
        sr_reference = appointment_dict.get('basedOn', [{}])[0].get('reference', '')
        if not sr_reference.startswith('ServiceRequest/'):
            return "invalidServiceRequest", None
            
        sr_id = sr_reference.split('/')[1]
        sr_status, _ = GetServiceRequestById(sr_id)
        if sr_status != 'success':
            return "serviceRequestNotFound", None
        
        # FHIR validation
        appt = Appointment.model_validate(appointment_dict)
        result = collection.insert_one(appt.model_dump())
        
        return "success", str(result.inserted_id)
    except Exception as e:
        return f"error: {str(e)}", None