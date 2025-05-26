from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.patient import Patient
from datetime import datetime, date
import logging

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
        # Create unique indexes
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

# Initialize indexes when module loads
setup_indexes()

def WritePatient(patient_dict: dict):
    """
    Creates a new patient with duplicate checking
    Returns tuple: (status, data/message)
    """
    try:
        # Validate FHIR structure
        try:
            patient = Patient.model_validate(patient_dict)
            validated_data = patient.model_dump()
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return "errorValidating", f"Invalid patient data: {str(e)}"

        # Convert dates for MongoDB
        mongo_patient = convert_dates_to_string(validated_data)

        # Check for duplicates by identifier
        if 'identifier' in mongo_patient and len(mongo_patient['identifier']) > 0:
            identifier = mongo_patient['identifier'][0]
            status, existing = GetPatientByIdentifier(
                identifier.get('system'), 
                identifier.get('value')
            )
            if status == "success" and existing:
                return "exists", existing['_id']

        # Check for duplicates by name + birthdate
        if ('name' in mongo_patient and len(mongo_patient['name']) > 0 and 
            'birthDate' in mongo_patient):
            name = mongo_patient['name'][0]
            existing = collection.find_one({
                "name.0.family": name.get('family'),
                "name.0.given": name.get('given', [""])[0],
                "birthDate": mongo_patient['birthDate']
            })
            if existing:
                return "exists", str(existing['_id'])

        # Insert new patient
        try:
            result = collection.insert_one(mongo_patient)
            if result.inserted_id:
                return "success", str(result.inserted_id)
            return "errorInserting", "Failed to create patient"
        except Exception as e:
            if "duplicate key error" in str(e).lower():
                # Handle race condition where duplicate was inserted between check and insert
                status, existing = GetPatientByIdentifier(
                    mongo_patient['identifier'][0]['system'],
                    mongo_patient['identifier'][0]['value']
                )
                if status == "success":
                    return "exists", existing['_id']
                return "errorInserting", "Duplicate patient detected but could not retrieve ID"
            logger.error(f"Insert error: {str(e)}")
            return "errorInserting", f"Database error: {str(e)}"

    except Exception as e:
        logger.error(f"Unexpected error in WritePatient: {str(e)}")
        return "error", f"Unexpected error: {str(e)}"

def GetPatientById(patient_id: str):
    """Retrieve patient by ID"""
    try:
        if not ObjectId.is_valid(patient_id):
            return "notFound", None
        
        patient = collection.find_one({"_id": ObjectId(patient_id)})
        if patient:
            patient["_id"] = str(patient["_id"])
            return "success", patient
        return "notFound", None
    except Exception as e:
        logger.error(f"Error in GetPatientById: {str(e)}")
        return "error", None

def GetPatientByIdentifier(patientSystem: str, patientValue: str):
    """Retrieve patient by identifier"""
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
        return "error", None

def UpdatePatient(patient_id: str, update_data: dict):
    """Update existing patient"""
    try:
        if not ObjectId.is_valid(patient_id):
            return "invalidId", None
        
        # Validate update data
        try:
            Patient.model_validate(update_data)
        except Exception as e:
            return "validationError", str(e)

        # Convert dates
        mongo_data = convert_dates_to_string(update_data)
        
        result = collection.update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": mongo_data}
        )
        
        if result.modified_count == 1:
            return "success", patient_id
        return "notModified", None
    except Exception as e:
        logger.error(f"Error updating patient: {str(e)}")
        return "error", None

def DeletePatient(patient_id: str):
    """Delete a patient"""
    try:
        if not ObjectId.is_valid(patient_id):
            return "invalidId"
        
        result = collection.delete_one({"_id": ObjectId(patient_id)})
        if result.deleted_count == 1:
            return "success"
        return "notFound"
    except Exception as e:
        logger.error(f"Error deleting patient: {str(e)}")
        return "error"