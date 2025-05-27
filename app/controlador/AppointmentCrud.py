from connection import connect_to_mongodb
from bson import ObjectId
from datetime import datetime
from fhir.resources.appointment import Appointment
from app.controlador.ServiceRequestCrud import GetServiceRequestById

collection = connect_to_mongodb("RIS_DataBase", "Appointments")

def GetAppointmentById(appointment_id: str):
    try:
        appointment = collection.find_one({"_id": ObjectId(appointment_id)})
        if appointment:
            appointment["_id"] = str(appointment["_id"])
            return "success", appointment
        return "notFound", None
    except Exception as e:
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

def GetAppointmentsByServiceRequest(service_request_id: str):
    try:
        appointments = list(collection.find({
            "basedOn.reference": f"ServiceRequest/{service_request_id}"
        }))
        
        for appt in appointments:
            appt["_id"] = str(appt["_id"])
            
        return "success", appointments
    except Exception as e:
        return f"error: {str(e)}", None