from connection import connect_to_mongodb
from bson import ObjectId
from datetime import datetime
from fastapi import HTTPException
from pydantic import ValidationError
from fhir.resources.imagingstudy import ImagingStudy
from app.controlador.AppointmentCrud import GetAppointmentById

collection = connect_to_mongodb("RIS_DataBase", "ImagingStudies")

def GetImagingStudyById(imaging_study_id: str):
    try:
        study = collection.find_one({"_id": ObjectId(imaging_study_id)})
        if study:
            study["_id"] = str(study["_id"])
            return "success", study
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def GetImagingStudyByIdentifier(identifier: str):
    try:
        study = collection.find_one({"identifier.value": identifier})
        if study:
            study["_id"] = str(study["_id"])
            return "success", study
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def WriteImagingStudy(imaging_study_dict: dict):
    try:
        # 1. Validate Appointment reference
        appt_reference = imaging_study_dict.get('basedOn', [{}])[0].get('reference', '')
        if not appt_reference.startswith('Appointment/'):
            return "invalidAppointmentReference", None
            
        appt_id = appt_reference.split('/')[1]
        
        # 2. Check if Appointment exists
        appt_status, appt_data = GetAppointmentById(appt_id)
        if appt_status != 'success':
            return "appointmentNotFound", None
        
        # 3. Check for duplicate ImagingStudy
        existing_study = collection.find_one({
            "basedOn.reference": f"Appointment/{appt_id}"
        })
        if existing_study:
            return "imagingStudyAlreadyExists", str(existing_study['_id'])

        # 4. Validate required FHIR fields
        if not imaging_study_dict.get('status'):
            imaging_study_dict['status'] = 'registered'  # Default status
            
        if not imaging_study_dict.get('started'):
            return "missingRequiredField: started", None
            
        # 5. Ensure proper datetime format with timezone
        if 'started' in imaging_study_dict:
            try:
                started = imaging_study_dict['started']
                if not started.endswith('Z') and 'T' in started:
                    imaging_study_dict['started'] = f"{started}Z"
                datetime.fromisoformat(imaging_study_dict['started'].replace('Z', '+00:00'))
            except ValueError:
                return "invalidDateTimeFormat", None

        # 6. Validate modality structure
        if 'modality' in imaging_study_dict:
            for modality in imaging_study_dict['modality']:
                if not isinstance(modality, dict) or 'code' not in modality:
                    return "invalidModalityStructure", None

        # 7. FHIR Resource Validation
        try:
            study = ImagingStudy.model_validate(imaging_study_dict)
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = ".".join(str(loc) for loc in error['loc'])
                errors.append(f"{field}: {error['msg']}")
            return f"validationError: {', '.join(errors)}", None
            
        # 8. Add default values if missing
        study_dict = study.model_dump()
        if 'numberOfSeries' not in study_dict:
            study_dict['numberOfSeries'] = 1
        if 'numberOfInstances' not in study_dict:
            study_dict['numberOfInstances'] = 1
        if 'series' not in study_dict:
            study_dict['series'] = [{
                'uid': "1.2.3.4",  # Placeholder UID
                'number': 1,
                'modality': study_dict['modality'][0] if study_dict.get('modality') else {'code': 'OT'},
                'numberOfInstances': 1
            }]

        # 9. Save to database
        result = collection.insert_one(study_dict)
        
        return "success", str(result.inserted_id)
        
    except Exception as e:
        return f"error: {str(e)}", None

def SearchImagingStudies(criteria: dict, page: int = 1, page_size: int = 10):
    try:
        query = {}
        
        if criteria.get('patient_id'):
            query["subject.reference"] = f"Patient/{criteria['patient_id']}"
        
        if criteria.get('appointment_id'):
            query["basedOn.reference"] = f"Appointment/{criteria['appointment_id']}"
        
        if criteria.get('status'):
            query["status"] = criteria['status']
        
        if criteria.get('modality'):
            query["series.modality.code"] = criteria['modality']
        
        total = collection.count_documents(query)
        studies = list(collection.find(query)
                      .skip((page - 1) * page_size)
                      .limit(page_size))
        
        for study in studies:
            study["_id"] = str(study["_id"])
            
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "results": studies
        }
    except Exception as e:
        raise HTTPException(500, f"Search failed: {str(e)}")

def UpdateImagingStudy(imaging_study_id: str, update_data: dict):
    try:
        # Validate update data
        if 'basedOn' in update_data:
            raise HTTPException(400, "No se puede modificar la referencia a la cita")
            
        # Check if ImagingStudy exists
        status, existing = GetImagingStudyById(imaging_study_id)
        if status != "success":
            raise HTTPException(404, "Estudio de imagen no encontrado")
            
        # Perform update
        result = collection.update_one(
            {"_id": ObjectId(imaging_study_id)},
            {"$set": update_data}
        )
        
        if result.modified_count == 1:
            return {"status": "success", "updated_id": imaging_study_id}
        return {"status": "no changes detected"}
        
    except Exception as e:
        raise HTTPException(500, f"Update failed: {str(e)}")