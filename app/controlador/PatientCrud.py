from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.patient import Patient
from fastapi import HTTPException
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

collection = connect_to_mongodb("RIS_DataBase", "Patients")

def setup_indexes():
    try:
        # Create indexes with error handling
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

# Call this when your application starts
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
        # Check by identifier
        if patient_data.get('identifier') and len(patient_data['identifier']) > 0:
            identifier = patient_data['identifier'][0]
            result = GetPatientByIdentifier(identifier.get('system'), identifier.get('value'))
            if result.get('status') == "success" and result.get('patient'):
                return {
                    "isDuplicate": True,
                    "matchType": "identifier",
                    "existingId": result['patient']['_id']
                }
        
        # Check by name + birthdate
        if (patient_data.get('name') and len(patient_data['name']) > 0 and 
            isinstance(patient_data['name'][0], dict) and 
            patient_data.get('birthDate')):
            
            name = patient_data['name'][0]
            existing = collection.find_one({
                "name.0.family": name.get('family'),
                "name.0.given": name.get('given', [""])[0],
                "birthDate": patient_data['birthDate']
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
            pat = Patient.model_validate(patient_dict)
            validated_patient = pat.model_dump()
        except Exception as validation_error:
            logger.error(f"Validation error: {str(validation_error)}")
            return {
                "status": "error",
                "message": f"Invalid patient data: {str(validation_error)}",
                "details": str(validation_error)
            }
        
        # Check for duplicates
        duplicate_check = CheckDuplicatePatient(validated_patient)
        if duplicate_check.get('isDuplicate'):
            return {
                "status": "exists",
                "message": "Patient already exists",
                "existingId": duplicate_check.get('existingId'),
                "matchType": duplicate_check.get('matchType')
            }
        
        # Insert new patient
        try:
            result = collection.insert_one(validated_patient)
            return {
                "status": "success",
                "insertedId": str(result.inserted_id)
            }
        except Exception as insert_error:
            if "duplicate key error" in str(insert_error).lower():
                # Handle race condition where duplicate was inserted between check and insert
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