-- Attendly lean schema. Run once in Supabase → SQL Editor.
-- Service role (EXE / Flask) bypasses RLS.

create table if not exists admins (
  id bigint generated always as identity primary key,
  username text unique not null,
  password_hash text not null,
  name text not null
);

create table if not exists schools (
  id bigint generated always as identity primary key,
  name text not null,
  username text unique not null,
  password_hash text not null,
  license_expires_at timestamptz,
  max_students int not null default 200,
  is_active boolean not null default true
);

create table if not exists license_keys (
  id bigint generated always as identity primary key,
  key_code text unique not null,
  days_valid int not null default 30,
  max_students int not null default 200,
  school_id bigint references schools(id) on delete set null,
  used_at timestamptz,
  notes text,
  is_revoked boolean not null default false
);

create table if not exists students (
  id bigint generated always as identity primary key,
  school_id bigint not null references schools(id) on delete cascade,
  student_id text not null,
  name text not null,
  class_name text not null,
  parent_phone text not null,
  dob date not null,
  nfc_uid text not null,
  unique (school_id, student_id),
  unique (school_id, nfc_uid)
);

create index if not exists students_phone_idx on students (school_id, parent_phone);

create table if not exists attendance (
  id bigint generated always as identity primary key,
  school_id bigint not null references schools(id) on delete cascade,
  student_pk bigint not null references students(id) on delete cascade,
  day date not null,
  time_in text,
  time_out text,
  src text not null default 'm',
  unique (school_id, student_pk, day)
);

create index if not exists attendance_day_idx on attendance (school_id, day);

create table if not exists alerts (
  id bigint generated always as identity primary key,
  school_id bigint not null references schools(id) on delete cascade,
  title text not null,
  body text not null,
  created_at timestamptz not null default now()
);

create index if not exists alerts_school_idx on alerts (school_id, id desc);

create table if not exists fcm_tokens (
  token text primary key,
  school_id bigint not null references schools(id) on delete cascade,
  parent_phone text not null,
  updated_at timestamptz not null default now()
);

create index if not exists fcm_phone_idx on fcm_tokens (school_id, parent_phone);

alter table admins enable row level security;
alter table schools enable row level security;
alter table license_keys enable row level security;
alter table students enable row level security;
alter table attendance enable row level security;
alter table alerts enable row level security;
alter table fcm_tokens enable row level security;
