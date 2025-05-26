from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.servicerequest import ServiceRequest
from datetime import datetime
from typing import Optional

collection = connect_to_mongodb("RIS_DataBase", "ServiceRequest")

def GetServiceRequestById(request_id: str):
    try:
        service_request = collection.find_one({"_id": ObjectId(request_id)})
        if service_request:
            service_request["_id"] = str(service_request["_id"])
            return "success", service_request
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def WriteServiceRequest(service_request_dict: dict):
    try:
        # Add current date if not provided
        if 'occurrenceDateTime' not in service_request_dict:
            service_request_dict['occurrenceDateTime'] = datetime.now().isoformat()
        
        # Simple validation - check patient exists
        if 'subject' in service_request_dict:
            from app.controlador.PatientCrud import GetPatientById
            patient_id = service_request_dict['subject']['reference'].split('/')[-1]
            status, _ = GetPatientById(patient_id)
            if status != 'success':
                return "invalidPatient", None

        # FHIR validation
        req = ServiceRequest.model_validate(service_request_dict)
        result = collection.insert_one(req.model_dump())
        
        return "success", str(result.inserted_id)
    except Exception as e:
        return f"error: {str(e)}", None

def GetServiceRequestByIdentifier(system: str, value: str):
    try:
        service_request = collection.find_one({
            "identifier.system": system,
            "identifier.value": value
        })
        if service_request:
            service_request["_id"] = str(service_request["_id"])
            return "success", service_request
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def GetServiceRequestsByPatient(patient_id: str):
    try:
        requests = list(collection.find({
            "subject.reference": f"Patient/{patient_id}"
        }))
        for req in requests:
            req["_id"] = str(req["_id"])
        return "success", requests
    except Exception as e:
        return f"error: {str(e)}", None