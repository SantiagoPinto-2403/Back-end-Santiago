from connection import connect_to_mongodb
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException
from fhir.resources.appointment import Appointment
from app.controlador.ServiceRequestCrud import GetServiceRequestById

collection = connect_to_mongodb("RIS_DataBase", "Appointments")

def GetAppointmentById(appointment_id: str):
    try:
        # First check if it's a valid ObjectId
        if not ObjectId.is_valid(appointment_id):
            return "invalidIdFormat", None
            
        appointment = collection.find_one({"_id": ObjectId(appointment_id)})
        
        if not appointment:
            return "notFound", None
            
        # Convert ObjectId to string for JSON serialization
        appointment["_id"] = str(appointment["_id"])
        
        # Ensure basedOn reference is properly formatted if it exists
        if 'basedOn' in appointment and isinstance(appointment['basedOn'], list):
            for ref in appointment['basedOn']:
                if 'reference' in ref and not ref['reference'].startswith('ServiceRequest/'):
                    ref['reference'] = f"ServiceRequest/{ref['reference'].split('/')[-1]}"
        
        return "success", appointment
        
    except Exception as e:
        return f"error: {str(e)}", None

def WriteAppointment(appointment_dict: dict):
    try:
        # Validate ServiceRequest reference
        sr_reference = appointment_dict.get('basedOn', [{}])[0].get('reference', '')
        if not sr_reference.startswith('ServiceRequest/'):
            return "invalidServiceRequestReference", None
            
        sr_id = sr_reference.split('/')[1]
        
        # Check if ServiceRequest exists
        from app.controlador.ServiceRequestCrud import GetServiceRequestById
        sr_status, sr_data = GetServiceRequestById(sr_id)
        if sr_status != 'success':
            return "serviceRequestNotFound", None
        
        # Verify no existing appointment for this ServiceRequest
        existing_appt = collection.find_one({
            "basedOn.reference": f"ServiceRequest/{sr_id}"
        })
        
        if existing_appt:
            return "appointmentAlreadyExists", str(existing_appt['_id'])
        
        # Proceed with creation
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