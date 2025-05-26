from datetime import datetime, date
from bson import ObjectId
from fhir.resources.patient import Patient
import logging
from connection import connect_to_mongodb

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

collection = connect_to_mongodb("RIS_DataBase", "Patients")

def convert_dates_to_string(obj):
    """Recursively convert date objects to ISO format strings"""
    if isinstance(obj, dict):
        return {k: convert_dates_to_string(v) for k, v in obj.items()}
    elif isinstance(obj, (list, tuple)):
        return [convert_dates_to_string(v) for v in obj]
    elif isinstance(obj, date):
        return obj.isoformat()
    return obj

def setup_indexes():
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
        logger.info("Database indexes created successfully")
    except Exception as e:
        logger.error(f"Error creating indexes: {str(e)}")

setup_indexes()

def GetPatientById(patient_id: str):
    try:
        if not ObjectId.is_valid(patient_id):
            return {"status": "error", "message": "Invalid patient ID format"}
        
        patient = collection.find_one({"_id": ObjectId(patient_id)})
        if patient:
            patient["_id"] = str(patient["_id"])
            return {"status": "success", "patient": patient}
        return {"status": "notFound", "message": "Patient not found"}
    except Exception as e:
        logger.error(f"Error in GetPatientById: {str(e)}")
        return {"status": "error", "message": str(e)}

def GetPatientByIdentifier(patientSystem: str, patientValue: str):
    try:
        patient = collection.find_one({
            "identifier.system": patientSystem,
            "identifier.value": patientValue
        })
        if patient:
            patient["_id"] = str(patient["_id"])
            return {"status": "success", "patient": patient}
        return {"status": "notFound", "message": "Patient not found"}
    except Exception as e:
        logger.error(f"Error in GetPatientByIdentifier: {str(e)}")
        return {"status": "error", "message": str(e)}

def CheckDuplicatePatient(patient_data: dict):
    try:
        # Convert dates to strings for MongoDB query
        query_data = convert_dates_to_string(patient_data)
        
        # Check by identifier
        if query_data.get('identifier') and len(query_data['identifier']) > 0:
            identifier = query_data['identifier'][0]
            result = GetPatientByIdentifier(identifier.get('system'), identifier.get('value'))
            if result.get('status') == "success" and result.get('patient'):
                return {
                    "isDuplicate": True,
                    "matchType": "identifier",
                    "existingId": result['patient']['_id']
                }
        
        # Check by name + birthdate
        if (query_data.get('name') and len(query_data['name']) > 0 and 
            isinstance(query_data['name'][0], dict) and 
            query_data.get('birthDate')):
            
            name = query_data['name'][0]
            existing = collection.find_one({
                "name.0.family": name.get('family'),
                "name.0.given": name.get('given', [""])[0],
                "birthDate": query_data['birthDate']
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
        # First validate FHIR structure
        try:
            pat = Patient.model_validate(patient_dict)
            validated_patient = pat.model_dump()
        except Exception as validation_error:
            logger.error(f"Validation error: {str(validation_error)}")
            return {
                "status": "error",
                "message": f"Invalid patient data: {str(validation_error)}",
                "details": str(validation_error)
            }
        
        # Convert dates to strings for MongoDB
        mongo_patient = convert_dates_to_string(validated_patient)
        
        # Check for duplicates
        duplicate_check = CheckDuplicatePatient(mongo_patient)
        if duplicate_check.get('isDuplicate'):
            return {
                "status": "exists",
                "message": "Patient already exists",
                "existingId": duplicate_check.get('existingId'),
                "matchType": duplicate_check.get('matchType')
            }
        
        # Insert new patient
        try:
            result = collection.insert_one(mongo_patient)
            return {
                "status": "success",
                "insertedId": str(result.inserted_id)
            }
        except Exception as insert_error:
            if "duplicate key error" in str(insert_error).lower():
                return {
                    "status": "exists",
                    "message": "Patient was just created by another process"
                }
            logger.error(f"Insert error: {str(insert_error)}")
            return {
                "status": "error",
                "message": f"Failed to insert patient: {str(insert_error)}"
            }
            
    except Exception as e:
        logger.error(f"Unexpected error in WritePatient: {str(e)}")
        return {
            "status": "error",
            "message": "Internal server error",
            "details": str(e)
        }