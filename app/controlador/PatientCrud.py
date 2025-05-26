from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.patient import Patient
from fastapi import HTTPException
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

# CREATE
def CreatePatient(patient_data: dict):
    """
    Creates a new patient with duplicate checking
    Returns tuple: (status, data/message)
    """
    try:
        # Validate FHIR structure
        try:
            patient = Patient.model_validate(patient_data)
            validated_data = patient.model_dump()
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            return "validation_error", f"Invalid patient data: {str(e)}"

        # Convert dates for MongoDB
        mongo_patient = convert_dates_to_string(validated_data)

        # Check for duplicates
        duplicate_status, duplicate_id = check_for_duplicates(mongo_patient)
        if duplicate_status:
            return "exists", duplicate_id

        # Insert new patient
        try:
            result = collection.insert_one(mongo_patient)
            if result.inserted_id:
                return "success", str(result.inserted_id)
            return "error", "Failed to create patient"
        except Exception as e:
            if "duplicate key error" in str(e).lower():
                return "exists", find_existing_patient(mongo_patient)
            logger.error(f"Insert error: {str(e)}")
            return "error", f"Database error: {str(e)}"

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return "error", f"Unexpected error: {str(e)}"

def check_for_duplicates(patient_data: dict):
    """Check for existing patients by identifier or demographics"""
    # Check by identifier
    if patient_data.get('identifier') and len(patient_data['identifier']) > 0:
        identifier = patient_data['identifier'][0]
        status, existing = GetPatientByIdentifier(
            identifier.get('system'), 
            identifier.get('value')
        )
        if status == "success" and existing:
            return True, existing['_id']

    # Check by name + birthdate
    if (patient_data.get('name') and len(patient_data['name']) > 0 and 
        patient_data.get('birthDate')):
        name = patient_data['name'][0]
        existing = collection.find_one({
            "name.0.family": name.get('family'),
            "name.0.given": name.get('given', [""])[0],
            "birthDate": patient_data['birthDate']
        })
        if existing:
            return True, str(existing['_id'])
    
    return False, None

def find_existing_patient(patient_data: dict):
    """Find existing patient after duplicate key error"""
    try:
        if patient_data.get('identifier'):
            identifier = patient_data['identifier'][0]
            status, patient = GetPatientByIdentifier(
                identifier.get('system'),
                identifier.get('value')
            )
            if status == "success":
                return patient['_id']
        
        if patient_data.get('name') and patient_data.get('birthDate'):
            name = patient_data['name'][0]
            existing = collection.find_one({
                "name.0.family": name.get('family'),
                "name.0.given": name.get('given', [""])[0],
                "birthDate": patient_data['birthDate']
            })
            if existing:
                return str(existing['_id'])
    except Exception as e:
        logger.error(f"Error finding existing patient: {str(e)}")
    return "unknown_id"

# READ
def GetPatientById(patient_id: str):
    """Retrieve patient by ID"""
    try:
        if not ObjectId.is_valid(patient_id):
            return "invalid_id", None
        
        patient = collection.find_one({"_id": ObjectId(patient_id)})
        if patient:
            patient["_id"] = str(patient["_id"])
            return "success", patient
        return "not_found", None
    except Exception as e:
        logger.error(f"Error in GetPatientById: {str(e)}")
        return "error", None

def GetPatientByIdentifier(system: str, value: str):
    """Retrieve patient by identifier"""
    try:
        patient = collection.find_one({
            "identifier.system": system,
            "identifier.value": value
        })
        if patient:
            patient["_id"] = str(patient["_id"])
            return "success", patient
        return "not_found", None
    except Exception as e:
        logger.error(f"Error in GetPatientByIdentifier: {str(e)}")
        return "error", None

def ListPatients(skip: int = 0, limit: int = 100):
    """List patients with pagination"""
    try:
        patients = list(collection.find().skip(skip).limit(limit))
        for p in patients:
            p["_id"] = str(p["_id"])
        return "success", patients
    except Exception as e:
        logger.error(f"Error listing patients: {str(e)}")
        return "error", None

# UPDATE
def UpdatePatient(patient_id: str, update_data: dict):
    """Update existing patient"""
    try:
        if not ObjectId.is_valid(patient_id):
            return "invalid_id", None
        
        # Validate update data
        try:
            Patient.model_validate(update_data)
        except Exception as e:
            return "validation_error", str(e)

        # Convert dates
        mongo_data = convert_dates_to_string(update_data)
        
        result = collection.update_one(
            {"_id": ObjectId(patient_id)},
            {"$set": mongo_data}
        )
        
        if result.modified_count == 1:
            return "success", patient_id
        return "not_modified", None
    except Exception as e:
        logger.error(f"Error updating patient: {str(e)}")
        return "error", None

# DELETE
def DeletePatient(patient_id: str):
    """Delete a patient"""
    try:
        if not ObjectId.is_valid(patient_id):
            return "invalid_id"
        
        result = collection.delete_one({"_id": ObjectId(patient_id)})
        if result.deleted_count == 1:
            return "success"
        return "not_found"
    except Exception as e:
        logger.error(f"Error deleting patient: {str(e)}")
        return "error"