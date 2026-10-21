import "server-only";
import { readConfig } from "./config";
import { publicError } from "./errors";
import { WebSession } from "./session";
import { SessionStore } from "./store";

declare global {
  var quezoWeb: Promise<WebSession> | undefined;
  var quezoShutdownInstalled: boolean | undefined;
}

export function runtime(): Promise<WebSession> {
  globalThis.quezoWeb ??= (async () => {
    const config = readConfig();
    const store = await SessionStore.open(config);
    return new WebSession(config, store);
  })().catch((error: unknown) => {
    globalThis.quezoWeb = undefined;
    throw publicError(error);
  });
  return globalThis.quezoWeb;
}

export async function startRuntime(): Promise<void> {
  await runtime();
  if (globalThis.quezoShutdownInstalled) return;
  globalThis.quezoShutdownInstalled = true;
  let stopping = false;
  for (const signal of ["SIGINT", "SIGTERM"] as const) {
    process.on(signal, () => {
      if (stopping) return;
      stopping = true;
      void (async () => {
        try {
          const web = await globalThis.quezoWeb;
          if (web) await web.store.close();
          process.exit(0);
        } catch (error) {
          publicError(error);
          process.exit(1);
        }
      })();
    });
  }
}
