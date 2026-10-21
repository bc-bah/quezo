import { cookies } from "next/headers";
import { runtime } from "../lib/server/runtime";
import { publicError } from "../lib/server/errors";
import { SessionShell } from "./session-shell";

export const dynamic = "force-dynamic";

export default async function HomePage() {
  try {
    const web = await runtime();
    const cookie = (await cookies()).get(web.config.sessionCookie)?.value;
    return <SessionShell view={await web.view(cookie)} />;
  } catch (error) {
    return <SessionShell view={{ state: "error", error: publicError(error).envelope }} />;
  }
}
