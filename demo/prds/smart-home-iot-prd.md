# Product Requirements Document: Smart Home IoT Platform

## Document Information
- **Product:** HomeHub IoT Platform API
- **Version:** 3.0
- **Date:** 2026-04-24
- **Status:** Production
- **Owner:** IoT Platform Team

---

## 1. Executive Summary

HomeHub is a unified IoT platform API that connects and controls smart home devices (lights, thermostats, cameras, locks, sensors) from multiple manufacturers. The system provides real-time device control, automation rules, energy monitoring, and security features.

### Key Objectives
- Support 100+ device types from 50+ manufacturers
- Handle 1M+ connected devices
- Sub-100ms device command latency
- 99.95% uptime for critical operations
- Zero-trust security model

---

## 2. User Personas & Access Control

### 2.1 Homeowners (Primary Users)
- **Capabilities:** Add devices, create automations, view energy data, manage user access
- **Constraints:** Must own the home (verified via account), 2FA for sensitive operations

### 2.2 Home Members (Secondary Users)
- **Capabilities:** Control devices, view status, receive alerts
- **Constraints:** Invited by homeowner, permissions managed per-device

### 2.3 Service Providers (Installers/Techs)
- **Capabilities:** Configure devices, diagnose issues, view logs
- **Constraints:** Temporary access (24-hour tokens), audit trail required

### 2.4 Third-Party Integrations
- **Capabilities:** Read device status, trigger automations (via OAuth)
- **Constraints:** Scoped permissions, rate-limited, webhook-based events

---

## 3. Device Management

### 3.1 Device Registration

**Endpoint:** `POST /devices/register`

**Business Rules:**
1. **Device Discovery**
   - Scan local network for UPnP/mDNS devices
   - Support Zigbee, Z-Wave, WiFi, Bluetooth protocols
   - Device must respond to pairing request within 30 seconds

2. **Device Metadata**
   - Manufacturer, model, firmware version required
   - Unique identifier (MAC address, serial number)
   - Device type classification (light, thermostat, camera, lock, sensor, outlet, etc.)

3. **Onboarding Flow**
   - Verify device supports HomeHub protocol (or bridge)
   - Exchange encryption keys (device certificate + platform key)
   - Assign to room/zone
   - Set friendly name (user-provided, 1-50 chars)

4. **Duplicate Detection**
   - Check if device already registered (by unique ID)
   - If duplicate: return existing device, update status to "online"

**Validation:**
- Device ID: alphanumeric, 8-64 chars
- Device type: must be from supported list (see schema)
- Network connectivity: ping device, latency <500ms
- Firmware: must be on approved version list (security)

**Expected Response:**
- HTTP 201: Device registered successfully
- HTTP 400: Invalid device type, missing required fields
- HTTP 409: Device already registered
- HTTP 422: Device unreachable, incompatible firmware

---

### 3.2 Device Control

**Endpoint:** `POST /devices/{deviceId}/commands`

**Command Types:**

**3.2.1 Smart Lights**
```json
{
  "command": "set_state",
  "parameters": {
    "power": "on" | "off",
    "brightness": 0-100,          // optional
    "color": {                     // optional
      "hue": 0-360,               // degrees
      "saturation": 0-100,        // percent
      "value": 0-100              // brightness
    },
    "temperature": 2700-6500,     // Kelvin, optional
    "transition": 0-10000         // milliseconds
  }
}
```

**Validation:**
- Brightness: 0 (off) to 100 (max), increments of 1
- Color-capable devices only: hue, saturation, temperature
- Transition: smooth fade, 0=instant, max 10 seconds

**3.2.2 Thermostats**
```json
{
  "command": "set_temperature",
  "parameters": {
    "mode": "heat" | "cool" | "auto" | "off",
    "targetTemp": 50-90,          // Fahrenheit
    "fanMode": "auto" | "on" | "circulate",
    "holdUntil": "ISO 8601 datetime" | null  // temporary override
  }
}
```

**Validation:**
- Target temp: 50-90°F (10-32°C), 0.5° increments
- Heat/cool deadband: min 2° difference
- Hold duration: max 24 hours

**3.2.3 Smart Locks**
```json
{
  "command": "set_lock",
  "parameters": {
    "state": "locked" | "unlocked",
    "userId": "uuid",             // who triggered (audit)
    "accessCode": "string",       // if using PIN, 4-8 digits
    "autoLock": boolean,          // relock after 30 seconds
    "notifyOnAccess": boolean
  }
}
```

