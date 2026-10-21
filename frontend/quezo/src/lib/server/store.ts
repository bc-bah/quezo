import "server-only";
import { createHash, randomBytes } from "node:crypto";
import { Pool, type PoolClient, type QueryResultRow } from "pg";
import { limits, type WebConfig } from "./config";
import { unauthenticated, unavailable } from "./errors";

export const opaque = () => randomBytes(32).toString("base64url");
export const validOpaque = (value: string | undefined): value is string =>
  typeof value === "string" && /^[A-Za-z0-9_-]{43}$/.test(value);
const hash = (value: string) => createHash("sha256").update(value).digest("hex");

export interface LoginTransaction extends QueryResultRow {
  state: string;
  nonce: string;
  verifier: string;
}
export interface Session extends QueryResultRow {
  access_token: string;
  expires_at: Date;
}

export class SessionStore {
  private constructor(private readonly pool: Pool) {}

  static async open(config: Pick<WebConfig, "databaseUrl" | "local">): Promise<SessionStore> {
    const pool = new Pool({
      connectionString: config.databaseUrl,
      ssl: config.local ? false : { rejectUnauthorized: true },
      max: limits.poolMax,
      connectionTimeoutMillis: limits.networkMs,
      idleTimeoutMillis: 10000,
      maxLifetimeSeconds: 300,
      statement_timeout: limits.networkMs,
      query_timeout: limits.networkMs + 1000,
      lock_timeout: 2000,
      idle_in_transaction_session_timeout: limits.networkMs,
      application_name: "quezo-web",
      options: "-c timezone=UTC -c search_path=pg_catalog",
    });
    pool.on("error", () => {
      console.error(JSON.stringify({ event: "web_database_connection_failed", code: "DEPENDENCY_UNAVAILABLE" }));
    });
    const store = new SessionStore(pool);
    try {
      const result = await pool.query<{ allowed: boolean }>(`
        SELECT current_user = 'quezo_web'
          AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls)
          AS allowed FROM pg_roles WHERE rolname = current_user
      `);
      if (!result.rows[0]?.allowed) throw unavailable();
      await pool.query("SELECT id_hash FROM quezo_session.sessions LIMIT 0");
      await pool.query("SELECT id_hash FROM quezo_session.login_transactions LIMIT 0");
      return store;
    } catch {
      await pool.end();
      throw unavailable();
    }
  }

  close(): Promise<void> { return this.pool.end(); }

  private async query<Row extends QueryResultRow>(text: string, values: unknown[] = []) {
    if (this.pool.waitingCount >= limits.poolWaitingMax) throw unavailable();
    try { return await this.pool.query<Row>(text, values); }
    catch { throw unavailable(); }
  }

  private async transaction<T>(work: (client: PoolClient) => Promise<T>): Promise<T> {
    if (this.pool.waitingCount >= limits.poolWaitingMax) throw unavailable();
    let client: PoolClient | undefined;
    try {
      client = await this.pool.connect();
      await client.query("BEGIN");
      const result = await work(client);
      await client.query("COMMIT");
      return result;
    } catch {
      if (client) {
        try { await client.query("ROLLBACK"); }
        catch { client.release(true); client = undefined; }
      }
      throw unavailable();
    } finally { client?.release(); }
  }

  async beginLogin(transaction: LoginTransaction, oldLogin?: string, oldSession?: string): Promise<string> {
    const id = opaque();
    await this.transaction(async (client) => {
      await this.invalidate(client, oldSession, oldLogin);
      await client.query(`
        INSERT INTO quezo_session.login_transactions (id_hash, state, nonce, verifier, expires_at)
        VALUES ($1, $2, $3, $4, clock_timestamp() + make_interval(secs => $5))
      `, [hash(id), transaction.state, transaction.nonce, transaction.verifier, limits.loginSeconds]);
    });
    return id;
  }

  async consumeLogin(id: string | undefined): Promise<LoginTransaction | undefined> {
    if (!validOpaque(id)) return undefined;
    const result = await this.query<LoginTransaction>(`
      UPDATE quezo_session.login_transactions SET consumed = true
      WHERE id_hash = $1 AND consumed = false
      RETURNING state, nonce, verifier, expires_at > clock_timestamp() AS valid
    `, [hash(id)]);
    const row = result.rows[0];
    return row?.valid === true ? row : undefined;
  }

  async createSession(accessToken: string, tokenExpiresAt: Date, loginId: string): Promise<string> {
    const id = opaque();
    const result = await this.query(`
      WITH login AS (
        DELETE FROM quezo_session.login_transactions
        WHERE id_hash = $4 AND consumed = true AND expires_at > clock_timestamp()
        RETURNING id_hash
      )
      INSERT INTO quezo_session.sessions
        (id_hash, access_token, token_expires_at, expires_at, idle_expires_at, login_hash)
      SELECT $1, $2, $3,
        LEAST($3, clock_timestamp() + make_interval(secs => $5)),
        LEAST($3, clock_timestamp() + make_interval(secs => $6)), login.id_hash FROM login
    `, [hash(id), accessToken, tokenExpiresAt, hash(loginId), limits.sessionSeconds, limits.idleSeconds]);
    if (result.rowCount !== 1) throw unauthenticated();
    return id;
  }

  async session(id: string | undefined): Promise<Session | undefined> {
    if (!validOpaque(id)) return undefined;
    const result = await this.query<Session>(`
      UPDATE quezo_session.sessions
      SET idle_expires_at = LEAST(expires_at, clock_timestamp() + make_interval(secs => $2))
      WHERE id_hash = $1 AND expires_at > clock_timestamp()
        AND idle_expires_at > clock_timestamp() AND token_expires_at > clock_timestamp()
      RETURNING access_token, expires_at
    `, [hash(id), limits.idleSeconds]);
    return result.rows[0];
  }

  async logout(id: string | undefined, loginId?: string): Promise<void> {
    await this.transaction((client) => this.invalidate(client, id, loginId));
  }

  private async invalidate(client: PoolClient, id?: string, loginId?: string): Promise<void> {
    const loginHash = validOpaque(loginId) ? hash(loginId) : null;
    // Separate READ COMMITTED statements matter: if callback completion holds the
    // login row lock, the second snapshot must see its newly committed session.
    await client.query("DELETE FROM quezo_session.login_transactions WHERE id_hash = $1", [loginHash]);
    await client.query("DELETE FROM quezo_session.sessions WHERE id_hash = $1 OR login_hash = $2",
      [validOpaque(id) ? hash(id) : null, loginHash]);
  }

  async prune(): Promise<void> {
    await this.query(`
      WITH expired_login AS (
        DELETE FROM quezo_session.login_transactions WHERE id_hash IN (
          SELECT id_hash FROM quezo_session.login_transactions
          WHERE expires_at <= clock_timestamp() LIMIT 100
        )
      )
      DELETE FROM quezo_session.sessions WHERE id_hash IN (
        SELECT id_hash FROM quezo_session.sessions
        WHERE expires_at <= clock_timestamp() OR idle_expires_at <= clock_timestamp() LIMIT 100
      )
    `);
  }
}
