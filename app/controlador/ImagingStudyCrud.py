from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.imagingstudy import ImagingStudy
from fastapi import HTTPException

collection = connect_to_mongodb("RIS_DataBase", "ImagingStudies")
appointment_collection = connect_to_mongodb("RIS_DataBase", "Appointments")

def _validate_appointment_reference(study_dict: dict) -> tuple:
    """
    Validate that the referenced appointment exists and is unique
    Returns (status, message) tuple
    """
    if "basedOn" not in study_dict or not study_dict["basedOn"]:
        return "error", "Missing appointment reference in basedOn"
    
    # Find first appointment reference
    appointment_ref = next(
        (ref for ref in study_dict["basedOn"] 
         if isinstance(ref, dict) and ref.get("reference", "").startswith("Appointment/")),
        None
    )
    
    if not appointment_ref:
        return "error", "No valid Appointment reference found in basedOn"
    
    try:
        appointment_id = appointment_ref["reference"].split("/")[1]
        if not ObjectId.is_valid(appointment_id):
            return "error", "Invalid appointment ID format"
        
        # Check if appointment exists
        if not appointment_collection.find_one({"_id": ObjectId(appointment_id)}):
            return "notFound", "Referenced appointment not found"
        
        # Check if imaging study already exists for this appointment
        existing_study = collection.find_one({
            "basedOn.reference": f"Appointment/{appointment_id}"
        })
        
        if existing_study:
            return "exists", "ImagingStudy already exists for this appointment"
            
        return "success", appointment_id
        
    except Exception as e:
        return "error", f"Validation error: {str(e)}"

def GetImagingStudyById(study_id: str) -> tuple:
    """Get ImagingStudy by MongoDB _id"""
    try:
        if not ObjectId.is_valid(study_id):
            return "invalidId", None
            
        study = collection.find_one({"_id": ObjectId(study_id)})
        if study:
            study["_id"] = str(study["_id"])
            return "success", study
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def GetImagingStudyByIdentifier(study_system: str, study_value: str) -> tuple:
    """Get ImagingStudy by identifier system and value"""
    try:
        study = collection.find_one({
            "identifier": {
                "$elemMatch": {
                    "system": study_system,
                    "value": study_value
                }
            }
        })
        if study:
            study["_id"] = str(study["_id"])
            return "success", study
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def GetImagingStudyByAppointment(appointment_id: str) -> tuple:
    """Get ImagingStudy by appointment reference"""
    try:
        if not ObjectId.is_valid(appointment_id):
            return "invalidId", None
            
        study = collection.find_one({
            "basedOn.reference": f"Appointment/{appointment_id}"
        })
        if study:
            study["_id"] = str(study["_id"])
            return "success", study
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def WriteImagingStudy(study_dict: dict) -> tuple:
    """Create a new ImagingStudy with validation"""
    # Validate appointment reference first
    appt_status, appt_message = _validate_appointment_reference(study_dict)
    if appt_status != "success":
        return appt_status, appt_message
    
    # Validate FHIR resource
    try:
        study = ImagingStudy.model_validate(study_dict)
    except Exception as e:
        return f"validationError: {str(e)}", None
    
    # Insert into database
    try:
        validated_study = study.model_dump()
        result = collection.insert_one(validated_study)
        if result.inserted_id:
            return "success", str(result.inserted_id)
        return "insertError", None
    except Exception as e:
        return f"databaseError: {str(e)}", None

def UpdateImagingStudy(study_id: str, update_data: dict) -> tuple:
    """Update an existing ImagingStudy"""
    # First validate the study exists
    status, existing_study = GetImagingStudyById(study_id)
    if status != "success":
        return status, None
    
    # Prevent changing appointment reference
    if "basedOn" in update_data:
        existing_refs = existing_study.get("basedOn", [])
        new_refs = update_data.get("basedOn", [])
        
        existing_appt = next(
            (ref["reference"] for ref in existing_refs 
             if isinstance(ref, dict) and ref.get("reference", "").startswith("Appointment/")),
            None
        )
        
        new_appt = next(
            (ref["reference"] for ref in new_refs 
             if isinstance(ref, dict) and ref.get("reference", "").startswith("Appointment/")),
            None
        )
        
        if existing_appt and new_appt and existing_appt != new_appt:
            return "invalidUpdate", "Cannot change appointment reference"
    
    # Validate FHIR resource with updates
    try:
        updated_study = {**existing_study, **update_data}
        ImagingStudy.model_validate(updated_study)
    except Exception as e:
        return f"validationError: {str(e)}", None
    
    # Update in database
    try:
        result = collection.update_one(
            {"_id": ObjectId(study_id)},
            {"$set": update_data}
        )
        if result.modified_count == 1:
            return "success", study_id
        return "notModified", None
    except Exception as e:
        return f"databaseError: {str(e)}", None

def DeleteImagingStudy(study_id: str) -> tuple:
    """Delete an ImagingStudy"""
    try:
        if not ObjectId.is_valid(study_id):
            return "invalidId", None
            
        result = collection.delete_one({"_id": ObjectId(study_id)})
        if result.deleted_count == 1:
            return "success", None
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None