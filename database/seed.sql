-- 三类测试账号的密码均为 123456。
-- password_hash 保存的是 PBKDF2-SHA256 散列，不是明文密码。

INSERT OR IGNORE INTO users (
    role, username, password_hash, student_no, name, age, gender,
    grade, class_name, major, phone, wechat_openid, status
) VALUES (
    'student',
    'student001',
    'pbkdf2_sha256$260000$11111111111111111111111111111111$ff12dc58cdc005105f473fe16bfa64ecee20fe9b7cea8784789cadb0ad7d18c5',
    '20260001',
    '张三',
    20,
    '男',
    '2026级',
    '软件工程1班',
    '软件工程',
    '13800000001',
    'wechat_demo_student001',
    'active'
);

-- 第二名学生让教师端统计、图表和 200 人并发以外的常规演示更直观。
INSERT OR IGNORE INTO users (
    role, username, password_hash, student_no, name, age, gender,
    grade, class_name, major, phone, status
) VALUES (
    'student',
    'student002',
    'pbkdf2_sha256$260000$11111111111111111111111111111111$ff12dc58cdc005105f473fe16bfa64ecee20fe9b7cea8784789cadb0ad7d18c5',
    '20260002',
    '李四',
    20,
    '女',
    '2026级',
    '软件工程1班',
    '软件工程',
    '13800000004',
    'active'
);

INSERT OR IGNORE INTO users (
    role, username, password_hash, name, age, gender, phone, qq_openid, status
) VALUES (
    'teacher',
    'teacher001',
    'pbkdf2_sha256$260000$22222222222222222222222222222222$9adf2483e6c54385af81b13ed8157fb8b013b7a967c417fcfe0d7ece5e6173c3',
    '李老师',
    35,
    '女',
    '13800000002',
    'qq_demo_teacher001',
    'active'
);

INSERT OR IGNORE INTO users (
    role, username, password_hash, name, age, gender, phone, status
) VALUES (
    'admin',
    'admin001',
    'pbkdf2_sha256$260000$33333333333333333333333333333333$c2a83c6f7f9aac561d0e63df1351b706078fe8377d1ed19586a2235dd56b0caa',
    '系统管理员',
    30,
    '男',
    '13800000003',
    'active'
);

-- 如果账号由旧版初始化脚本创建，则只补齐尚未设置的本地第三方演示绑定。
UPDATE users
SET wechat_openid = 'wechat_demo_student001'
WHERE username = 'student001' AND wechat_openid IS NULL;

UPDATE users
SET qq_openid = 'qq_demo_teacher001'
WHERE username = 'teacher001' AND qq_openid IS NULL;

INSERT INTO courses (name, teacher_id, description, status)
SELECT
    'Python 程序设计',
    id,
    '课堂学情监控管理系统测试课程',
    'active'
FROM users
WHERE username = 'teacher001'
  AND NOT EXISTS (
      SELECT 1
      FROM courses
      WHERE name = 'Python 程序设计'
        AND teacher_id = users.id
  );

INSERT INTO course_sessions (
    course_id, class_name, topic, start_time, status
)
SELECT
    id,
    '软件工程1班',
    'FastAPI 基础',
    datetime('now', '-30 minutes'),
    'active'
FROM courses
WHERE name = 'Python 程序设计'
  AND NOT EXISTS (
      SELECT 1
      FROM course_sessions
      WHERE course_id = courses.id
        AND class_name = '软件工程1班'
        AND status = 'active'
  );

INSERT OR IGNORE INTO statistics_settings (
    id, interval_minutes, updated_by
)
SELECT 1, 5, id
FROM users
WHERE username = 'admin001';

-- 学生 1 的当前反馈为 5 分。
INSERT INTO feedback_records (session_id, student_id, score, submitted_at)
SELECT
    course_sessions.id,
    users.id,
    5,
    datetime(course_sessions.start_time, '+2 minutes')
FROM course_sessions
JOIN courses ON courses.id = course_sessions.course_id
JOIN users ON users.username = 'student001'
WHERE courses.name = 'Python 程序设计'
  AND course_sessions.class_name = '软件工程1班'
  AND course_sessions.status = 'active'
  AND NOT EXISTS (
      SELECT 1
      FROM feedback_records
      WHERE feedback_records.session_id = course_sessions.id
        AND feedback_records.student_id = users.id
  );

-- 学生 2 先提交 2 分，触发自主新增的学情预警模块。
INSERT INTO feedback_records (session_id, student_id, score, submitted_at)
SELECT
    course_sessions.id,
    users.id,
    2,
    datetime(course_sessions.start_time, '+1 minute')
FROM course_sessions
JOIN courses ON courses.id = course_sessions.course_id
JOIN users ON users.username = 'student002'
WHERE courses.name = 'Python 程序设计'
  AND course_sessions.class_name = '软件工程1班'
  AND course_sessions.status = 'active'
  AND NOT EXISTS (
      SELECT 1
      FROM feedback_records
      WHERE feedback_records.session_id = course_sessions.id
        AND feedback_records.student_id = users.id
  );