**Validation:**
- Access code: 4-8 digit PIN, unique per user
- Biometric: fingerprint ID (device-specific)
- Audit: log every lock/unlock with timestamp, user, method

**3.2.4 Security Cameras**
```json
{
  "command": "configure_recording",
  "parameters": {
    "recordingMode": "continuous" | "motion" | "scheduled" | "off",
    "resolution": "720p" | "1080p" | "4K",
    "motionSensitivity": 0-100,
    "privacyZones": [              // areas to blur
      {"x": 0-100, "y": 0-100, "width": 1-100, "height": 1-100}
    ],
    "storageLocation": "cloud" | "local"
  }
}
```

**Validation:**
- Motion sensitivity: 0=disabled, 100=max
- Privacy zones: max 5 per camera
- Storage: cloud=7 days free, 30 days paid; local=unlimited (if NVR)

**Expected Response:**
- HTTP 200: Command sent, device acknowledged
- HTTP 202: Command queued (device offline, will execute when online)
- HTTP 400: Invalid command, unsupported parameter
- HTTP 403: Insufficient permissions
- HTTP 404: Device not found
- HTTP 408: Device timeout (no response after 5 seconds)
- HTTP 503: Device offline

---

### 3.3 Device Status

**Endpoint:** `GET /devices/{deviceId}/status`

**Real-Time Status:**
- **Power state:** on/off
- **Connectivity:** online/offline, last seen timestamp
- **Battery level:** 0-100% (if battery-powered)
- **Signal strength:** -100 to 0 dBm (WiFi/Zigbee/Z-Wave)
- **Current values:** brightness, temperature, lock state, etc.

**Telemetry Data:**
- **Energy usage:** watts (current), kWh (daily/monthly)
- **Sensor readings:** temperature, humidity, CO2, motion, door open/close
- **Diagnostic info:** firmware version, uptime, error codes

**Cache Behavior:**
- Status cached for 5 seconds (reduce device polling)
- Force refresh: `?refresh=true` (directly query device)

**Expected Response:**
- HTTP 200: Current device status
- HTTP 404: Device not found
- HTTP 503: Device offline (return last known status + offline flag)

---

## 4. Automation & Scenes

### 4.1 Create Automation Rule

**Endpoint:** `POST /automations`

**Rule Structure:**
```json
{
  "name": "Evening lights",
  "enabled": true,
  "triggers": [
    {
      "type": "time",
      "time": "sunset",           // or "HH:MM", "sunrise"
      "offset": -30               // minutes before/after
    },
    {
      "type": "device_state",
      "deviceId": "uuid",
      "condition": "motion_detected"
    },
    {
      "type": "geofence",
      "userId": "uuid",
      "location": "home",
      "event": "arrive" | "depart"
    },
    {
      "type": "sensor_threshold",
      "deviceId": "uuid",
      "metric": "temperature",
      "operator": ">",
      "value": 75
    }
  ],
  "conditions": [                  // optional AND conditions
    {
      "type": "time_window",
      "start": "18:00",
      "end": "23:00"
    },
    {
      "type": "day_of_week",
      "days": ["monday", "tuesday", "wednesday", "thursday", "friday"]
    },
    {
      "type": "device_state",
      "deviceId": "uuid",
      "state": "home" | "away" | "sleep"
    }
  ],
  "actions": [
    {
      "type": "device_command",
      "deviceId": "uuid",
      "command": "set_state",
      "parameters": {"power": "on", "brightness": 75}
    },
    {
      "type": "scene",
      "sceneId": "uuid"
    },
    {
      "type": "notification",
      "message": "Front door unlocked",
      "severity": "info" | "warning" | "critical"
    },
    {
      "type": "webhook",
      "url": "https://api.example.com/notify",
      "method": "POST",
      "headers": {},
      "body": {}
    }
  ]
}
```

**Business Rules:**
1. **Trigger Evaluation**
   - ANY trigger can start the rule (OR logic)
   - ALL conditions must be true (AND logic)
   - Re-evaluate conditions every 60 seconds

2. **Action Execution**
   - Execute actions in order (sequential)
   - If one fails, log error but continue
   - Max 20 actions per rule

3. **Rate Limiting**
   - Same rule cannot fire more than once per minute
   - Debounce motion sensors: 5-minute cooldown

4. **Priority Handling**
   - Critical rules (security) execute first
   - Normal rules queued (max 100 queued)

**Validation:**
- Name: 1-100 chars
- Triggers: 1-10 per rule
- Conditions: 0-10 per rule
- Actions: 1-20 per rule
- Webhook URLs: HTTPS only, allowlist domains

