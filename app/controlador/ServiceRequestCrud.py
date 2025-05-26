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