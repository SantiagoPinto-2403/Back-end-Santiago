from connection import connect_to_mongodb
from bson import ObjectId
from fhir.resources.appointment import Appointment
from fhir.resources.servicerequest import ServiceRequest
import json
from datetime import datetime

collection = connect_to_mongodb("RIS_DataBase", "Appointment")
service_request_collection = connect_to_mongodb("RIS_DataBase", "ServiceRequest")

def GetAppointmentById(appointment_id: str):
    try:
        appointment = appointment_collection.find_one({"_id": ObjectId(appointment_id)})
        if appointment:
            appointment["_id"] = str(appointment["_id"])
            return "success", appointment
        return "notFound", None
    except Exception as e:
        return f"error: {str(e)}", None

def WriteAppointment(appointment_dict: dict):
    try:
        # Validate required fields
        if not all(k in appointment_dict for k in ["status", "start", "participant"]):
            return "error: Missing required fields", None
            
        # Check for existing appointment
        existing = appointment_collection.find_one({
            "start": appointment_dict["start"],
            "participant.actor.identifier.value": appointment_dict["participant"][0]["actor"]["identifier"]["value"]
        })
        if existing:
            return "error: Appointment already exists", None
            
        result = appointment_collection.insert_one(appointment_dict)
        return "success", str(result.inserted_id)
    except Exception as e:
        return f"error: {str(e)}", None
