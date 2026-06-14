# Electric Bus Tracker

Flutter + Node/Express + MySQL implementation for the Electric Bus Tracker project.

## What Is Included

- Passenger route search, local favourites, live bus tracking, and estimated arrival screen.
- Driver login, profile, daily duty, monthly schedule, duty start/end, and GPS publishing.
- Admin dashboard, driver management, route management, duty management, and PDF reports.
- MySQL schema, minimal admin seed, views, triggers, and stored procedures in `dbDDL.sql` and `dbDML.sql`.
- No Google Maps API dependency. The app uses OpenStreetMap tiles through Flutter map widgets.

## Database Setup

The DDL recreates the database, so review before running it against an existing MySQL instance.

```bash
mysql -u root -p < dbDDL.sql
mysql -u root -p < dbDML.sql
```

Default database name: `electric_bus_tracker`

## Backend Setup

```bash
cd backend
npm install
```

Create `backend/.env`:

```env
PORT=5000
NODE_ENV=development
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=
DB_NAME=electric_bus_tracker
JWT_SECRET=replace_this_with_a_long_secret
JWT_EXPIRE=7d
DISABLE_REPORT_SCHEDULER=true
```

Start the API:

```bash
npm run dev
```

## Mobile Setup

```bash
cd mobile
flutter pub get
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:5000/api
```

For a physical phone, replace `10.0.2.2` with your computer LAN IP.
For AWS, replace it with your deployed backend URL.

## Initial Login

- Admin: username `admin_main`, user ID `ADM-001`, password `admin123`

Drivers, buses, routes, duties, and stops are now created from inside the admin app.

## Notes

- Password reset codes print to the backend console in development if SendGrid is not configured.
- Reports are generated as PDFs under `backend/reports`.
- Passenger favourites are stored locally on the device because the current ERD has no passenger account table.