**Expected Response:**
- HTTP 201: Automation created
- HTTP 400: Invalid trigger/condition syntax
- HTTP 403: Insufficient permissions
- HTTP 422: Circular dependency detected (rule triggers itself)

---

### 4.2 Scenes

**Endpoint:** `POST /scenes`

**Scene Definition:**
```json
{
  "name": "Movie time",
  "icon": "tv",
  "devices": [
    {
      "deviceId": "uuid",
      "state": {"power": "on", "brightness": 20, "color": {"hue": 240}}
    },
    {
      "deviceId": "uuid",
      "state": {"power": "off"}
    }
  ]
}
```

**Business Rules:**
- Execute all device commands in parallel (fast activation)
- Scene activation: <500ms for all devices
- Max 50 devices per scene

**Expected Response:**
- HTTP 201: Scene created
- HTTP 400: Invalid device state

---

## 5. Energy Monitoring

### 5.1 Energy Data

**Endpoint:** `GET /energy/usage`

**Query Parameters:**
- `deviceId`: specific device (optional, default=all)
- `granularity`: minute, hour, day, month
- `startDate`: ISO 8601
- `endDate`: ISO 8601 (max 1 year range)

**Response Data:**
```json
{
  "period": {
    "start": "2026-04-01T00:00:00Z",
    "end": "2026-04-30T23:59:59Z"
  },
  "totalKwh": 450.5,
  "totalCost": 67.58,              // USD, based on rate
  "costPerKwh": 0.15,
  "devices": [
    {
      "deviceId": "uuid",
      "deviceName": "Living room AC",
      "kwh": 120.3,
      "cost": 18.05,
      "percentOfTotal": 26.7
    }
  ],
  "breakdown": {
    "heating": 180.2,
    "cooling": 120.3,
    "lighting": 50.0,
    "appliances": 100.0
  }
}
```

**Business Logic:**
- Real-time power: updated every 10 seconds
- Historical data: aggregated hourly
- Cost calculation: use utility rate API (by zip code)

---

## 6. Security & Alerts

### 6.1 Security Events

**Endpoint:** `GET /security/events`

**Event Types:**
- `door_opened`: Door/window sensor triggered
- `motion_detected`: Motion sensor activated
- `lock_accessed`: Lock unlocked (with user ID)
- `camera_motion`: Camera detected motion
- `alarm_triggered`: Security alarm activated
- `device_offline`: Critical device lost connection
- `unusual_activity`: AI-detected anomaly

**Alert Routing:**
- Push notification: mobile app (instant)
- SMS: for critical events (alarm, lock, camera)
- Email: daily digest
- Webhook: third-party integrations

**Retention:**
- Security events: 90 days
- Video recordings: 7 days (free), 30 days (paid)

---

## 7. Data Validation & Constraints

### 7.1 Device Command Validation
```
Power: "on" | "off"
Brightness: integer [0-100]
Temperature (thermostat): float [50.0-90.0] step 0.5
Temperature (color): integer [2700-6500] Kelvin
Hue: integer [0-360] degrees
Saturation: integer [0-100] percent
Lock state: "locked" | "unlocked"
PIN code: string [4-8 digits], regex: ^\d{4,8}$
```

### 7.2 Automation Constraints
```
Automation name: string [1-100 chars]
Triggers: array [1-10 items]
Conditions: array [0-10 items]
Actions: array [1-20 items]
Time: HH:MM 24-hour format, or "sunrise"/"sunset"
Offset: integer [-120 to 120] minutes
Geofence radius: integer [50-5000] meters
Sensor threshold: number (type-dependent)
```

### 7.3 Scene Constraints
```
Scene name: string [1-50 chars]
Devices per scene: integer [1-50]
Activation time: <500ms
Icon: enum [predefined list]
```

---

## 8. Performance Requirements

| Metric | Target | Measurement |
|--------|--------|-------------|
| Device Command Latency | <100ms (p95) | Command to acknowledgment |
| Device Status Query | <50ms (p95) | API response time |
| Automation Trigger Time | <200ms | Trigger to action start |
| Scene Activation | <500ms | All devices commanded |
| Concurrent Devices | 1,000,000+ | Load testing |
| Commands per Second | 10,000+ | Peak load handling |
| API Availability | 99.95% | Uptime (critical ops) |

---

## 9. Security Requirements

### 9.1 Authentication
- OAuth 2.0 + OpenID Connect
- JWT tokens (access: 1 hour, refresh: 30 days)
- 2FA required for: lock commands, security settings, user management

### 9.2 Authorization
- Role-based access control (RBAC)
  - Owner: full access
  - Admin: all except delete home
  - Member: device control only
  - Guest: read-only
