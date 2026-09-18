-- Parent app talks to these functions with the publishable key.
-- Tables stay locked (RLS on, no anon policies).

create or replace function attendly_phone(p text)
returns text
language sql
immutable
as $$
  select right(regexp_replace(coalesce(p, ''), '\D', '', 'g'), 10);
$$;

create or replace function parent_login(p_school text, p_phone text, p_dob date)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_phone text := attendly_phone(p_phone);
  v_school record;
  v_kids json;
begin
  select id, name into v_school
  from schools
  where is_active
    and (
      lower(name) = lower(trim(p_school))
      or lower(username) = lower(trim(p_school))
    )
  limit 1;

  if v_school.id is null then
    select id, name into v_school
    from schools
    where is_active and lower(name) like '%' || lower(trim(p_school)) || '%'
    limit 2;
    if not found then
      return json_build_object('ok', false, 'error', 'School not found. Check the school name.');
    end if;
  end if;

  if not exists (
    select 1 from students
    where school_id = v_school.id and parent_phone = v_phone and dob = p_dob
  ) then
    return json_build_object('ok', false, 'error', 'No matching child for this phone and date of birth.');
  end if;

  select coalesce(json_agg(json_build_object(
    'id', id,
    'student_id', student_id,
    'name', name,
    'class_name', class_name,
    'dob', dob
  ) order by name), '[]'::json)
  into v_kids
  from students
  where school_id = v_school.id and parent_phone = v_phone;

  return json_build_object(
    'ok', true,
    'school', json_build_object('id', v_school.id, 'name', v_school.name),
    'children', v_kids
  );
end;
$$;

create or replace function parent_guard(p_school_id bigint, p_phone text, p_dob date, p_student bigint)
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select exists (
    select 1 from students
    where school_id = p_school_id
      and parent_phone = attendly_phone(p_phone)
      and dob = p_dob
      and id = p_student
  );
$$;

create or replace function parent_today(p_school_id bigint, p_phone text, p_dob date, p_student bigint)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_stu record;
  v_in text;
  v_out text;
begin
  if not parent_guard(p_school_id, p_phone, p_dob, p_student) then
    return json_build_object('ok', false, 'error', 'Please sign in again.');
  end if;
  select id, name, class_name into v_stu from students where id = p_student;
  select time_in, time_out into v_in, v_out
  from attendance
  where school_id = p_school_id and student_pk = p_student and day = current_date;
  return json_build_object(
    'ok', true,
    'date', current_date,
    'is_present', v_in is not null,
    'time_in', coalesce(v_in, ''),
    'time_out', coalesce(v_out, ''),
    'student', json_build_object(
      'id', v_stu.id, 'name', v_stu.name, 'class_name', v_stu.class_name
    )
  );
end;
$$;

create or replace function parent_month(p_school_id bigint, p_phone text, p_dob date, p_student bigint, p_year int, p_month int)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_from date;
  v_to date;
  v_days json;
begin
  if not parent_guard(p_school_id, p_phone, p_dob, p_student) then
    return json_build_object('ok', false, 'error', 'Please sign in again.');
  end if;
  v_from := make_date(p_year, p_month, 1);
  v_to := (v_from + interval '1 month' - interval '1 day')::date;
  select coalesce(json_agg(json_build_object(
    'date', day, 'time_in', coalesce(time_in, ''), 'time_out', coalesce(time_out, '')
  ) order by day), '[]'::json)
  into v_days
  from attendance
  where school_id = p_school_id and student_pk = p_student
    and day between v_from and v_to;
  return json_build_object('ok', true, 'year', p_year, 'month', p_month, 'days', v_days);
end;
$$;

