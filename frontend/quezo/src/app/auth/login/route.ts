import type { NextRequest } from "next/server";
import { authRoute } from "../../../lib/server/http";

export const runtime = "nodejs";
export const POST = (request: NextRequest) => authRoute("login", request);
