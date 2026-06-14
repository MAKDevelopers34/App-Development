const { query } = require('../config/database');

const GRACE_MINUTES = 25;

const refreshDutyStatuses = async () => {
  await query(
    `UPDATE duty_assignments
     SET status = 'Skipped',
         completion_note = COALESCE(
           completion_note,
           'Auto-marked skipped after 25 minute start grace'
         )
     WHERE status = 'Scheduled'
       AND NOW() >= DATE_ADD(
         TIMESTAMP(scheduled_date, scheduled_start_time),
         INTERVAL ${GRACE_MINUTES} MINUTE
       )`
  );

  await query(
    `UPDATE bus_locations bl
     JOIN duty_assignments da ON da.duty_id = bl.duty_id
     SET bl.is_active = FALSE
     WHERE bl.is_active = TRUE
       AND da.status IN ('Completed', 'Skipped')`
  );
};

module.exports = {
  GRACE_MINUTES,
  refreshDutyStatuses
};
