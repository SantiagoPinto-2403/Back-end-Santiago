from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.servicerequest import ServiceRequest
import json

collection = connect_to_mongodb("RIS_DataBase", "ServiceRequest")


def GetServiceRequestById(request_id: str):
    try:
        service_request = collection.find_one({"_id": ObjectId(request_id)})
        if service_request:
            service_request["_id"] = str(service_request["_id"])
            return "success", service_request
        return "notFound", None
    except Exception:
        return "error", None


def WriteServiceRequest(service_request_dict: dict):
    try:
        req = ServiceRequest.model_validate(service_request_dict)
    except Exception as e:
        return f"errorValidating: {str(e)}", None
    validated_service_request_json = req.model_dump()
    result = collection.insert_one(validated_service_request_json)
    if result:
        inserted_id = str(result.inserted_id)
        return "success", inserted_id
    return "errorInserting", None


def GetServiceRequestByIdentifier(requestSystem, requestValue):
    try:
        service_request = collection.find_one({"identifier.system": requestSystem, "identifier.value": requestValue})
        if service_request:
            service_request["_id"] = str(service_request["_id"])
            return "success", service_request
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

