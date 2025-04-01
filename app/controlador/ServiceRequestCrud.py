from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.servicerequest import ServiceRequest
import json

collection = connect_to_mongodb("RIS_DataBase", "ServiceRequest")


def GetServiceRrquestById(service_request_id: str):
    try:
        service_request = collection.find_one({"_id": ObjectId(service_request_id)})
        if service_request:
            service_request["_id"] = str(service_request["_id"])
            return "success", service_request
        return "notFound", None
    except Exception as e:
        return f"notFound", None

def WriteServiceRequest(patient_dict: dict):
    try:
        ser = servicerequest.model_validate(patient_dict)
    except Exception as e:
        return f"errorValidating: {str(e)}",None
    validated_service_request_json = ser.model_dump()
    result = collection.insert_one(validated_service_request_json)
    if result:
        inserted_id = str(result.inserted_id)
        return "success",inserted_id
    else:
        return "errorInserting", None

def GetPatientByIdentifier(patientSystem,patientValue):
    try:
        patient = collection.find_one({"identifier.system":patientSystem,"identifier.value":patientValue})
        if patient:
            patient["_id"] = str(patient["_id"])
            return "success", patient
        return "notFound", None
    except Exception as e:
        return f"error encontrado: {str(e)}", None
