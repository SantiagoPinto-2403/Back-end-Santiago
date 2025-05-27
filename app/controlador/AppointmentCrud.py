from connection import connect_to_mongodb
from bson import ObjectId
from datetime import datetime
from fhir.resources.appointment import Appointment
from app.controlador.ServiceRequestCrud import GetServiceRequestById

collection = connect_to_mongodb("RIS_DataBase", "Appointments")

def GetAppointmentById(appointment_id: str):
    try:
        if not ObjectId.is_valid(appointment_id):
            return "invalidIdFormat", None
            
        appointment = collection.find_one({"_id": ObjectId(appointment_id)})
        if not appointment:
            return "notFound", None
            
        appointment["_id"] = str(appointment["_id"])
        return "success", appointment
        
    except Exception as e:
        return f"error: {str(e)}", None

def WriteAppointment(appointment_dict: dict):
    try:
        # Validate ServiceRequest reference
        if not appointment_dict.get('basedOn') or not isinstance(appointment_dict['basedOn'], list):
            return "invalidServiceRequestReference", None
            
        sr_reference = appointment_dict['basedOn'][0].get('reference', '')
        if not sr_reference.startswith('ServiceRequest/'):
            return "invalidServiceRequestReference", None
            
        sr_id = sr_reference.split('/')[1]
        if not ObjectId.is_valid(sr_id):
            return "invalidServiceRequestId", None
        
        # Check if ServiceRequest exists and is active
        sr_status, sr_data = GetServiceRequestById(sr_id)
        if sr_status != 'success':
            return "serviceRequestNotFound", None
            
        if sr_data.get('status') not in ['active', 'completed']:
            return "serviceRequestNotActive", None
        
        # Verify no existing appointment for this ServiceRequest
        existing_appt = collection.find_one({
            "basedOn.reference": f"ServiceRequest/{sr_id}"
        })
        
        if existing_appt:
            existing_appt["_id"] = str(existing_appt["_id"])
            return "appointmentAlreadyExists", existing_appt
        
        # Validate appointment dates
        start_time = appointment_dict.get('start')
        end_time = appointment_dict.get('end')
        
        if start_time and end_time:
            try:
                start_dt = datetime.fromisoformat(start_time)
                end_dt = datetime.fromisoformat(end_time)
                if end_dt <= start_dt:
                    return "invalidAppointmentDuration", None
            except ValueError:
                return "invalidDateTimeFormat", None
        
        # Validate participant structure
        if not appointment_dict.get('participant') or not isinstance(appointment_dict['participant'], list):
            return "missingParticipants", None
        
        # Proceed with FHIR validation and creation
        appt = Appointment.model_validate(appointment_dict)
        result = collection.insert_one(appt.model_dump())
        
        return "success", str(result.inserted_id)
        
    except Exception as e:
        return f"error: {str(e)}", None

def GetAppointmentsByServiceRequest(service_request_id: str):
    try:
        if not service_request_id or service_request_id == "undefined":
            return "invalidIdFormat", None
            
        # First try direct lookup by ID reference
        appointments = list(collection.find({
            "basedOn.reference": f"ServiceRequest/{service_request_id}"
        }))
        
        # If no results, try alternative reference formats
        if not appointments:
            appointments = list(collection.find({
                "$or": [
                    {"basedOn.reference": service_request_id},  # Full URL format
                    {"basedOn.reference": f"ServiceRequest/{service_request_id}"},
                    {"basedOn.reference": {"$regex": f".*{service_request_id}$"}}
                ]
            }))
        
        # Convert ObjectId to string
        for appt in appointments:
            appt["_id"] = str(appt["_id"])
            
        return "success", appointments
        
    except Exception as e:
        print(f"Error getting appointments: {str(e)}")  # Log the error
        return f"error: {str(e)}", None