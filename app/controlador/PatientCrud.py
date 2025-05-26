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
            if result.inserted_id:
                return {
                    "status": "success",
                    "message": "Patient created successfully",
                    "insertedId": str(result.inserted_id),
                    "patient": mongo_patient  # Return the created patient data
                }
            else:
                return {
                    "status": "error",
                    "message": "Failed to create patient"
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