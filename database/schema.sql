-- 课堂学情监控管理系统：完整数据库结构
-- 技术栈：SQLite。此脚本可单独导入，用于创建全部业务表和索引。

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    role VARCHAR(20) NOT NULL
        CONSTRAINT ck_users_role
        CHECK (role IN ('student', 'teacher', 'admin')),
    username VARCHAR(50) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    student_no VARCHAR(30) UNIQUE,
    name VARCHAR(50) NOT NULL,
    age INTEGER
        CONSTRAINT ck_users_age
        CHECK (age IS NULL OR (age >= 1 AND age <= 120)),
    gender VARCHAR(20),
    grade VARCHAR(30),
    class_name VARCHAR(100),
    major VARCHAR(100),
    phone VARCHAR(30) NOT NULL UNIQUE,
    wechat_openid VARCHAR(100) UNIQUE,
    qq_openid VARCHAR(100) UNIQUE,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CONSTRAINT ck_users_status
        CHECK (status IN ('active', 'disabled')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_student_required_fields CHECK (
        role != 'student'
        OR (
            student_no IS NOT NULL
            AND grade IS NOT NULL
            AND class_name IS NOT NULL
            AND major IS NOT NULL
        )
    )
);

CREATE INDEX IF NOT EXISTS ix_users_role ON users (role);
CREATE INDEX IF NOT EXISTS ix_users_class_name ON users (class_name);

CREATE TABLE IF NOT EXISTS login_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    expires_at DATETIME NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_login_sessions_user_id
    ON login_sessions (user_id);
CREATE INDEX IF NOT EXISTS ix_login_sessions_expires_at
    ON login_sessions (expires_at);

CREATE TABLE IF NOT EXISTS sms_verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    code_hash VARCHAR(255) NOT NULL,
    expires_at DATETIME NOT NULL,
    used_at DATETIME,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_sms_codes_user_created
    ON sms_verification_codes (user_id, created_at);
CREATE INDEX IF NOT EXISTS ix_sms_codes_expires_at
    ON sms_verification_codes (expires_at);

CREATE TABLE IF NOT EXISTS courses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    teacher_id INTEGER NOT NULL,
    description TEXT,
    status VARCHAR(20) NOT NULL DEFAULT 'active'
        CONSTRAINT ck_courses_status
        CHECK (status IN ('active', 'inactive')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_courses_teacher_id ON courses (teacher_id);

CREATE TABLE IF NOT EXISTS course_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    course_id INTEGER NOT NULL,
    class_name VARCHAR(100) NOT NULL,
    topic VARCHAR(200) NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME,
    status VARCHAR(20) NOT NULL DEFAULT 'scheduled'
        CONSTRAINT ck_course_sessions_status
        CHECK (status IN ('scheduled', 'active', 'finished')),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (course_id) REFERENCES courses (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_course_sessions_course_id
    ON course_sessions (course_id);
CREATE INDEX IF NOT EXISTS ix_course_sessions_class_status
    ON course_sessions (class_name, status);
CREATE INDEX IF NOT EXISTS ix_course_sessions_start_time
    ON course_sessions (start_time);

CREATE TABLE IF NOT EXISTS feedback_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    score INTEGER NOT NULL
        CONSTRAINT ck_feedback_score
        CHECK (score >= 1 AND score <= 6),
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES course_sessions (id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_feedback_session_time
    ON feedback_records (session_id, submitted_at);
CREATE INDEX IF NOT EXISTS ix_feedback_student_session_time
    ON feedback_records (student_id, session_id, submitted_at);

CREATE TABLE IF NOT EXISTS statistics_settings (
    id INTEGER PRIMARY KEY,
    interval_minutes INTEGER NOT NULL DEFAULT 5
        CONSTRAINT ck_statistics_interval
        CHECK (interval_minutes >= 5 AND interval_minutes <= 10),
    updated_by INTEGER NOT NULL,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (updated_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS statistics_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    interval_minutes INTEGER NOT NULL
        CONSTRAINT ck_snapshot_interval
        CHECK (interval_minutes >= 5 AND interval_minutes <= 10),
    period_start DATETIME NOT NULL,
    period_end DATETIME NOT NULL,
    total_students INTEGER NOT NULL DEFAULT 0,
    score_1_count INTEGER NOT NULL DEFAULT 0,
    score_2_count INTEGER NOT NULL DEFAULT 0,
    score_3_count INTEGER NOT NULL DEFAULT 0,
    score_4_count INTEGER NOT NULL DEFAULT 0,
    score_5_count INTEGER NOT NULL DEFAULT 0,
    score_6_count INTEGER NOT NULL DEFAULT 0,
    average_score REAL NOT NULL DEFAULT 0,
    variance REAL NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_snapshot_period CHECK (period_end > period_start),
    CONSTRAINT ck_snapshot_total_count CHECK (
        total_students = score_1_count + score_2_count + score_3_count
            + score_4_count + score_5_count + score_6_count
    ),
    CONSTRAINT ck_snapshot_average_score CHECK (
        average_score >= 0 AND average_score <= 6
    ),
    CONSTRAINT ck_snapshot_variance CHECK (variance >= 0),
    CONSTRAINT uq_snapshot_session_period_interval UNIQUE (
        session_id, period_start, interval_minutes
    ),
    FOREIGN KEY (session_id) REFERENCES course_sessions (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_snapshots_session_period
    ON statistics_snapshots (session_id, period_start);

CREATE TABLE IF NOT EXISTS discussion_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    content TEXT,
    image_path VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_discussion_message_content CHECK (
        (content IS NOT NULL AND length(trim(content)) > 0)
        OR image_path IS NOT NULL
    ),
    FOREIGN KEY (session_id) REFERENCES course_sessions (id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_discussion_session_id
    ON discussion_messages (session_id, id);
CREATE INDEX IF NOT EXISTS ix_discussion_user_id
    ON discussion_messages (user_id);

CREATE TABLE IF NOT EXISTS learning_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    latest_feedback_id INTEGER NOT NULL UNIQUE,
    latest_score INTEGER NOT NULL
        CONSTRAINT ck_learning_alerts_score
        CHECK (latest_score IN (1, 2)),
    status VARCHAR(20) NOT NULL DEFAULT 'pending'
        CONSTRAINT ck_learning_alerts_status
        CHECK (status IN ('pending', 'resolved')),
    teacher_note TEXT,
    handled_by INTEGER,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resolved_at DATETIME,
    CONSTRAINT ck_learning_alerts_teacher_note CHECK (
        teacher_note IS NULL
        OR (length(trim(teacher_note)) >= 1 AND length(teacher_note) <= 500)
    ),
    CONSTRAINT ck_learning_alerts_resolution CHECK (
        (
            status = 'pending'
            AND teacher_note IS NULL
            AND handled_by IS NULL
            AND resolved_at IS NULL
        )
        OR (
            status = 'resolved'
            AND teacher_note IS NOT NULL
            AND handled_by IS NOT NULL
            AND resolved_at IS NOT NULL
        )
    ),
    FOREIGN KEY (session_id) REFERENCES course_sessions (id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (latest_feedback_id) REFERENCES feedback_records (id) ON DELETE RESTRICT,
    FOREIGN KEY (handled_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_learning_alerts_session_status
    ON learning_alerts (session_id, status);
CREATE INDEX IF NOT EXISTS ix_learning_alerts_student_created
    ON learning_alerts (student_id, created_at);
CREATE INDEX IF NOT EXISTS ix_learning_alerts_handled_by
    ON learning_alerts (handled_by);
