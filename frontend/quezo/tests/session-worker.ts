import { SessionStore } from "../src/lib/server/store";
import { config } from "./fixtures";

async function main() {
  let input = "";
  for await (const chunk of process.stdin) input += String(chunk);
  const command: { action: string; id?: string } = JSON.parse(input);
  const store = await SessionStore.open(config());
  try {
  if (command.action === "create") {
    const login = await store.beginLogin({ state: "synthetic", nonce: "synthetic", verifier: "synthetic" });
    await store.consumeLogin(login);
    console.log(await store.createSession("synthetic-access-token", new Date(Date.now() + 3600000), login));
  } else if (command.action === "read") {
    console.log(Boolean(await store.session(command.id)));
  } else if (command.action === "logout") {
    await store.logout(command.id);
    console.log("invalidated");
  } else if (command.action === "create-login") {
    console.log(await store.beginLogin({ state: "synthetic", nonce: "synthetic", verifier: "synthetic" }));
  } else if (command.action === "consume-login") {
    console.log(Boolean(await store.consumeLogin(command.id)));
  } else {
    throw new Error("Unknown test action");
  }
  } finally { await store.close(); }
}
void main();