INSERT INTO learning_alerts (
    session_id, student_id, latest_feedback_id, latest_score, status,
    teacher_note, handled_by, created_at, updated_at, resolved_at
)
SELECT
    feedback_records.session_id,
    feedback_records.student_id,
    feedback_records.id,
    feedback_records.score,
    'resolved',
    '建议课后复习 FastAPI 路由，并在讨论区提出不懂的问题。',
    teacher.id,
    datetime(course_sessions.start_time, '+1 minute'),
    datetime(course_sessions.start_time, '+3 minutes'),
    datetime(course_sessions.start_time, '+3 minutes')
FROM feedback_records
JOIN course_sessions ON course_sessions.id = feedback_records.session_id
JOIN users AS student ON student.id = feedback_records.student_id
JOIN users AS teacher ON teacher.username = 'teacher001'
WHERE student.username = 'student002'
  AND feedback_records.score = 2
  AND NOT EXISTS (
      SELECT 1
      FROM learning_alerts
      WHERE learning_alerts.latest_feedback_id = feedback_records.id
  )
ORDER BY feedback_records.id ASC
LIMIT 1;

-- 后续再提交 5 分，使实时统计展示两名学生当前均为 5 分，同时保留跟进记录。
INSERT INTO feedback_records (session_id, student_id, score, submitted_at)
SELECT
    course_sessions.id,
    users.id,
    5,
    datetime(course_sessions.start_time, '+4 minutes')
FROM course_sessions
JOIN courses ON courses.id = course_sessions.course_id
JOIN users ON users.username = 'student002'
WHERE courses.name = 'Python 程序设计'
  AND course_sessions.class_name = '软件工程1班'
  AND course_sessions.status = 'active'
  AND EXISTS (
      SELECT 1
      FROM feedback_records
      WHERE feedback_records.session_id = course_sessions.id
        AND feedback_records.student_id = users.id
        AND feedback_records.score = 2
  )
  AND NOT EXISTS (
      SELECT 1
      FROM feedback_records
      WHERE feedback_records.session_id = course_sessions.id
        AND feedback_records.student_id = users.id
        AND feedback_records.score = 5
  );

-- 保存一份初始统计快照，后续由系统按管理员设置的 5～10 分钟周期继续生成。
INSERT INTO statistics_snapshots (
    session_id, interval_minutes, period_start, period_end,
    total_students, score_1_count, score_2_count, score_3_count,
    score_4_count, score_5_count, score_6_count, average_score, variance
)
SELECT
    course_sessions.id,
    statistics_settings.interval_minutes,
    course_sessions.start_time,
    datetime(course_sessions.start_time, '+' || statistics_settings.interval_minutes || ' minutes'),
    2, 0, 0, 0, 0, 2, 0, 5.0, 0.0
FROM course_sessions
JOIN courses ON courses.id = course_sessions.course_id
JOIN statistics_settings ON statistics_settings.id = 1
WHERE courses.name = 'Python 程序设计'
  AND course_sessions.class_name = '软件工程1班'
  AND course_sessions.status = 'active'
  AND NOT EXISTS (
      SELECT 1
      FROM statistics_snapshots
      WHERE statistics_snapshots.session_id = course_sessions.id
  );

INSERT INTO discussion_messages (session_id, user_id, content, created_at)
SELECT
    course_sessions.id,
    users.id,
    '老师您好，我想确认 FastAPI 路由参数的写法。',
    datetime(course_sessions.start_time, '+5 minutes')
FROM course_sessions
JOIN courses ON courses.id = course_sessions.course_id
JOIN users ON users.username = 'student001'
WHERE courses.name = 'Python 程序设计'
  AND course_sessions.class_name = '软件工程1班'
  AND course_sessions.status = 'active'
  AND NOT EXISTS (
      SELECT 1
      FROM discussion_messages
      WHERE discussion_messages.session_id = course_sessions.id
        AND discussion_messages.content = '老师您好，我想确认 FastAPI 路由参数的写法。'
  );

INSERT INTO discussion_messages (session_id, user_id, content, created_at)
SELECT
    course_sessions.id,
    users.id,
    '可以先看路径参数示例，不明白的地方继续在这里提问。',
    datetime(course_sessions.start_time, '+6 minutes')
FROM course_sessions
JOIN courses ON courses.id = course_sessions.course_id
JOIN users ON users.username = 'teacher001'
WHERE courses.name = 'Python 程序设计'
  AND course_sessions.class_name = '软件工程1班'
  AND course_sessions.status = 'active'
  AND NOT EXISTS (
      SELECT 1
      FROM discussion_messages
      WHERE discussion_messages.session_id = course_sessions.id
        AND discussion_messages.content = '可以先看路径参数示例，不明白的地方继续在这里提问。'
  );