- Device-level permissions (per-device access grants)

### 9.3 Encryption
- TLS 1.3 for API communication
- AES-256 for device commands (end-to-end)
- At-rest encryption for video, event logs

### 9.4 Privacy
- Video recordings: encrypted, user-controlled deletion
- Location data: anonymized after 90 days
- Sensor data: aggregated for analytics (no PII)

---

## 10. Error Handling

### 10.1 Error Response Format
```json
{
  "error": {
    "code": "DEVICE_OFFLINE",
    "message": "Unable to communicate with device",
    "details": {
      "deviceId": "uuid",
      "lastSeen": "2026-04-24T08:30:00Z",
      "suggestion": "Check device power and network connectivity"
    },
    "requestId": "uuid",
    "timestamp": "2026-04-24T10:00:00Z"
  }
}
```

### 10.2 Common Error Codes
- `DEVICE_NOT_FOUND`: Invalid device ID
- `DEVICE_OFFLINE`: Device unreachable
- `COMMAND_TIMEOUT`: Device did not acknowledge command
- `INVALID_PARAMETER`: Command parameter out of range
- `UNSUPPORTED_COMMAND`: Device doesn't support command
- `RATE_LIMIT_EXCEEDED`: Too many commands (throttled)
- `INSUFFICIENT_PERMISSIONS`: User lacks access
- `FIRMWARE_INCOMPATIBLE`: Device firmware too old
- `NETWORK_ERROR`: Platform-device communication failure

---

## 11. Integration Patterns

### 11.1 Webhooks
- User configures webhook URL
- Platform sends POST on events (device state change, automation trigger, alert)
- Signature verification (HMAC-SHA256)
- Retry logic: 3 attempts with exponential backoff

### 11.2 Voice Assistants
- Alexa: "Alexa, turn on kitchen lights"
- Google Assistant: "Hey Google, set thermostat to 72"
- Siri Shortcuts: custom scenes

### 11.3 IFTTT / Zapier
- OAuth2 integration
- Triggers: device state, automation, alert
- Actions: send command, activate scene

---

## 12. API Endpoints Summary

| Endpoint | Method | Purpose | Auth | Rate Limit |
|----------|--------|---------|------|------------|
| `/devices/register` | POST | Add device | Required | 10/min |
| `/devices` | GET | List devices | Required | 60/min |
| `/devices/{id}` | GET | Device details | Required | 120/min |
| `/devices/{id}/status` | GET | Real-time status | Required | 120/min |
| `/devices/{id}/commands` | POST | Control device | Required | 300/min |
| `/devices/{id}` | DELETE | Remove device | Required | 5/min |
| `/automations` | GET/POST | Manage rules | Required | 30/min |
| `/automations/{id}` | GET/PATCH/DELETE | Rule CRUD | Required | 30/min |
| `/scenes` | GET/POST | Manage scenes | Required | 30/min |
| `/scenes/{id}/activate` | POST | Trigger scene | Required | 60/min |
| `/energy/usage` | GET | Energy data | Required | 30/min |
| `/security/events` | GET | Event history | Required | 60/min |
| `/users/{id}/permissions` | GET/PATCH | Access control | Owner only | 20/min |

---

## 13. Edge Cases & Business Logic

### 13.1 Device Offline Handling
- Commands queued for offline devices (max 10 commands, 24-hour TTL)
- When device reconnects: execute queued commands in order
- User notified if device offline >24 hours

### 13.2 Conflicting Automations
- Priority order: security > energy-saving > convenience
- If two rules set same device to different states: last-wins
- User warning if conflict detected

### 13.3 Firmware Updates
- Auto-update: overnight (2-6 AM), non-critical devices
- Critical devices (locks, alarms): manual approval required
- Rollback if device becomes unresponsive after update

### 13.4 Network Partitioning
- Local control: devices operate on local network even if cloud unavailable
- Sync state when cloud reconnects
- Critical automations (security) run locally

---

## 14. Acceptance Criteria

### Definition of Done
✅ All device types tested (50+ models)  
✅ Command latency <100ms (p95)  
✅ Automation execution <200ms  
✅ Security events logged with audit trail  
✅ Rate limiting enforced  
✅ Error responses include actionable messages  
✅ OAuth2 integration functional  
✅ Load tested (1M devices, 10k commands/sec)  
✅ Encryption verified (penetration testing)  
✅ Documentation complete with examples  

---

*Document Version: 3.0*  
*Last Updated: 2026-04-24*  
*Prepared for: API Contract Validator Demo*
