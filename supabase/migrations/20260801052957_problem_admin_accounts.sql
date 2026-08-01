create table dojo.problem_admins (
    email text primary key,
    user_id uuid unique references auth.users(id) on delete restrict,
    created_at timestamptz not null default now(),
    activated_at timestamptz,
    constraint problem_admins_email_normalized
        check (email = lower(trim(email)) and length(email) > 3),
    constraint problem_admins_activation_consistent
        check (
            (user_id is null and activated_at is null)
            or (user_id is not null and activated_at is not null)
        )
);

comment on table dojo.problem_admins is
    'Private allowlist for accounts permitted to author coding problems.';

revoke all on schema dojo from public, anon, authenticated;
revoke all on table dojo.problem_admins from public, anon, authenticated;
