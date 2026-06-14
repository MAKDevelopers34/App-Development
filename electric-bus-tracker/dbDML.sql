USE electric_bus_tracker;

-- Final production seed data.
-- Default admin login:
--   username: admin_main
--   user ID: ADM-001
--   email: admin@electricbus.pk
--   password: admin123
-- The password is stored below as a bcrypt hash, not as plain text.

INSERT INTO users (
  username,
  user_code,
  name,
  email,
  contact,
  password_hash,
  role,
  account_status
)
VALUES (
  'admin_main',
  'ADM-001',
  'Admin User',
  'admin@electricbus.pk',
  '+923001110001',
  '$2b$10$wgGNhoHm9kodolvQx690HulzyWqLcGhblFPxoPvNXXSvFR68pHTfi',
  'Admin',
  'Active'
)
ON DUPLICATE KEY UPDATE
  user_code = VALUES(user_code),
  name = VALUES(name),
  email = VALUES(email),
  contact = VALUES(contact),
  password_hash = VALUES(password_hash),
  role = VALUES(role),
  account_status = VALUES(account_status),
  deletion_date = NULL;

INSERT INTO admins (user_id)
SELECT user_id
FROM users
WHERE username = 'admin_main'
  AND role = 'Admin'
ON DUPLICATE KEY UPDATE
  user_id = VALUES(user_id);
