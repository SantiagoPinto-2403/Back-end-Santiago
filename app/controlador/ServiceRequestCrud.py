from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.servicerequest import ServiceRequest
from datetime import datetime
from typing import Optional
from app.controlador.PatientCrud import GetPatientByIdentifier

collection = connect_to_mongodb("RIS_DataBase", "ServiceRequest")

def WriteServiceRequest(service_request_dict: dict):
    try:
        # Validate patient exists via identifier ONLY
        if 'identifier' not in service_request_dict.get('subject', {}):
            return "missingPatientIdentifier", None
            
        identifier = service_request_dict['subject']['identifier']
        status, patient = GetPatientByIdentifier(
            identifier['system'], 
            identifier['value']
        )
        
        if status != 'success':
            return "patientNotFound", None

        # Proceed with FHIR validation
        req = ServiceRequest.model_validate(service_request_dict)
        result = collection.insert_one(req.model_dump())
        
        return "success", str(result.inserted_id)
        
    except Exception as e:
        return f"error: {str(e)}", None


def GetServiceRequestsByPatient(system: str, value: str):
    """Get all requests for a patient using their identifier"""
    try:
        requests = list(collection.find({
            "subject.identifier.system": system,
            "subject.identifier.value": value
        }))
        
        for req in requests:
            req["_id"] = str(req["_id"])
            
        return "success", requests
        
    except Exception as e:
        return f"error: {str(e)}", None

def GetServiceRequestById(request_id: str):
    try:
        # First try direct ID lookup
        if ObjectId.is_valid(request_id):
            request = collection.find_one({"_id": ObjectId(request_id)})
            if request:
                request["_id"] = str(request["_id"])
                return "success", request
        
        # Fallback: Try by identifier value if not found by ID
        request = collection.find_one({"identifier.value": request_id})
        if request:
            request["_id"] = str(request["_id"])
            return "success", request
            
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def GetServiceRequestByIdentifier(system: str, value: str):
    try:
        request = collection.find_one({
            "identifier.system": system,
            "identifier.value": value
        })
        if request:
            request["_id"] = str(request["_id"])
            return "success", request
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None