create or replace function parent_alerts(p_school_id bigint, p_phone text, p_dob date, p_student bigint)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_rows json;
begin
  if not parent_guard(p_school_id, p_phone, p_dob, p_student) then
    return json_build_object('ok', false, 'error', 'Please sign in again.');
  end if;
  select coalesce(json_agg(json_build_object(
    'id', id, 'title', title, 'body', body, 'created_at', created_at
  ) order by id desc), '[]'::json)
  into v_rows
  from (
    select id, title, body, created_at from alerts
    where school_id = p_school_id
    order by id desc
    limit 40
  ) a;
  return json_build_object('ok', true, 'alerts', v_rows);
end;
$$;

create or replace function parent_feed(p_school_id bigint, p_phone text, p_dob date, p_student bigint)
returns json
language plpgsql
security definer
set search_path = public
as $$
declare
  v_name text;
  v_att_id bigint;
  v_in text;
  v_out text;
  v_day date;
  v_items json := '[]'::json;
begin
  if not parent_guard(p_school_id, p_phone, p_dob, p_student) then
    return json_build_object('ok', false, 'error', 'Please sign in again.');
  end if;
  select name into v_name from students where id = p_student;
  select id, time_in, time_out, day into v_att_id, v_in, v_out, v_day
  from attendance
  where school_id = p_school_id and student_pk = p_student and day = current_date;
  select coalesce(json_agg(item order by ord), '[]'::json) into v_items
  from (
    select 1 as ord, json_build_object(
      'id', coalesce(v_att_id, 0),
      'ntype', 'arrival',
      'title', split_part(v_name, ' ', 1) || ' arrived at school',
      'body', v_name || ' arrived at school at ' || v_in,
      'created_at', coalesce(v_day::text, current_date::text) || ' ' || v_in
    ) as item
    where v_in is not null
    union all
    select 2, json_build_object(
      'id', 500000 + coalesce(v_att_id, 0),
      'ntype', 'departure',
      'title', split_part(v_name, ' ', 1) || ' left school',
      'body', v_name || ' left school at ' || v_out,
      'created_at', coalesce(v_day::text, current_date::text) || ' ' || v_out
    )
    where v_out is not null
    union all
    select 100 + id, json_build_object(
      'id', 1000000 + id, 'ntype', 'alert', 'title', title, 'body', body, 'created_at', created_at
    )
    from alerts
    where school_id = p_school_id
  ) s;
  return json_build_object('ok', true, 'notifications', v_items);
end;
$$;

create or replace function parent_register_fcm(p_school_id bigint, p_phone text, p_dob date, p_student bigint, p_token text)
returns json
language plpgsql
security definer
set search_path = public
as $$
begin
  if not parent_guard(p_school_id, p_phone, p_dob, p_student) then
    return json_build_object('ok', false, 'error', 'Please sign in again.');
  end if;
  if p_token is null or length(trim(p_token)) < 10 then
    return json_build_object('ok', false, 'error', 'Missing FCM token.');
  end if;
  insert into fcm_tokens(token, school_id, parent_phone, updated_at)
  values (trim(p_token), p_school_id, attendly_phone(p_phone), now())
  on conflict (token) do update
    set school_id = excluded.school_id,
        parent_phone = excluded.parent_phone,
        updated_at = now();
  return json_build_object('ok', true);
end;
$$;

revoke all on function parent_login(text, text, date) from public;
revoke all on function parent_today(bigint, text, date, bigint) from public;
revoke all on function parent_month(bigint, text, date, bigint, int, int) from public;
revoke all on function parent_alerts(bigint, text, date, bigint) from public;
revoke all on function parent_feed(bigint, text, date, bigint) from public;
revoke all on function parent_register_fcm(bigint, text, date, bigint, text) from public;

grant execute on function parent_login(text, text, date) to anon, authenticated;
grant execute on function parent_today(bigint, text, date, bigint) to anon, authenticated;
grant execute on function parent_month(bigint, text, date, bigint, int, int) to anon, authenticated;
grant execute on function parent_alerts(bigint, text, date, bigint) to anon, authenticated;
grant execute on function parent_feed(bigint, text, date, bigint) to anon, authenticated;
grant execute on function parent_register_fcm(bigint, text, date, bigint, text) to anon, authenticated;
