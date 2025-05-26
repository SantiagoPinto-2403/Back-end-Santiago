from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.patient import Patient
from fastapi import HTTPException
import logging

collection = connect_to_mongodb("RIS_DataBase", "Patients")
logger = logging.getLogger(__name__)

try:
    collection.create_index(
        [("identifier.system", 1), ("identifier.value", 1)], 
        unique=True,
        partialFilterExpression={"identifier": {"$exists": True}}
    )
    collection.create_index(
        [
            ("name.0.family", 1),
            ("name.0.given", 1),
            ("birthDate", 1)
        ],
        unique=True
    )
except Exception as e:
    logger.error(f"Error creating indexes: {str(e)}")


def GetPatientById(patient_id: str):
    try:
        patient = collection.find_one({"_id": ObjectId(patient_id)})
        if patient:
            patient["_id"] = str(patient["_id"])
            return "success", patient
        return "notFound", None
    except Exception as e:
        logger.error(f"Error in GetPatientById: {str(e)}")
        return f"error: {str(e)}", None

def GetPatientByIdentifier(patientSystem: str, patientValue: str):
    try:
        patient = collection.find_one({
            "identifier.system": patientSystem,
            "identifier.value": patientValue
        })
        if patient:
            patient["_id"] = str(patient["_id"])
            return "success", patient
        return "notFound", None
    except Exception as e:
        logger.error(f"Error in GetPatientByIdentifier: {str(e)}")
        return f"error: {str(e)}", None

def CheckDuplicatePatient(patient_dict: dict):
    try:
        # Check by identifier
        if 'identifier' in patient_dict and len(patient_dict['identifier']) > 0:
            identifier = patient_dict['identifier'][0]
            status, existing = GetPatientByIdentifier(identifier['system'], identifier['value'])
            if status == "success" and existing:
                return {
                    "isDuplicate": True,
                    "matchType": "identifier",
                    "existingId": existing['_id']
                }
        
        # Check by name + birthdate
        if 'name' in patient_dict and len(patient_dict['name']) > 0 and 'birthDate' in patient_dict:
            name = patient_dict['name'][0]
            existing = collection.find_one({
                "name.0.family": name.get('family'),
                "name.0.given": name.get('given', [""])[0],
                "birthDate": patient_dict['birthDate']
            })
            if existing:
                return {
                    "isDuplicate": True,
                    "matchType": "demographics",
                    "existingId": str(existing['_id'])
                }
        
        return {"isDuplicate": False}
    except Exception as e:
        logger.error(f"Error in CheckDuplicatePatient: {str(e)}")
        return {"isDuplicate": False, "error": str(e)}

def WritePatient(patient_dict: dict):
    try:
        # Validate FHIR structure
        try:
            Patient.model_validate(patient_dict)
        except Exception as e:
            return f"errorValidating: {str(e)}", None
        
        # Check for duplicates
        duplicate_check = CheckDuplicatePatient(patient_dict)
        if duplicate_check.get('isDuplicate'):
            return "patientExists", duplicate_check.get('existingId')
        
        # Insert new patient
        result = collection.insert_one(patient_dict)
        if result.inserted_id:
            return "success", str(result.inserted_id)
        return "errorInserting", None
    except Exception as e:
        logger.error(f"Error in WritePatient: {str(e)}")
        return f"error: {str(e)}", None