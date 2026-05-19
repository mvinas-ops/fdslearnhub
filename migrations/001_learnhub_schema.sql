-- LearnHub schema migration aligned with the SQLAlchemy models in app/models.py.
-- Optional: the app can also auto-create tables on startup. Use this file if you prefer manual DB migration.
-- Run in psql: psql -U postgres -d learnhub -f migrations/001_learnhub_schema.sql

CREATE TABLE IF NOT EXISTS permissions (
  id SERIAL PRIMARY KEY,
  key VARCHAR(100) UNIQUE NOT NULL,
  name VARCHAR(150) NOT NULL,
  module VARCHAR(100),
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS roles (
  id SERIAL PRIMARY KEY,
  name VARCHAR(100) UNIQUE NOT NULL,
  slug VARCHAR(100) UNIQUE NOT NULL,
  description TEXT,
  color VARCHAR(30) DEFAULT 'blue',
  is_system_role BOOLEAN DEFAULT FALSE NOT NULL,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS role_permissions (
  id SERIAL PRIMARY KEY,
  role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
  permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
  CONSTRAINT uq_role_permission UNIQUE(role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS barangays (
  id SERIAL PRIMARY KEY,
  name VARCHAR(150) UNIQUE NOT NULL,
  psgc VARCHAR(32),
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
  id SERIAL PRIMARY KEY,
  full_name VARCHAR(255) NOT NULL DEFAULT 'Unnamed User',
  email VARCHAR(255) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  role VARCHAR(50) DEFAULT 'trainee',
  role_id INTEGER REFERENCES roles(id),
  barangay_id INTEGER REFERENCES barangays(id),
  phone VARCHAR(50),
  psgc VARCHAR(32),
  status VARCHAR(30) DEFAULT 'active',
  is_active BOOLEAN DEFAULT TRUE NOT NULL,
  refresh_token VARCHAR(2048),
  refresh_token_expiry TIMESTAMP,
  last_login TIMESTAMP,
  reset_token VARCHAR(255),
  reset_token_expiry TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS cml_barangays (
  id SERIAL PRIMARY KEY,
  cml_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  barangay_id INTEGER NOT NULL REFERENCES barangays(id) ON DELETE CASCADE,
  CONSTRAINT uq_cml_barangay UNIQUE(cml_user_id, barangay_id)
);

CREATE TABLE IF NOT EXISTS training_materials (
  id SERIAL PRIMARY KEY,
  title VARCHAR(255) NOT NULL,
  slug VARCHAR(255) UNIQUE NOT NULL,
  description TEXT,
  category VARCHAR(100),
  number_of_lessons INTEGER DEFAULT 0,
  total_duration VARCHAR(80),
  status VARCHAR(30) DEFAULT 'active',
  created_by_id INTEGER REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS lessons (
  id SERIAL PRIMARY KEY,
  material_id INTEGER NOT NULL REFERENCES training_materials(id) ON DELETE CASCADE,
  lesson_number INTEGER NOT NULL,
  title VARCHAR(255) NOT NULL,
  duration_minutes INTEGER DEFAULT 0,
  order_index INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT uq_material_lesson_number UNIQUE(material_id, lesson_number)
);

CREATE TABLE IF NOT EXISTS resources (
  id SERIAL PRIMARY KEY,
  material_id INTEGER NOT NULL REFERENCES training_materials(id) ON DELETE CASCADE,
  file_name VARCHAR(255) NOT NULL,
  stored_file_name VARCHAR(255),
  file_type VARCHAR(20) NOT NULL,
  file_size INTEGER DEFAULT 0,
  file_path VARCHAR(500),
  uploaded_by_id INTEGER REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS schedules (
  id SERIAL PRIMARY KEY,
  material_id INTEGER REFERENCES training_materials(id),
  session_title VARCHAR(255) NOT NULL,
  session_date DATE NOT NULL,
  session_time VARCHAR(10) NOT NULL,
  location VARCHAR(255),
  barangay_id INTEGER NOT NULL REFERENCES barangays(id),
  status VARCHAR(30) DEFAULT 'upcoming',
  created_by_id INTEGER REFERENCES users(id),
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE TABLE IF NOT EXISTS schedule_participants (
  id SERIAL PRIMARY KEY,
  schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  attendance_status VARCHAR(30) DEFAULT 'pending',
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT uq_schedule_participant UNIQUE(schedule_id, user_id)
);

CREATE TABLE IF NOT EXISTS user_sessions (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  schedule_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
  status VARCHAR(30) DEFAULT 'assigned',
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT uq_user_session UNIQUE(user_id, schedule_id)
);

CREATE TABLE IF NOT EXISTS session_material_mappings (
  id SERIAL PRIMARY KEY,
  session_id INTEGER NOT NULL REFERENCES schedules(id) ON DELETE CASCADE,
  material_id INTEGER NOT NULL REFERENCES training_materials(id) ON DELETE CASCADE,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT uq_session_material UNIQUE(session_id, material_id)
);

CREATE TABLE IF NOT EXISTS lesson_progress (
  id SERIAL PRIMARY KEY,
  user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  lesson_id INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
  is_completed BOOLEAN DEFAULT FALSE NOT NULL,
  completed_at TIMESTAMP,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  CONSTRAINT uq_user_lesson_progress UNIQUE(user_id, lesson_id)
);

CREATE TABLE IF NOT EXISTS audit_logs (
  id SERIAL PRIMARY KEY,
  actor_user_id INTEGER REFERENCES users(id),
  action VARCHAR(100) NOT NULL,
  entity VARCHAR(100) NOT NULL,
  entity_id INTEGER,
  details TEXT,
  created_at TIMESTAMPTZ DEFAULT now() NOT NULL,
  updated_at TIMESTAMPTZ DEFAULT now() NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_users_role_status ON users(role, status);
CREATE INDEX IF NOT EXISTS idx_users_barangay ON users(barangay_id);
CREATE INDEX IF NOT EXISTS idx_materials_status_category ON training_materials(status, category);
CREATE INDEX IF NOT EXISTS idx_schedules_barangay_date ON schedules(barangay_id, session_date);
CREATE INDEX IF NOT EXISTS idx_participants_user_status ON schedule_participants(user_id, attendance_status);


CREATE TABLE IF NOT EXISTS client_groups (
    id SERIAL PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    description TEXT,
    barangay_id INTEGER REFERENCES barangays(id),
    status VARCHAR(30) DEFAULT 'active',
    created_by_id INTEGER REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL
);

CREATE TABLE IF NOT EXISTS client_group_members (
    id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES client_groups(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW() NOT NULL,
    CONSTRAINT uq_client_group_member UNIQUE(group_id, user_id)
);
CREATE INDEX IF NOT EXISTS ix_client_groups_barangay_id ON client_groups(barangay_id);
CREATE INDEX IF NOT EXISTS ix_client_group_members_group_id ON client_group_members(group_id);
CREATE INDEX IF NOT EXISTS ix_client_group_members_user_id ON client_group_members(user_id);
