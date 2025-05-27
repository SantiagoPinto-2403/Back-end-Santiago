from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.appointment import Appointment
from fhir.resources.servicerequest import ServiceRequest
import json
from datetime import datetime

collection = connect_to_mongodb("RIS_DataBase", "Appointment")
service_request_collection = connect_to_mongodb("RIS_DataBase", "ServiceRequest")

def GetAppointmentById(appointment_id: str):
    try:
        appointment = collection.find_one({"_id": ObjectId(appointment_id)})
        if appointment:
            appointment["_id"] = str(appointment["_id"])
            return "success", appointment
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def CheckDuplicateAppointment(service_request_id: str, scheduled_time: str):
    """Check if an appointment already exists for this service request at this time"""
    try:
        existing = collection.find_one({
            "basedOn.reference": f"ServiceRequest/{service_request_id}",
            "start": scheduled_time
        })
        return existing is not None
    except Exception as e:
        print(f"Error checking duplicate appointment: {str(e)}")
        return False

def ValidateServiceRequestExists(service_request_id: str):
    """Verify the referenced ServiceRequest exists"""
    try:
        return service_request_collection.find_one({"_id": ObjectId(service_request_id)}) is not None
    except Exception as e:
        print(f"Error validating ServiceRequest: {str(e)}")
        return False

def WriteAppointment(appointment_dict: dict):
    try:
        # Validate FHIR structure first
        appt = Appointment.model_validate(appointment_dict)
    except Exception as e:
        return f"errorValidating: {str(e)}", None
    
    # Extract key fields for validation
    based_on_ref = appointment_dict.get("basedOn", [{}])[0].get("reference", "").split("/")
    if len(based_on_ref) != 2 or based_on_ref[0] != "ServiceRequest":
        return "error: Invalid ServiceRequest reference", None
    
    service_request_id = based_on_ref[1]
    scheduled_time = appointment_dict.get("start")
    
    # Validate required relationships
    if not ValidateServiceRequestExists(service_request_id):
        return "error: ServiceRequest not found", None
    
    # Check for duplicates
    if CheckDuplicateAppointment(service_request_id, scheduled_time):
        return "error: Duplicate appointment exists for this ServiceRequest at this time", None
    
    # Add metadata
    appointment_dict["meta"] = {
        "lastUpdated": datetime.now().isoformat(),
        "versionId": "1"
    }
    
    # Insert the validated appointment
    try:
        result = collection.insert_one(appointment_dict)
        if result.inserted_id:
            return "success", str(result.inserted_id)
        return "error: Insertion failed", None
    except Exception as e:
        return f"errorInserting: {str(e)}", None

def GetAppointmentByIdentifier(appointmentSystem, appointmentValue):
    try:
        appointment = collection.find_one({
            "identifier": {
                "$elemMatch": {
                    "system": appointmentSystem,
                    "value": appointmentValue
                }
            }
        })
        if appointment:
            appointment["_id"] = str(appointment["_id"])
            return "success", appointment
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def GetAppointmentsByServiceRequest(service_request_id: str):
    """Get all appointments for a specific ServiceRequest"""
    try:
        appointments = list(collection.find({
            "basedOn.reference": f"ServiceRequest/{service_request_id}"
        }))
        for appt in appointments:
            appt["_id"] = str(appt["_id"])
        return "success", appointments
    except Exception as e:
        return f"error: {str(e)}", None