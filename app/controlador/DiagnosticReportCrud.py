from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.diagnosticreport import DiagnosticReport
import json

collection = connect_to_mongodb("RIS_DataBase", "DiagnosticReport")


def GetDiagnosticReportById(report_id: str):
    try:
        diagnostic_report = collection.find_one({"_id": ObjectId(report_id)})
        if diagnostic_report:
            diagnostic_report["_id"] = str(diagnostic_report["_id"])
            return "success", diagnostic_report
        return "notFound", None
    except Exception as e:
        return f"notFound", None


def WriteDiagnosticReport(diagnostic_report_dict: dict):
    try:
        report = DiagnosticReport.model_validate(diagnostic_report_dict)
    except Exception as e:
        return f"errorValidating: {str(e)}", None
    validated_diagnostic_report_json = report.model_dump()
    result = collection.insert_one(validated_diagnostic_report_dic)
    if result:
        inserted_id = str(result.inserted_id)
        return "success", inserted_id
    else:
        return "errorInserting", None


def GetDiagnosticReportByIdentifier(reportSystem, reportValue):
    try:
        diagnostic_report = collection.find_one({"identifier.system": reportSystem, "identifier.value": reportValue})
        if diagnostic_report:
            diagnostic_report["_id"] = str(diagnostic_report["_id"])
            return "success", diagnostic_report
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None