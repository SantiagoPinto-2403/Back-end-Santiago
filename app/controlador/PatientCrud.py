from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.patient import Patient
from fastapi import HTTPException

collection = connect_to_mongodb("RIS_DataBase", "Patients")

# Create indexes (run this once during application startup)
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

def GetPatientById(patient_id: str):
    try:
        patient = collection.find_one({"_id": ObjectId(patient_id)})
        if patient:
            patient["_id"] = str(patient["_id"])
            return {"status": "success", "patient": patient}
        return {"status": "notFound", "message": "Patient not found"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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
        raise HTTPException(status_code=400, detail=str(e))

def CheckDuplicatePatient(patient_data: dict):
    # Check by identifier
    if 'identifier' in patient_data and len(patient_data['identifier']) > 0:
        identifier = patient_data['identifier'][0]
        result = GetPatientByIdentifier(identifier['system'], identifier['value'])
        if result['status'] == "success":
            return {
                "isDuplicate": True,
                "matchType": "identifier",
                "existingId": result['patient']['_id']
            }
    
    # Check by name + birthdate
    if 'name' in patient_data and len(patient_data['name']) > 0 and 'birthDate' in patient_data:
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

def WritePatient(patient_dict: dict):
    # First validate FHIR structure
    try:
        pat = Patient.model_validate(patient_dict)
    except Exception as e:
        return {"status": "error", "message": f"Validation failed: {str(e)}"}
    
    # Check for duplicates
    duplicate_check = CheckDuplicatePatient(patient_dict)
    if duplicate_check['isDuplicate']:
        return {
            "status": "exists",
            "message": "Patient already exists",
            "existingId": duplicate_check['existingId'],
            "matchType": duplicate_check['matchType']
        }
    
    # Insert new patient
    try:
        result = collection.insert_one(patient_dict)
        return {
            "status": "success",
            "insertedId": str(result.inserted_id)
        }
    except Exception as e:
        return {"status": "error", "message": f"Insert failed: {str(e)}"}