from uuid import UUID, uuid5

from psycopg import AsyncConnection

from quezo_api.database import Database
from quezo_api.errors import ApiError, ErrorCode
from quezo_api.modules.identity.account_admin import KeycloakAccountAdmin
from quezo_api.schemas import (
    AccountAdminPage,
    AccountAdminView,
    AccountProvisionRequest,
    AccountRoleUpdate,
    Actor,
    Role,
)

ACCOUNT_NAMESPACE = UUID("09623a53-dda8-47d3-8989-8be3aa6ad81e")
ACCOUNT_LOCK = 716269004


async def _view(connection: AsyncConnection[tuple[object, ...]], account_id: UUID) -> AccountAdminView:
    cursor = await connection.execute(
        """
        SELECT a.id, a.username, a.email, a.status,
               ARRAY(SELECT r.role FROM quezo.account_roles r
                     WHERE r.account_id = a.id ORDER BY r.role),
               a.provisioning_state, a.provisioning_error_code,
               a.identity_sync_state, a.identity_error_code
        FROM quezo.accounts a WHERE a.id = %s
        """,
        (account_id,),
    )
    row = await cursor.fetchone()
    if row is None:
        raise ApiError(ErrorCode.NOT_FOUND)
    return AccountAdminView.model_validate({
        "userId": row[0], "username": row[1], "email": row[2], "status": row[3],
        "roles": row[4], "provisioningState": row[5],
        "provisioningErrorCode": row[6], "identitySyncState": row[7],
        "identityErrorCode": row[8],
    })


