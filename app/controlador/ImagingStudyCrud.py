from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.imagingstudy import ImagingStudy
import json

collection = connect_to_mongodb("RIS_DataBase", "ImagingStudies")


def GetImagingStudyById(study_id: str):
    try:
        study = collection.find_one({"_id": ObjectId(study_id)})
        if study:
            study["_id"] = str(study["_id"])
            return "success", study
        return "notFound", None
    except Exception as e:
        return f"notFound", None


def WriteImagingStudy(study_dict: dict):
    try:
        study = ImagingStudy.model_validate(study_dict)
    except Exception as e:
        return f"errorValidating: {str(e)}", None
    validated_study_json = study.model_dump()
    result = collection.insert_one(validated_study_json)
    if result:
        inserted_id = str(result.inserted_id)
        return "success", inserted_id
    else:
        return "errorInserting", None


def GetImagingStudyByIdentifier(studySystem, studyValue):
    try:
        study = collection.find_one({"identifier.system": studySystem, "identifier.value": studyValue})
        if study:
            study["_id"] = str(study["_id"])
            return "success", study
        return "notFound", None
    except Exception as e:
        return f"error encontrado: {str(e)}", None