from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.appointment import Appointment
import json

collection = connect_to_mongodb("RIS_DataBase", "Appointment")

def GetAppointmentById(appointment_id: str):
    try:
        appointment = collection.find_one({"_id": ObjectId(appointment_id)})
        if appointment:
            appointment["_id"] = str(appointment["_id"])
            return "success", appointment
        return "notFound", None
    except Exception as e:
        return f"notFound", None

def WriteAppointment(appointment_dict: dict):
    try:
        appt = Appointment.model_validate(appointment_dict)
    except Exception as e:
        return f"errorValidating: {str(e)}",None
    validated_appointment_json = appt.model_dump()
    result = collection.insert_one(appointment_dict)
    if result:
        inserted_id = str(result.inserted_id)
        return "success",inserted_id
    else:
        return "errorInserting", None

def GetAppointmentByIdentifier(appointmentSystem, appointmentValue):
    try:
        appointment = collection.find_one({"identifier.system": appointmentSystem, "identifier.value": appointmentValue})
        if appointment:
            appointment["_id"] = str(appointment["_id"])
            return "success", appointment
        return "notFound", None
    except Exception as e:
        return f"error encontrado: {str(e)}", None