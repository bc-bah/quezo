// Next leaves signal handling to the session runtime, which closes its bounded pg pool.
process.env.NEXT_MANUAL_SIG_HANDLE = "1";
if (!process.argv.includes("--hostname")) process.argv.push("--hostname", "127.0.0.1");
await import("next/dist/bin/next");
