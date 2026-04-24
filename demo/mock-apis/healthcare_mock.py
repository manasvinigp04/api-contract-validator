"""
Healthcare Patient Management Mock API Server
Intentionally includes drift issues for ACV demo

Run: python demo/mock-apis/healthcare_mock.py
Server: http://localhost:9000
"""

from flask import Flask, jsonify, request
from datetime import datetime, timedelta
import uuid
import re

app = Flask(__name__)

# Mock data
patients_db = {}
appointments_db = {}
prescriptions_db = {}

@app.route('/v3/patients', methods=['POST'])
def register_patient():
    """Register patient - DRIFT: Weak validation"""
    data = request.get_json()

    # DRIFT: Should validate SSN format (XXX-XX-XXXX)
    # Should validate phone format (E.164)
    # Should validate email format
    # Accepts invalid SSN like "123456789" or "abc-de-fghi"

    patient_id = str(uuid.uuid4())
    mrn = f"MRN-{len(patients_db) + 1:010d}"

    patient = {
        "id": patient_id,
        "mrn": mrn,
        "firstName": data.get("firstName"),
        "lastName": data.get("lastName"),
        "dateOfBirth": data.get("dateOfBirth"),
        "ssn": data.get("ssn"),  # DRIFT: No format validation
        "email": data.get("email"),
        "phone": data.get("phone"),
        "address": data.get("address"),
        "status": "active",
        "createdAt": datetime.utcnow().isoformat() + "Z"
        # DRIFT: Missing emergencyContact, insuranceInfo, medicalHistory
    }

    patients_db[patient_id] = patient

    return jsonify(patient), 201

