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
        sr = ServiceRequest.parse_obj(service_request_dict)
    except Exception as e:
        return f"errorValidating: {str(e)}", None

    # Revisión paso a paso
    subject = service_request_dict.get("subject", {})
    subject_ref = subject.get("reference")

    code = service_request_dict.get("code", {})
    coding_list = code.get("coding", [])
    procedure_code = coding_list[0].get("code") if coding_list else None

    # Imprimir para debug
    print("✅ subject.reference:", subject_ref)
    print("✅ code.coding[0].code:", procedure_code)

    if not subject_ref or not procedure_code:
        return "missingKeyFields", None

    # Verificar si ya existe
    existing = service_requests_collection.find_one({
        "subject.reference": subject_ref,
        "code.coding.0.code": procedure_code
    })

    if existing:
        return "alreadyExists", str(existing["_id"])

    # Insertar si no existe
    result = service_requests_collection.insert_one(service_request_dict)
    if result.inserted_id:
        return "success", str(result.inserted_id)
    else:
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

