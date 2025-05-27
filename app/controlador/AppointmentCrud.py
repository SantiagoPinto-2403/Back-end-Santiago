from bson import ObjectId
from datetime import datetime
from pymongo import ReturnDocument
from app.controlador.ServiceRequestCrud import GetServiceRequestById

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
        # Validate service request reference
        if not appointment_dict.get('basedOn') or not isinstance(appointment_dict['basedOn'], list):
            return "invalidServiceRequestReference", None
            
        sr_reference = appointment_dict['basedOn'][0].get('reference', '')
        if not sr_reference.startswith('ServiceRequest/'):
            return "invalidServiceRequestReference", None
            
        sr_id = sr_reference.split('/')[1]
        if not ObjectId.is_valid(sr_id):
            return "invalidServiceRequestId", None
        
        # Check service request exists
        sr_status, sr_data = GetServiceRequestById(sr_id)
        if sr_status != 'success':
            return "serviceRequestNotFound", None
            
        # Check for existing appointment (with transaction)
        with collection.database.client.start_session() as session:
            with session.start_transaction():
                existing = collection.find_one(
                    {"basedOn.reference": f"ServiceRequest/{sr_id}"},
                    session=session
                )
                
                if existing:
                    return "appointmentAlreadyExists", str(existing['_id'])
                
                # Validate FHIR resource
                appt = Appointment.model_validate(appointment_dict)
                result = collection.insert_one(
                    appt.model_dump(),
                    session=session
                )
                
                session.commit_transaction()
                return "success", str(result.inserted_id)
                
    except Exception as e:
        print(f"DB Error in WriteAppointment: {str(e)}")
        return f"error: {str(e)}", None