@app.route('/v3/patients/<patient_id>', methods=['GET'])
def get_patient(patient_id):
    """Get patient details"""
    if patient_id not in patients_db:
        return jsonify({
            "error": "not_found",
            "message": f"Patient {patient_id} not found",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 404

    return jsonify(patients_db[patient_id]), 200

@app.route('/v3/patients/<patient_id>', methods=['PATCH'])
def update_patient(patient_id):
    """Update patient"""
    if patient_id not in patients_db:
        return jsonify({
            "error": "not_found",
            "message": f"Patient {patient_id} not found",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 404

    data = request.get_json()

    # DRIFT: No validation of update fields
    patients_db[patient_id].update(data)
    patients_db[patient_id]["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    return jsonify(patients_db[patient_id]), 200

@app.route('/v3/patients/<patient_id>/medical-records', methods=['GET'])
def get_medical_records(patient_id):
    """Get medical records"""
    if patient_id not in patients_db:
        return jsonify({
            "error": "not_found",
            "message": f"Patient {patient_id} not found",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 404

    # Return mock records
    return jsonify([
        {
            "id": str(uuid.uuid4()),
            "patientId": patient_id,
            "recordType": "diagnosis",
            "recordedBy": str(uuid.uuid4()),
            "recordedAt": "2024-03-15T10:00:00Z",
            "diagnosis": {
                "code": "E11.9",  # ICD-10 code
                "description": "Type 2 diabetes mellitus without complications",
                "severity": "moderate"
                # DRIFT: Missing diagnosedDate
            }
        }
    ]), 200

@app.route('/v3/patients/<patient_id>/medical-records', methods=['POST'])
def add_medical_record(patient_id):
    """Add medical record - DRIFT: Missing validation"""
    if patient_id not in patients_db:
        return jsonify({
            "error": "not_found",
            "message": f"Patient {patient_id} not found",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 404

    data = request.get_json()

    # DRIFT: Should validate ICD-10 code format (^[A-Z][0-9]{2}(\.[0-9]{1,2})?$)
    # Should validate severity enum
    # Accepts invalid codes like "XYZ123" or "E11"

    record = {
        "id": str(uuid.uuid4()),
        "patientId": patient_id,
        "recordType": data.get("recordType"),
        "recordedBy": str(uuid.uuid4()),  # Mock doctor ID
        "recordedAt": datetime.utcnow().isoformat() + "Z"
    }

    if "diagnosis" in data:
        record["diagnosis"] = data["diagnosis"]
    if "labResult" in data:
        record["labResult"] = data["labResult"]
    if "vitals" in data:
        record["vitals"] = data["vitals"]

    return jsonify(record), 201

@app.route('/v3/appointments', methods=['GET'])
def list_appointments():
    """List appointments"""
    patient_id = request.args.get('patientId')
    from_date = request.args.get('fromDate')
    to_date = request.args.get('toDate')

    # DRIFT: Should validate fromDate/toDate are required
    # Should validate date formats

    appointments = list(appointments_db.values())

    if patient_id:
        appointments = [a for a in appointments if a["patientId"] == patient_id]

    return jsonify(appointments), 200

@app.route('/v3/appointments', methods=['POST'])
def schedule_appointment():
    """Schedule appointment - DRIFT: Weak validation"""
    data = request.get_json()

    # DRIFT: Should validate scheduledStart is future date
    # Should validate duration is 15-180 minutes
    # Should check doctor availability
    # Accepts past dates, invalid durations!

    appointment_id = str(uuid.uuid4())

    scheduled_start = data.get("scheduledStart")
    duration = data.get("duration", 30)

    # DRIFT: No validation that scheduledStart is in the future
    # DRIFT: No validation of duration range

    try:
        start_dt = datetime.fromisoformat(scheduled_start.replace('Z', '+00:00'))
        end_dt = start_dt + timedelta(minutes=duration)
    except:
        # DRIFT: Should return 400 for invalid date format
        start_dt = datetime.utcnow()
        end_dt = start_dt + timedelta(minutes=30)

    appointment = {
        "id": appointment_id,
        "patientId": data.get("patientId"),
        "doctorId": data.get("doctorId"),
        "appointmentType": data.get("appointmentType"),
        "scheduledStart": start_dt.isoformat() + "Z",
        "scheduledEnd": end_dt.isoformat() + "Z",
        "status": "scheduled",
        "createdAt": datetime.utcnow().isoformat() + "Z"
        # DRIFT: Missing location, reason, telemedicineLink
    }

    appointments_db[appointment_id] = appointment

    return jsonify(appointment), 201

@app.route('/v3/appointments/<appointment_id>', methods=['GET'])
def get_appointment(appointment_id):
    """Get appointment"""
    if appointment_id not in appointments_db:
        return jsonify({
            "error": "not_found",
            "message": f"Appointment {appointment_id} not found",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 404

    return jsonify(appointments_db[appointment_id]), 200

@app.route('/v3/appointments/<appointment_id>', methods=['PATCH'])
def update_appointment(appointment_id):
    """Update appointment"""
    if appointment_id not in appointments_db:
        return jsonify({
            "error": "not_found",
            "message": f"Appointment {appointment_id} not found",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 404

    data = request.get_json()

    # DRIFT: No validation
    appointments_db[appointment_id].update(data)
    appointments_db[appointment_id]["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    return jsonify(appointments_db[appointment_id]), 200

@app.route('/v3/appointments/<appointment_id>/notes', methods=['POST'])
def add_clinical_notes(appointment_id):
    """Add clinical notes - SECURITY DRIFT: No XSS sanitization!"""
    if appointment_id not in appointments_db:
        return jsonify({
            "error": "not_found",
            "message": f"Appointment {appointment_id} not found",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 404

    data = request.get_json()

    # SECURITY DRIFT: Should sanitize notes for XSS
    # Accepts: <script>alert('xss')</script>
    # Should validate minLength: 10, maxLength: 10000

    notes = data.get("notes", "")

    appointments_db[appointment_id]["clinicalNotes"] = notes  # Raw, unsanitized!
    appointments_db[appointment_id]["updatedAt"] = datetime.utcnow().isoformat() + "Z"

    return jsonify(appointments_db[appointment_id]), 201

@app.route('/v3/prescriptions', methods=['GET'])
def list_prescriptions():
    """List prescriptions"""
    patient_id = request.args.get('patientId')

    if not patient_id:
        return jsonify({
            "error": "bad_request",
            "message": "patientId is required",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 400

    prescriptions = [p for p in prescriptions_db.values() if p["patientId"] == patient_id]

    return jsonify(prescriptions), 200

@app.route('/v3/prescriptions', methods=['POST'])
def create_prescription():
    """Create prescription - DRIFT: Missing validation"""
    data = request.get_json()

    # DRIFT: Should validate NDC code format (XXXXX-XXXX-XX)
    # Should validate dosage pattern
    # Should validate DEA schedule for controlled substances
    # Should validate duration 1-365 days
    # Accepts invalid NDC codes, wrong dosage formats!

    prescription_id = str(uuid.uuid4())

    start_date = data.get("startDate")
    duration = data.get("duration", 30)

    try:
        start_dt = datetime.fromisoformat(start_date)
        end_dt = start_dt + timedelta(days=duration)
    except:
        start_dt = datetime.utcnow()
        end_dt = start_dt + timedelta(days=30)

    prescription = {
        "id": prescription_id,
        "patientId": data.get("patientId"),
        "doctorId": str(uuid.uuid4()),  # Mock
        "medication": data.get("medication"),  # DRIFT: No NDC validation
        "dosage": data.get("dosage"),  # DRIFT: No pattern validation
        "frequency": data.get("frequency"),
        "route": data.get("route"),
        "startDate": start_dt.date().isoformat(),
        "endDate": end_dt.date().isoformat(),
        "refillsRemaining": data.get("refills", 0),
        "status": "active",
        "createdAt": datetime.utcnow().isoformat() + "Z"
    }

    prescriptions_db[prescription_id] = prescription

    return jsonify(prescription), 201

@app.route('/v3/prescriptions/<prescription_id>', methods=['GET'])
def get_prescription(prescription_id):
    """Get prescription"""
    if prescription_id not in prescriptions_db:
        return jsonify({
            "error": "not_found",
            "message": f"Prescription {prescription_id} not found",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 404

    return jsonify(prescriptions_db[prescription_id]), 200

@app.route('/v3/doctors', methods=['GET'])
def list_doctors():
    """List doctors"""
    return jsonify([
        {
            "id": str(uuid.uuid4()),
            "firstName": "Sarah",
            "lastName": "Johnson",
            "specialty": "cardiology",
            "licenseNumber": "CA-123456",
            "npiNumber": "1234567890",
            "phone": "+15551234567",
            "email": "sarah.johnson@hospital.example.com"
        },
        {
            "id": str(uuid.uuid4()),
            "firstName": "Michael",
            "lastName": "Chen",
            "specialty": "pediatrics",
            "licenseNumber": "CA-789012",
            "npiNumber": "0987654321",
            "phone": "+15559876543",
            "email": "michael.chen@hospital.example.com"
        }
    ]), 200

@app.route('/v3/doctors/<doctor_id>/availability', methods=['GET'])
def get_doctor_availability(doctor_id):
    """Get doctor availability"""
    date_param = request.args.get('date')

    if not date_param:
        return jsonify({
            "error": "bad_request",
            "message": "date parameter is required",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 400

    # Mock availability
    try:
        date = datetime.fromisoformat(date_param)
        slots = []

        for hour in range(9, 17):  # 9 AM to 5 PM
            start = date.replace(hour=hour, minute=0, second=0)
            end = start + timedelta(minutes=30)
            slots.append({
                "start": start.isoformat() + "Z",
                "end": end.isoformat() + "Z",
                "available": hour % 2 == 0  # Mock: every other slot available
            })

        return jsonify(slots), 200

    except:
        return jsonify({
            "error": "bad_request",
            "message": "Invalid date format",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }), 400

if __name__ == '__main__':
    print("=" * 60)
    print("Healthcare Patient Management Mock API Server")
    print("=" * 60)
    print("Server: http://localhost:9000")
    print("Base URL: http://localhost:9000/v3")
    print()
    print("Intentional drift issues for ACV demo:")
    print("  - Missing SSN format validation (XXX-XX-XXXX)")
    print("  - Missing ICD-10 code validation")
    print("  - Missing NDC code validation")
    print("  - Accepts past dates for future appointments")
    print("  - XSS vulnerability in clinical notes")
    print("  - Missing required fields in responses")
    print("  - Weak validation on medical data")
    print()
    print("Endpoints:")
    print("  POST   /v3/patients")
    print("  GET    /v3/patients/{id}")
    print("  PATCH  /v3/patients/{id}")
    print("  GET    /v3/patients/{id}/medical-records")
    print("  POST   /v3/patients/{id}/medical-records")
    print("  GET    /v3/appointments")
    print("  POST   /v3/appointments")
    print("  GET    /v3/appointments/{id}")
    print("  PATCH  /v3/appointments/{id}")
    print("  POST   /v3/appointments/{id}/notes")
    print("  GET    /v3/prescriptions")
    print("  POST   /v3/prescriptions")
    print("  GET    /v3/prescriptions/{id}")
    print("  GET    /v3/doctors")
    print("  GET    /v3/doctors/{id}/availability")
    print("=" * 60)
    print()

    app.run(host='localhost', port=9000, debug=False)
