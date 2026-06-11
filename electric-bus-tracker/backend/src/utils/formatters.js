const asDate = (value) => {
  if (!value) return null;
  return value instanceof Date ? value.toISOString() : value;
};

const formatRoute = (row, stops = [], schedules = []) => ({
  routeId: String(row.route_id),
  routeCode: row.route_code,
  routeName: row.name,
  startPoint: {
    name: row.starting_point,
    latitude: Number(row.start_latitude),
    longitude: Number(row.start_longitude)
  },
  endPoint: {
    name: row.destination_point,
    latitude: Number(row.destination_latitude),
    longitude: Number(row.destination_longitude)
  },
  stops,
  totalDistance: Number(row.distance || 0),
  estimatedTotalTime: Number(row.estimated_duration || 0),
  schedule: schedules,
  status: row.status,
  stopCount: Number(row.stop_count || stops.length || 0)
});

const formatStop = (row) => ({
  stopId: String(row.stop_id),
  stopCode: row.stop_code,
  name: row.name,
  latitude: Number(row.latitude),
  longitude: Number(row.longitude),
  order: Number(row.stop_order || 0),
  distanceFromStart: Number(row.distance_from_start || 0),
  estimatedMinutesFromStart: Number(row.estimated_minutes_from_start || 0),
  arrivalTimes: []
});

const formatSchedule = (row) => ({
  scheduleId: row.schedule_id,
  busId: row.bus_id,
  departureTime: String(row.departure_time).slice(0, 5),
  arrivalTime: String(row.arrival_time).slice(0, 5),
  date: asDate(row.service_date),
  status: row.status
});

const formatDriver = (row) => ({
  _id: row.driver_id,
  driverId: row.driver_id,
  userDbId: row.user_id,
  username: row.username,
  userId: row.user_code,
  email: row.email,
  isActive: row.account_status === 'Active',
  status: row.driver_status,
  profileInfo: {
    fullName: row.name,
    phone: row.contact,
    licenseNo: row.license_no,
    hireDate: asDate(row.hire_date)
  }
});

const formatBus = (row) => ({
  _id: row.bus_id,
  busId: row.bus_id,
  busNumber: row.bus_number,
  capacity: row.capacity,
  model: row.model,
  status: String(row.status || '').toLowerCase(),
  registrationDate: asDate(row.registration_date)
});

const formatDuty = (row) => ({
  _id: row.duty_id,
  dutyId: row.duty_id,
  driver: row.driver_id ? {
    driverId: row.driver_id,
    username: row.driver_username || row.driver_name,
    profileInfo: { fullName: row.driver_name }
  } : null,
  bus: row.bus_id ? {
    busId: row.bus_id,
    busNumber: row.bus_number
  } : null,
  route: row.route_name,
  routeId: row.route_id,
  scheduledDate: asDate(row.scheduled_date),
  scheduledStartTime: String(row.scheduled_start_time || '').slice(0, 5),
  scheduledEndTime: String(row.scheduled_end_time || '').slice(0, 5),
  actualStartTime: asDate(row.actual_start_time),
  actualEndTime: asDate(row.actual_end_time),
  status: String(row.status || '').toLowerCase().replace('in-progress', 'started'),
  completionNote: row.completion_note
});

const formatLocation = (row) => ({
  locationId: row.location_id,
  busId: String(row.bus_id),
  busNumber: row.bus_number,
  driverId: row.driver_id,
  driverName: row.driver_name,
  routeId: String(row.route_id),
  routeName: row.route_name,
  dutyId: row.duty_id,
  location: {
    latitude: Number(row.latitude),
    longitude: Number(row.longitude)
  },
  speed: Number(row.speed || 0),
  isActive: true,
  timestamp: asDate(row.recorded_at)
});

const formatReport = (row) => ({
  reportId: row.report_code,
  dbReportId: row.report_id,
  type: row.type,
  generatedAt: asDate(row.generated_at),
  periodStart: asDate(row.period_start),
  periodEnd: asDate(row.period_end),
  adminName: row.admin_name,
  data: {
    totalDuties: Number(row.total_duties || 0),
    completedDuties: Number(row.completed_duties || 0),
    skippedDuties: Number(row.skipped_duties || 0),
    totalBuses: Number(row.total_buses || 0),
    totalDrivers: Number(row.total_drivers || 0),
    activeDrivers: Number(row.active_drivers || 0)
  },
  pdfPath: row.pdf_path,
  description: row.description
});

module.exports = {
  formatRoute,
  formatStop,
  formatSchedule,
  formatDriver,
  formatBus,
  formatDuty,
  formatLocation,
  formatReport
};