async def _audit(
    connection: AsyncConnection[tuple[object, ...]],
    actor_id: UUID,
    target_id: UUID,
    action: str,
    *,
    error_code: ErrorCode | None = None,
) -> None:
    await connection.execute(
        """
        INSERT INTO quezo.account_admin_events
            (actor_id, target_id, action, outcome, error_code)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            actor_id, target_id, action,
            "failure" if error_code is not None else "success",
            error_code.value if error_code is not None else None,
        ),
    )


async def list_accounts(database: Database) -> AccountAdminPage:
    async with database.transaction() as connection:
        cursor = await connection.execute(
            """
            SELECT a.id, a.username, a.email, a.status,
                   ARRAY(SELECT r.role FROM quezo.account_roles r
                         WHERE r.account_id = a.id ORDER BY r.role),
                   a.provisioning_state, a.provisioning_error_code,
                   a.identity_sync_state, a.identity_error_code
            FROM quezo.accounts a
            ORDER BY a.created_at DESC, a.id
            """
        )
        rows = await cursor.fetchall()
    return AccountAdminPage.model_validate({
        "items": [{
            "userId": row[0], "username": row[1], "email": row[2], "status": row[3],
            "roles": row[4], "provisioningState": row[5],
            "provisioningErrorCode": row[6], "identitySyncState": row[7],
            "identityErrorCode": row[8],
        } for row in rows],
        "nextCursor": None,
    })


async def provision_account(
    database: Database,
    provider: KeycloakAccountAdmin,
    issuer: str,
    actor: Actor,
    request: AccountProvisionRequest,
) -> AccountAdminView:
    username = request.username.lower()
    account_id = uuid5(ACCOUNT_NAMESPACE, f"{issuer}\n{username}")
    failure: ApiError | None = None
    async with database.transaction() as connection:
        await connection.execute("SELECT pg_advisory_xact_lock(%s)", (ACCOUNT_LOCK,))
        cursor = await connection.execute(
            """
            SELECT a.id, a.email, a.provisioning_state,
                   ARRAY(SELECT r.role FROM quezo.account_roles r
                         WHERE r.account_id = a.id ORDER BY r.role)
            FROM quezo.accounts a
            WHERE lower(username) = %s FOR UPDATE
            """,
            (username,),
        )
        existing = await cursor.fetchone()
        if existing is not None:
            if (
                existing[0] != account_id
                or existing[1] != request.email
                or existing[2] == "complete"
                or existing[3] != sorted(role.value for role in request.roles)
            ):
                raise ApiError(ErrorCode.INVALID_STATE)
        else:
            await connection.execute(
                """
                INSERT INTO quezo.accounts
                    (id, status, username, email, provisioning_state,
                     identity_sync_state, identity_desired_enabled)
                VALUES (%s, 'disabled', %s, %s, 'pending', 'in_sync', false)
                """,
                (account_id, username, request.email),
            )
            for role in request.roles:
                await connection.execute(
                    "INSERT INTO quezo.account_roles (account_id, role) VALUES (%s, %s)",
                    (account_id, role.value),
                )
        try:
            identity_issuer, subject = await provider.ensure_disabled_user(
                str(account_id), username, request.email,
            )
            if identity_issuer != issuer or not subject:
                raise ApiError(ErrorCode.DEPENDENCY_UNAVAILABLE)
            await connection.execute(
                """
                INSERT INTO quezo.identity_mappings (issuer, subject, account_id, active)
                VALUES (%s, %s, %s, false)
                ON CONFLICT (issuer, subject) DO UPDATE SET active = false
                WHERE quezo.identity_mappings.account_id = EXCLUDED.account_id
                """,
                (identity_issuer, subject, account_id),
            )
            cursor = await connection.execute(
                "SELECT account_id FROM quezo.identity_mappings WHERE issuer = %s AND subject = %s",
                (identity_issuer, subject),
            )
            mapping = await cursor.fetchone()
            if mapping is None or mapping[0] != account_id:
                raise ApiError(ErrorCode.INVALID_STATE)
            await connection.execute(
                """
                UPDATE quezo.accounts
                SET provisioning_state = 'complete', provisioning_error_code = NULL,
                    identity_sync_state = 'in_sync', identity_error_code = NULL
                WHERE id = %s
                """,
                (account_id,),
            )
            await _audit(connection, actor.user_id, account_id, "provision")
        except ApiError as error:
            failure = error
            await connection.execute(
                """
                UPDATE quezo.accounts
                SET status = 'disabled', provisioning_state = 'failed',
                    provisioning_error_code = %s, identity_sync_state = 'failed',
                    identity_error_code = %s, identity_desired_enabled = false
                WHERE id = %s
                """,
                (error.code.value, error.code.value, account_id),
            )
            await connection.execute(
                "UPDATE quezo.identity_mappings SET active = false WHERE account_id = %s",
                (account_id,),
            )
            await _audit(
                connection, actor.user_id, account_id, "provision", error_code=error.code,
            )
    if failure is not None:
        raise failure
    async with database.transaction() as connection:
        return await _view(connection, account_id)


async def update_roles(
    database: Database, actor: Actor, account_id: UUID, request: AccountRoleUpdate,
) -> AccountAdminView:
    async with database.transaction() as connection:
        await connection.execute("SELECT pg_advisory_xact_lock(%s)", (ACCOUNT_LOCK,))
        cursor = await connection.execute(
            "SELECT status, provisioning_state FROM quezo.accounts WHERE id = %s FOR UPDATE",
            (account_id,),
        )
        account = await cursor.fetchone()
        if account is None:
            raise ApiError(ErrorCode.NOT_FOUND)
        if account[1] != "complete":
            raise ApiError(ErrorCode.INVALID_STATE)
        cursor = await connection.execute(
            "SELECT 1 FROM quezo.account_roles WHERE account_id = %s AND role = 'administrator'",
            (account_id,),
        )
        was_admin = await cursor.fetchone() is not None
        if account[0] == "active" and was_admin and Role.ADMINISTRATOR not in request.roles:
            cursor = await connection.execute(
                """
                SELECT count(*) FROM quezo.accounts a
                JOIN quezo.identity_mappings m ON m.account_id = a.id AND m.active
                JOIN quezo.account_roles r ON r.account_id = a.id
                WHERE a.status = 'active' AND r.role = 'administrator'
                """
            )
            count_row = await cursor.fetchone()
            if count_row is None or type(count_row[0]) is not int:
                raise RuntimeError("Administrator count query returned no count")
            if count_row[0] <= 1:
                raise ApiError(ErrorCode.INVALID_STATE)
        await connection.execute("DELETE FROM quezo.account_roles WHERE account_id = %s", (account_id,))
        for role in request.roles:
            await connection.execute(
                "INSERT INTO quezo.account_roles (account_id, role) VALUES (%s, %s)",
                (account_id, role.value),
            )
        await _audit(connection, actor.user_id, account_id, "roles_update")
        return await _view(connection, account_id)


async def update_status(
    database: Database,
    provider: KeycloakAccountAdmin,
    actor: Actor,
    account_id: UUID,
    enabled: bool,
) -> AccountAdminView:
    action = "activate" if enabled else "deactivate"
    async with database.transaction() as connection:
        await connection.execute("SELECT pg_advisory_xact_lock(%s)", (ACCOUNT_LOCK,))
        cursor = await connection.execute(
            """
            SELECT a.status, a.provisioning_state, a.identity_sync_state,
                   a.identity_desired_enabled, m.issuer, m.subject
            FROM quezo.accounts a
            JOIN quezo.identity_mappings m ON m.account_id = a.id
            WHERE a.id = %s FOR UPDATE OF a
            """,
            (account_id,),
        )
        account = await cursor.fetchone()
        if account is None:
            raise ApiError(ErrorCode.NOT_FOUND)
        status, provisioning_state, sync_state, desired_enabled, issuer, subject = account
        if (
            not isinstance(status, str) or not isinstance(provisioning_state, str)
            or not isinstance(sync_state, str) or type(desired_enabled) is not bool
            or not isinstance(issuer, str) or not isinstance(subject, str)
        ):
            raise RuntimeError("Account identity query returned invalid data")
        if provisioning_state != "complete":
            raise ApiError(ErrorCode.INVALID_STATE)
        if enabled:
            if status == "active" and sync_state == "in_sync":
                return await _view(connection, account_id)
            if sync_state not in {"in_sync", "pending", "failed"} or (
                sync_state != "in_sync" and desired_enabled is not True
            ):
                raise ApiError(ErrorCode.INVALID_STATE)
            if issuer != provider.settings.issuer:
                raise ApiError(ErrorCode.INVALID_STATE)
            await connection.execute(
                """
                UPDATE quezo.accounts SET identity_sync_state = 'pending',
                    identity_desired_enabled = true, identity_error_code = NULL
                WHERE id = %s
                """,
                (account_id,),
            )
        else:
            if status == "active":
                cursor = await connection.execute(
                    """
                    SELECT 1 FROM quezo.account_roles
                    WHERE account_id = %s AND role = 'administrator'
                    """,
                    (account_id,),
                )
                if await cursor.fetchone() is not None:
                    cursor = await connection.execute(
                        """
                        SELECT count(*) FROM quezo.accounts a
                        JOIN quezo.identity_mappings m ON m.account_id = a.id AND m.active
                        JOIN quezo.account_roles r ON r.account_id = a.id
                        WHERE a.status = 'active' AND r.role = 'administrator'
                        """
                    )
                    count_row = await cursor.fetchone()
                    if count_row is None or type(count_row[0]) is not int:
                        raise RuntimeError("Administrator count query returned no count")
                    if count_row[0] <= 1:
                        raise ApiError(ErrorCode.INVALID_STATE)
            await connection.execute(
                """
                UPDATE quezo.accounts SET status = 'disabled',
                    identity_sync_state = 'pending',
                    identity_desired_enabled = false, identity_error_code = NULL
                WHERE id = %s
                """,
                (account_id,),
            )
            await connection.execute(
                "UPDATE quezo.identity_mappings SET active = false WHERE account_id = %s",
                (account_id,),
            )
    try:
        await provider.set_enabled(str(account_id), subject, enabled)
    except ApiError as error:
        async with database.transaction() as connection:
            await connection.execute(
                """
                UPDATE quezo.accounts SET identity_sync_state = 'failed',
                    identity_error_code = %s
                WHERE id = %s AND identity_sync_state = 'pending'
                    AND identity_desired_enabled = %s
                """,
                (error.code.value, account_id, enabled),
            )
            await _audit(connection, actor.user_id, account_id, action, error_code=error.code)
        raise
    async with database.transaction() as connection:
        await connection.execute("SELECT pg_advisory_xact_lock(%s)", (ACCOUNT_LOCK,))
        if enabled:
            cursor = await connection.execute(
                """
                UPDATE quezo.accounts SET status = 'active',
                    identity_sync_state = 'in_sync', identity_desired_enabled = true,
                    identity_error_code = NULL
                WHERE id = %s AND status = 'disabled'
                    AND identity_sync_state = 'pending'
                    AND identity_desired_enabled = true
                """,
                (account_id,),
            )
            if cursor.rowcount != 1:
                raise ApiError(ErrorCode.INVALID_STATE)
            await connection.execute(
                "UPDATE quezo.identity_mappings SET active = true WHERE account_id = %s",
                (account_id,),
            )
        else:
            cursor = await connection.execute(
                """
                UPDATE quezo.accounts SET identity_sync_state = 'in_sync',
                    identity_error_code = NULL
                WHERE id = %s AND status = 'disabled'
                    AND identity_sync_state = 'pending'
                    AND identity_desired_enabled = false
                """,
                (account_id,),
            )
            if cursor.rowcount != 1:
                raise ApiError(ErrorCode.INVALID_STATE)
        await _audit(connection, actor.user_id, account_id, action)
        return await _view(connection, account_id)
