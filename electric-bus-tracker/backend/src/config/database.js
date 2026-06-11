const mysql = require('mysql2/promise');

let pool;

const getPool = () => {
  if (!pool) {
    pool = mysql.createPool({
      host: process.env.DB_HOST || 'localhost',
      port: Number(process.env.DB_PORT || 3306),
      user: process.env.DB_USER || 'root',
      password: process.env.DB_PASSWORD || '',
      database: process.env.DB_NAME || 'electric_bus_tracker',
      waitForConnections: true,
      connectionLimit: Number(process.env.DB_CONNECTION_LIMIT || 10),
      queueLimit: 0,
      timezone: 'Z',
      dateStrings: true
    });
  }

  return pool;
};

const connectDB = async () => {
  const connection = await getPool().getConnection();
  try {
    await connection.ping();
    console.log('MySQL connected');
  } finally {
    connection.release();
  }
};

const query = async (sql, params = []) => {
  const [rows] = await getPool().execute(sql, params);
  return rows;
};

const callProcedure = async (name, params = []) => {
  const placeholders = params.map(() => '?').join(', ');
  const [resultSets] = await getPool().query(
    `CALL ${name}(${placeholders})`,
    params
  );
  return resultSets;
};

const firstResultSet = (resultSets) => {
  if (!Array.isArray(resultSets)) return [];
  return Array.isArray(resultSets[0]) ? resultSets[0] : resultSets;
};

module.exports = {
  connectDB,
  getPool,
  query,
  callProcedure,
  firstResultSet
};
